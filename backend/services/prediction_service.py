"""
PredictionService: engine scores → optimizer → captain engine → explainer.

Every generated prediction is persisted (prediction, predicted_player,
recommended_team, team_player) and rule firings are written to rule_trigger
for audit (MVP scope: "Rule trigger audit log").
"""
from __future__ import annotations

import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import (
    Prediction, PredictedPlayer, RecommendedTeam, RuleTrigger, TeamPlayer, User,
)
from backend.schemas import (
    CaptainOption, CaptainRecommendation, CaptainResponse, DifferentialOut, DifferentialsResponse,
    ExplainResponse, ExplanationFactor, PlayerPrediction, PredictTeamResponse, TeamResult,
)
from backend.services.engine import MatchScores, PlayerScore, score_match
from llm.explainer import build_factors, confidence_label, explain, template_explanation
from optimizer.captain_engine import recommend
from optimizer.lp_optimizer import solve_team
from optimizer.scoring import OptPlayer, ownership_tier, score_for_mode


def _err(status: int, code: str, message: str, **details) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message, "details": details})


def _pp(ps: PlayerScore, with_expl: bool = True, match=None, venue_name=None) -> PlayerPrediction:
    expl = None
    if with_expl:
        expl = template_explanation(ps, build_factors(ps, match, venue_name))
    return PlayerPrediction(
        player_id=uuid.UUID(ps.player_id), full_name=ps.full_name, role=ps.role, team=ps.team, credits=ps.credits,
        predicted_fp=ps.predicted_fp, fp_ceiling=ps.fp_ceiling, fp_floor=ps.fp_floor, confidence=ps.confidence,
        confidence_label=confidence_label(ps.confidence), is_differential=ps.is_differential,
        ownership_estimate=f"{ps.ownership:.0f}%", ownership_tier=ownership_tier(ps.ownership),
        rules_fired=[r["id"] for r in ps.rules_fired], explanation=expl,
    )


class PredictionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _scores(self, match_id: str, override_toss: Optional[dict] = None) -> MatchScores:
        try:
            return await score_match(self.db, match_id, override_toss=override_toss)
        except LookupError:
            raise _err(404, "MATCH_NOT_FOUND", f"Match {match_id} not found")
        except ValueError as e:
            if "PREDICTION_NO_PLAYERS" in str(e):
                raise _err(400, "PREDICTION_NO_PLAYERS",
                           "A squad isn't available for one of the teams yet — there is no recent match data to build "
                           "a probable XI from. Predictions unlock when the official squad is announced.")
            raise

    def _pool(self, ms: MatchScores, override_xi: Optional[Dict[str, List[str]]] = None) -> List[PlayerScore]:
        pool = ms.players
        if override_xi:
            names = {n.lower() for xi in override_xi.values() for n in xi}
            chosen = [p for p in pool if p.full_name.lower() in names or p.cricsheet_key.lower() in names]
            if len({p.team for p in chosen}) == 2 and len(chosen) >= 18:
                pool = chosen
        return pool

    def _team_result(self, ms: MatchScores, res, mode: str, index: int = 0) -> TeamResult:
        caps = recommend(res.players, mode, rotation=index)
        cap, vc = caps[0], caps[1]
        by_id = ms.by_id
        players = sorted(res.players, key=lambda p: ("WK", "BAT", "AR", "BOWL").index(p.role))
        conf = int(round(sum(by_id[p.player_id].confidence for p in players) / len(players)))
        return TeamResult(
            players=[_pp(by_id[p.player_id], True, ms.match, ms.match.venue_name) for p in players],
            captain=CaptainRecommendation(player_id=uuid.UUID(cap.player.player_id), full_name=cap.player.full_name,
                                          confidence=cap.player.confidence, ceiling_score=cap.player.ceiling,
                                          type=cap.type, reasoning=cap.reasoning),
            vice_captain=CaptainRecommendation(player_id=uuid.UUID(vc.player.player_id), full_name=vc.player.full_name,
                                               confidence=vc.player.confidence, ceiling_score=vc.player.ceiling,
                                               type="safe_vc" if vc.type == "safe_captain" else vc.type,
                                               reasoning=vc.reasoning),
            total_credits=round(sum(p.credits for p in players), 1),
            predicted_total_fp=round(sum(p.predicted_fp for p in players) + cap.player.predicted_fp
                                     + 0.5 * vc.player.predicted_fp, 1),
            team_ceiling=round(sum(p.ceiling for p in players), 1),
            team_confidence=conf,
            team_split=dict(Counter(p.team for p in players)),
            role_split={r: sum(1 for p in players if p.role == r) for r in ("WK", "BAT", "AR", "BOWL")},
            solver_used=res.solver, solve_time_ms=res.solve_time_ms,
        )

    async def generate_team(self, match_id: str, mode: str, count: int, user: User,
                            override_toss: Optional[dict] = None,
                            override_xi: Optional[Dict[str, List[str]]] = None) -> PredictTeamResponse:
        ms = await self._scores(match_id, override_toss)
        pool = self._pool(ms, override_xi)
        opts: List[OptPlayer] = [p.to_opt() for p in pool]
        score_for_mode(opts, mode)
        teams: List[TeamResult] = []
        previous: List[set] = []
        min_diff = 1 if mode == "grand_league" else 0
        for _ in range(count):
            res = solve_team(opts, previous=previous, max_overlap=9, min_differentials=min_diff)
            if res is None:
                if not teams:
                    raise _err(400, "OPTIMIZER_INFEASIBLE", "No valid Dream11 team could be built",
                               solver="lp", fallback_attempted=True)
                break
            teams.append(self._team_result(ms, res, mode, index=len(teams)))
            previous.append({p.player_id for p in res.players})

        pred = await self._persist(ms, mode, user, teams)
        return PredictTeamResponse(
            prediction_id=pred.id, match_id=match_id, mode=mode, generated_at=datetime.now(timezone.utc),
            match_phase=ms.phase, playing_xi_confirmed=ms.xi_confirmed, model_version=ms.model_version,
            teams=teams, ensemble_weights=ms.weights,
            pool=[_pp(p, False) for p in pool],
        )

    async def _persist(self, ms: MatchScores, mode: str, user: User, teams: List[TeamResult]) -> Prediction:
        pred = Prediction(match_id=ms.match.id, user_id=user.id, mode=mode, ensemble_weights=ms.weights,
                          match_phase=ms.phase, is_live=ms.phase == "live")
        self.db.add(pred)
        await self.db.flush()
        for rank, p in enumerate(ms.players, start=1):
            self.db.add(PredictedPlayer(
                prediction_id=pred.id, player_id=uuid.UUID(p.player_id), ensemble_score=p.ensemble_score,
                ml_score=p.ml_score, rules_score=p.rules_score, form_score=p.form_score, live_score=p.live_score,
                fp_predicted=p.predicted_fp, fp_ceiling=p.fp_ceiling, fp_floor=p.fp_floor,
                confidence=p.confidence, rank=rank, rules_fired=[r["id"] for r in p.rules_fired]))
            for r in p.rules_fired:
                self.db.add(RuleTrigger(prediction_id=pred.id, player_id=uuid.UUID(p.player_id),
                                        rule_ext_id=r["id"], impact_applied=r["impact"]))
        for t in teams:
            rt = RecommendedTeam(prediction_id=pred.id, mode=mode, captain_id=t.captain.player_id,
                                 vice_captain_id=t.vice_captain.player_id, total_credits=t.total_credits,
                                 predicted_total_fp=t.predicted_total_fp, solver_used=t.solver_used)
            self.db.add(rt)
            await self.db.flush()
            for p in t.players:
                self.db.add(TeamPlayer(team_id=rt.id, player_id=p.player_id, role=p.role, credits=p.credits))
        await self.db.commit()
        return pred

    async def get_captain_options(self, match_id: str, mode: str, user: User) -> CaptainResponse:
        ms = await self._scores(match_id)
        opts = [p.to_opt() for p in ms.players]
        score_for_mode(opts, mode)
        res = solve_team(opts, min_differentials=1 if mode == "grand_league" else 0)
        if res is None:
            raise _err(400, "OPTIMIZER_INFEASIBLE", "No valid team for captain selection")
        picks = recommend(res.players, mode)
        return CaptainResponse(recommendations=[
            CaptainOption(rank=i + 1, player_id=uuid.UUID(c.player.player_id), full_name=c.player.full_name,
                          type=c.type, ceiling_score=c.player.ceiling, confidence=c.player.confidence,
                          ownership_estimate=f"{c.player.ownership:.0f}%", predicted_fp=c.player.predicted_fp,
                          reasoning=c.reasoning)
            for i, c in enumerate(picks)])

    async def get_differentials(self, match_id: str) -> DifferentialsResponse:
        ms = await self._scores(match_id)
        diffs = [p for p in ms.players if p.is_differential]
        if len(diffs) < 3:  # top up with the best low-owned ceilings
            rest = sorted((p for p in ms.players if p.ownership < 30 and p not in diffs),
                          key=lambda p: -(p.fp_ceiling - p.ownership))
            diffs += rest[:3 - len(diffs)]
        diffs = sorted(diffs, key=lambda p: -(p.fp_ceiling * 0.6 + p.predicted_fp * 0.4))[:5]
        out = []
        for p in diffs:
            reasons = []
            if p.fp_ceiling >= 70:
                reasons.append(f"{p.fp_ceiling:.0f}-pt ceiling")
            if p.fp_avg_3 > p.fp_avg_10 + 5:
                reasons.append(f"trending up ({p.fp_avg_3:.0f} avg last 3)")
            if p.rules_fired:
                reasons.append(p.rules_fired[0]["description"].split(" — ")[0].rstrip("."))
            if p.features.get("venue_matches", 0) >= 2 and p.features["venue_fp_avg"] > p.fp_avg_10:
                reasons.append(f"averages {p.features['venue_fp_avg']:.0f} at this venue")
            reasons.append(f"only ~{p.ownership:.0f}% expected ownership")
            out.append(DifferentialOut(
                player_id=uuid.UUID(p.player_id), full_name=p.full_name, role=p.role, team=p.team,
                credits=p.credits, ownership_estimate=f"{p.ownership:.0f}%", ceiling_score=p.fp_ceiling,
                fp_avg_5=p.fp_avg_5, predicted_fp=p.predicted_fp, reason="; ".join(reasons).capitalize()))
        return DifferentialsResponse(differentials=out)

    async def explain_player(self, match_id: str, player_id: uuid.UUID, depth: str = "full") -> ExplainResponse:
        ms = await self._scores(match_id)
        ps = ms.by_id.get(str(player_id))
        if ps is None:
            raise _err(404, "PLAYER_NOT_FOUND", "Player is not in this match squad")
        if depth == "full":
            text, factors, source = await explain(ps, ms.match, ms.match.venue_name)
        else:
            factors = build_factors(ps, ms.match, ms.match.venue_name)
            text, source = template_explanation(ps, factors), "template"
            factors = factors[:2]
        return ExplainResponse(
            player_id=player_id, full_name=ps.full_name, role=ps.role, team=ps.team, match_id=match_id,
            explanation=text, explanation_source=source, depth=depth,
            factors=[ExplanationFactor(**f) for f in factors],
            rules_fired=[r["id"] for r in ps.rules_fired] if depth == "full" else [],
            rules_detail=ps.rules_fired if depth == "full" else [],
            confidence=ps.confidence, confidence_label=confidence_label(ps.confidence),
            predicted_fp=ps.predicted_fp, fp_ceiling=ps.fp_ceiling, fp_floor=ps.fp_floor,
            ownership_estimate=f"{ps.ownership:.0f}%",
            ensemble_breakdown=({f"{k}_score_norm": v for k, v in ps.components_norm.items()} | {
                "ml_points": ps.ml_score, "rules_points": ps.rules_score, "form_points": ps.form_score}
            ) if depth == "full" else None,
        )
