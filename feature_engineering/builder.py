"""
Leakage-free feature computation.

Every feature for a (player, match) row is computed only from that player's
matches strictly before it (pandas `shift(1)` before every rolling window).
Inference uses the exact same code: upcoming fixtures are appended as rows with
no fantasy points, so they receive features from the complete history —
training and serving can never drift apart.
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import Delivery, Match, Player, PlayerMatchPerformance, Venue

FORMAT_GROUP = {
    **{t: "T20" for t in ("T20", "IT20", "IPL", "BBL", "PSL", "CPL", "WPL")},
    **{t: "ODI" for t in ("ODI", "ODM", "WOD")},
    **{t: "Test" for t in ("Test", "MDM", "NTB", "WTB")},
}

STAGE_IMPORTANCE = {
    "final": 1.0, "eliminator": 0.85, "qualifier 2": 0.85, "2nd qualifier": 0.85,
    "semi final": 0.85, "semi-final": 0.85, "qualifier 1": 0.7, "1st qualifier": 0.7,
    "3rd place play-off": 0.6,
}

FEATURE_COLUMNS: List[str] = [
    # form
    "fp_avg_3", "fp_avg_5", "fp_avg_10", "fp_std_10", "fp_ceiling", "fp_floor",
    "fp_consistency", "fp_30plus_rate", "career_fp_avg", "career_matches",
    # batting
    "avg_runs_5", "avg_runs_10", "avg_sr_5", "avg_fours_5", "avg_sixes_5", "avg_bat_pos_5", "dismissal_rate_10",
    # bowling
    "avg_wickets_5", "avg_wickets_10", "avg_economy_5", "avg_overs_5", "dot_ball_rate_5",
    # venue
    "venue_fp_avg", "venue_matches", "venue_avg_first_innings", "venue_chasing_win_pct",
    # matchup
    "sr_vs_spin", "sr_vs_pace", "opp_spin_share", "expected_matchup_sr", "matchup_confidence",
    # context
    "is_chasing", "is_home", "match_importance", "days_since_last_match", "opposition_fp_allowed",
    # encodings
    "role_wk", "role_bat", "role_ar", "role_bowl", "bats_left", "bowls_spin", "bowls_pace",
    "pitch_batting", "pitch_spin", "pitch_pace",
]


@dataclass
class Frames:
    perf: pd.DataFrame          # one row per player per match
    matchup: pd.DataFrame       # per (match, player): balls/runs/outs vs spin & pace
    team_bowl: pd.DataFrame     # per (match, team): spin share of balls bowled
    venue_match: pd.DataFrame   # per match: venue, first-innings total, chase won
    players: pd.DataFrame       # player attributes
    death_share: dict = None    # bowler_id -> share of balls bowled at the death
    # Derived once (see prepare): team home venue, role priors, team-match FP totals
    home: pd.Series = None
    role_mean: pd.Series = None
    gmean: float = 25.0
    team_fp: pd.DataFrame = None

    def prepare(self) -> "Frames":
        p = self.perf
        self.home = p.groupby("team").venue_name.agg(lambda s: s.mode().iat[0] if len(s.mode()) else None)
        roles = p[["player_id", "fp"]].merge(self.players[["player_id", "role"]], on="player_id", how="left")
        roles["role"] = roles.role.fillna("BAT")
        self.role_mean = roles.groupby("role").fp.mean()
        self.gmean = float(p.fp.mean()) if len(p) else 25.0
        self.team_fp = (p.groupby(["match_id", "team", "opposition", "match_date"], dropna=False).fp.sum()
                        .reset_index())
        return self


CACHE_FILE = Path(settings.FEATURE_STORE_PATH) / "frames.pkl"


def save_frames_cache(frames: Frames) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_FILE.with_suffix(".tmp")
    with tmp.open("wb") as f:
        pickle.dump(frames, f, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(CACHE_FILE)


def drop_frames_cache() -> None:
    CACHE_FILE.unlink(missing_ok=True)


async def load_frames(db: AsyncSession, use_cache: bool = True) -> Frames:
    """Aggregated history for feature building. Served from data/features/frames.pkl when the
    feature pipeline has written it (dropped after every ingestion), else computed from SQL."""
    if use_cache and CACHE_FILE.exists():
        try:
            with CACHE_FILE.open("rb") as f:
                return pickle.load(f)
        except Exception:
            drop_frames_cache()
    return await _load_frames_sql(db)


async def _load_frames_sql(db: AsyncSession) -> Frames:
    P, M = PlayerMatchPerformance, Match
    rows = (await db.execute(
        select(P.match_id, P.player_id, P.match_date, P.match_type, P.venue_name, P.team, P.opposition,
               P.is_chasing, P.runs_scored, P.balls_faced, P.fours, P.sixes, P.did_bat, P.is_dismissed,
               P.batting_position, P.balls_bowled, P.runs_conceded, P.wickets_taken, P.dot_balls,
               P.fantasy_points, M.event_stage)
        .join(M, M.id == P.match_id)
    )).all()
    perf = pd.DataFrame(rows, columns=[
        "match_id", "player_id", "match_date", "match_type", "venue_name", "team", "opposition",
        "is_chasing", "runs", "balls", "fours", "sixes", "did_bat", "dismissed", "batting_position",
        "balls_bowled", "runs_conceded", "wickets", "dots", "fp", "event_stage"])

    prow = (await db.execute(select(
        Player.id, Player.cricsheet_key, Player.full_name, Player.primary_role, Player.batting_style,
        Player.bowler_type, Player.current_team, Player.base_credits))).all()
    players = pd.DataFrame(prow, columns=["player_id", "cricsheet_key", "full_name", "role", "batting_style",
                                          "bowler_type", "current_team", "base_credits"])

    from sqlalchemy.orm import aliased
    D = Delivery
    BP = aliased(Player)                 # bowler — styles live on the player (inferred or from the API)
    spin = BP.bowler_type.like("spin%")
    legal_bat = D.is_wide.is_(False)
    mrows = (await db.execute(
        select(D.match_id, D.batter_id,
               func.sum(case((and_(spin, legal_bat), 1), else_=0)),
               func.sum(case((spin, D.runs_batter), else_=0)),
               func.sum(case((and_(spin, D.wicket_player_out == D.batter), 1), else_=0)),
               func.sum(case((and_(~spin, legal_bat), 1), else_=0)),
               func.sum(case((~spin, D.runs_batter), else_=0)),
               func.sum(case((and_(~spin, D.wicket_player_out == D.batter), 1), else_=0)))
        .join(BP, BP.id == D.bowler_id).where(BP.bowler_type.is_not(None))
        .group_by(D.match_id, D.batter_id)
    )).all()
    matchup = pd.DataFrame(mrows, columns=["match_id", "player_id", "b_spin", "r_spin", "o_spin",
                                           "b_pace", "r_pace", "o_pace"]).dropna(subset=["player_id"])

    from backend.models import Innings
    I = Innings
    trows = (await db.execute(
        select(D.match_id, I.bowling_team,
               func.sum(case((and_(spin, ~D.is_wide, ~D.is_no_ball), 1), else_=0)),
               func.sum(case((and_(~D.is_wide, ~D.is_no_ball), 1), else_=0)))
        .join(I, I.id == D.innings_id).join(BP, BP.id == D.bowler_id).where(BP.bowler_type.is_not(None))
        .group_by(D.match_id, I.bowling_team)
    )).all()
    team_bowl = pd.DataFrame(trows, columns=["match_id", "team", "spin_balls", "balls"])
    team_bowl["spin_share"] = team_bowl.spin_balls / team_bowl.balls.replace(0, np.nan)

    vrows = (await db.execute(
        select(M.id, M.venue_name, M.match_date, M.match_winner, I.total_runs, I.batting_team, I.innings_number)
        .join(I, I.match_id == M.id)
    )).all()
    vdf = pd.DataFrame(vrows, columns=["match_id", "venue_name", "match_date", "winner", "runs", "batting_team", "inn"])
    first = vdf[vdf.inn == 1][["match_id", "venue_name", "match_date", "runs"]].rename(columns={"runs": "first_innings"})
    second = vdf[vdf.inn == 2][["match_id", "batting_team", "winner"]]
    second = second.assign(chase_won=(second.batting_team == second.winner).astype(float))[["match_id", "chase_won"]]
    venue_match = first.merge(second, on="match_id", how="left")

    vt = (await db.execute(select(Venue.name, Venue.pitch_type))).all()
    pitch = dict(vt)
    venue_match["pitch_type"] = venue_match.venue_name.map(pitch)
    perf["pitch_type"] = perf.venue_name.map(pitch)

    drows = (await db.execute(
        select(D.bowler_id, func.count(), func.sum(case((D.phase == "death", 1), else_=0)))
        .where(D.bowler_id.is_not(None)).group_by(D.bowler_id))).all()
    death = {b: (d or 0) / n for b, n, d in drows if n}
    return Frames(perf, matchup, team_bowl, venue_match, players, death).prepare()


def _shifted_roll(df: pd.DataFrame, key, col: str, window: int, fn: str = "mean", q: float | None = None) -> pd.Series:
    prev = df.groupby(key, sort=False)[col].shift(1)
    grp = prev.groupby([df[k] for k in key] if isinstance(key, list) else df[key], sort=False)
    if fn == "quantile":
        out = grp.rolling(window, min_periods=1).quantile(q)
    else:
        out = getattr(grp.rolling(window, min_periods=1), fn)()
    return out.reset_index(level=list(range(out.index.nlevels - 1)), drop=True).reindex(df.index)


def build_feature_frame(frames: Frames, pending: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Return perf (+ pending) rows with FEATURE_COLUMNS computed from prior matches only.

    `pending` rows need: match_id, player_id, match_date, match_type, venue_name, team,
    opposition, is_chasing (bool or NaN), event_stage, pitch_type — and fp = NaN.
    """
    has_pending = pending is not None and len(pending) > 0
    # Inference only needs the squad players' own histories; team / venue aggregates come from `frames`
    perf = (frames.perf[frames.perf.player_id.isin(set(pending.player_id))] if has_pending else frames.perf).copy()
    perf["is_pending"] = False
    if has_pending:
        pend = pending.copy()
        pend["is_pending"] = True
        for c in perf.columns:
            if c not in pend.columns:
                pend[c] = np.nan
        perf = pd.concat([perf, pend[perf.columns]], ignore_index=True)

    df = perf.merge(frames.players[["player_id", "role", "batting_style", "bowler_type"]], on="player_id", how="left")
    df["match_date"] = pd.to_datetime(df.match_date)
    df["fmt"] = df.match_type.map(FORMAT_GROUP).fillna(df.match_type)
    df = df.sort_values(["player_id", "fmt", "match_date", "match_id"]).reset_index(drop=True)
    key = ["player_id", "fmt"]
    num = ["runs", "balls", "fours", "sixes", "balls_bowled", "runs_conceded", "wickets", "dots", "batting_position"]
    for c in num:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["dismissed_f"] = df.dismissed.astype(float)
    df["fp"] = pd.to_numeric(df.fp, errors="coerce")

    g = df.groupby(key, sort=False)
    out = pd.DataFrame(index=df.index)

    # ── Form ──────────────────────────────────────────────────────────────
    for w in (3, 5, 10):
        out[f"fp_avg_{w}"] = _shifted_roll(df, key, "fp", w)
    out["fp_std_10"] = _shifted_roll(df, key, "fp", 10, "std")
    out["fp_ceiling"] = _shifted_roll(df, key, "fp", 10, "quantile", 0.9)
    out["fp_floor"] = _shifted_roll(df, key, "fp", 10, "quantile", 0.1)
    df["_30p"] = (df.fp >= 30).astype(float).where(df.fp.notna())
    out["fp_30plus_rate"] = _shifted_roll(df, key, "_30p", 10)
    out["career_matches"] = g.cumcount().astype(float)
    prev_fp = g.fp.shift(1)
    out["career_fp_avg"] = prev_fp.groupby([df.player_id, df.fmt]).expanding().mean().reset_index(level=[0, 1], drop=True).reindex(df.index)

    # ── Batting ───────────────────────────────────────────────────────────
    out["avg_runs_5"] = _shifted_roll(df, key, "runs", 5)
    out["avg_runs_10"] = _shifted_roll(df, key, "runs", 10)
    r5 = _shifted_roll(df, key, "runs", 5, "sum")
    b5 = _shifted_roll(df, key, "balls", 5, "sum")
    out["avg_sr_5"] = (r5 / b5.replace(0, np.nan) * 100)
    out["avg_fours_5"] = _shifted_roll(df, key, "fours", 5)
    out["avg_sixes_5"] = _shifted_roll(df, key, "sixes", 5)
    out["avg_bat_pos_5"] = _shifted_roll(df, key, "batting_position", 5)
    out["dismissal_rate_10"] = _shifted_roll(df, key, "dismissed_f", 10)

    # ── Bowling ───────────────────────────────────────────────────────────
    out["avg_wickets_5"] = _shifted_roll(df, key, "wickets", 5)
    out["avg_wickets_10"] = _shifted_roll(df, key, "wickets", 10)
    rc5 = _shifted_roll(df, key, "runs_conceded", 5, "sum")
    bb5 = _shifted_roll(df, key, "balls_bowled", 5, "sum")
    out["avg_economy_5"] = rc5 / (bb5 / 6).replace(0, np.nan)
    out["avg_overs_5"] = _shifted_roll(df, key, "balls_bowled", 5) / 6
    out["dot_ball_rate_5"] = _shifted_roll(df, key, "dots", 5, "sum") / bb5.replace(0, np.nan)

    # ── Venue (player-at-venue, and venue-level) ──────────────────────────
    vkey = ["player_id", "fmt", "venue_name"]
    df_v = df.copy()
    df_v["venue_name"] = df_v.venue_name.fillna("?")
    gv = df_v.groupby(vkey, sort=False)
    vprev = gv.fp.shift(1)
    out["venue_fp_avg"] = vprev.groupby([df_v[k] for k in vkey]).expanding().mean().reset_index(level=[0, 1, 2], drop=True).reindex(df.index)
    out["venue_matches"] = gv.cumcount().astype(float)

    vm = frames.venue_match.copy()
    vm["match_date"] = pd.to_datetime(vm.match_date)
    if pending is not None and len(pending):
        extra = pending[["match_id", "venue_name", "match_date"]].drop_duplicates("match_id")
        extra = extra[~extra.match_id.isin(vm.match_id)].assign(match_date=lambda x: pd.to_datetime(x.match_date))
        vm = pd.concat([vm, extra], ignore_index=True)
    vm = vm.sort_values(["venue_name", "match_date", "match_id"]).reset_index(drop=True)
    gvm = vm.groupby("venue_name", sort=False)
    vm["venue_avg_first_innings"] = gvm.first_innings.transform(lambda s: s.shift(1).expanding().mean())
    vm["venue_chasing_win_pct"] = gvm.chase_won.transform(lambda s: s.shift(1).expanding().mean())
    df = df.merge(vm[["match_id", "venue_avg_first_innings", "venue_chasing_win_pct"]], on="match_id", how="left")
    out[["venue_avg_first_innings", "venue_chasing_win_pct"]] = df[["venue_avg_first_innings", "venue_chasing_win_pct"]]

    # ── Matchup (batter vs spin / pace, opposition attack mix) ────────────
    mu = df[["match_id", "player_id"]].merge(frames.matchup, on=["match_id", "player_id"], how="left").fillna(0)
    for c in ("b_spin", "r_spin", "o_spin", "b_pace", "r_pace", "o_pace"):
        df[c] = mu[c].values
        df[f"cum_{c}"] = df.groupby(key, sort=False)[c].transform(lambda s: s.shift(1).cumsum())
    out["sr_vs_spin"] = df.cum_r_spin / df.cum_b_spin.replace(0, np.nan) * 100
    out["sr_vs_pace"] = df.cum_r_pace / df.cum_b_pace.replace(0, np.nan) * 100
    out["matchup_confidence"] = ((df.cum_b_spin.fillna(0) + df.cum_b_pace.fillna(0)) / 100).clip(0, 1)

    tb = frames.team_bowl.merge(frames.venue_match[["match_id", "match_date"]], on="match_id", how="left")
    if pending is not None and len(pending):
        pt = pending[["match_id", "team", "match_date"]].drop_duplicates(["match_id", "team"])
        tb = pd.concat([tb, pt], ignore_index=True)
    tb["match_date"] = pd.to_datetime(tb.match_date)
    tb = tb.sort_values(["team", "match_date", "match_id"]).reset_index(drop=True)
    tb["opp_spin_share"] = tb.groupby("team", sort=False).spin_share.transform(lambda s: s.shift(1).rolling(5, min_periods=1).mean())
    tb = tb.drop_duplicates(["match_id", "team"])
    df = df.merge(tb[["match_id", "team", "opp_spin_share"]].rename(columns={"team": "opposition"}),
                  on=["match_id", "opposition"], how="left")
    out["opp_spin_share"] = df.opp_spin_share.values

    # ── Opposition strength: avg FP the opposition concedes per match ─────
    pairs = frames.team_fp.rename(columns={"fp": "fp_scored"})
    if has_pending:
        extra = pending[["match_id", "team", "opposition", "match_date"]].drop_duplicates(["match_id", "team"])
        pairs = pd.concat([pairs, extra.assign(fp_scored=np.nan)], ignore_index=True)
    pairs = pairs.assign(match_date=pd.to_datetime(pairs.match_date))
    pairs = pairs.sort_values(["opposition", "match_date", "match_id"]).reset_index(drop=True)
    pairs["opposition_fp_allowed"] = pairs.groupby("opposition", sort=False).fp_scored.transform(
        lambda s: s.shift(1).rolling(10, min_periods=1).mean()) / 11
    df = df.merge(pairs[["match_id", "team", "opposition_fp_allowed"]], on=["match_id", "team"], how="left")
    out["opposition_fp_allowed"] = df.opposition_fp_allowed.values

    # ── Context ───────────────────────────────────────────────────────────
    ch = df.is_chasing.map({True: 1.0, False: 0.0, 1: 1.0, 0: 0.0})
    out["is_chasing"] = ch.fillna(0.5).values
    home = frames.home
    out["is_home"] = (df.venue_name == df.team.map(home)).astype(float).values
    stage = df.event_stage.fillna("").str.lower()
    out["match_importance"] = stage.map(lambda s: next((v for k, v in STAGE_IMPORTANCE.items() if k in s), 0.5)).values
    last = df.groupby(key, sort=False).match_date.shift(1)
    out["days_since_last_match"] = (df.match_date - last).dt.days.clip(upper=30).fillna(30).values

    # ── Encodings ─────────────────────────────────────────────────────────
    role = df.role.fillna("BAT")
    for r in ("wk", "bat", "ar", "bowl"):
        out[f"role_{r}"] = (role.str.upper() == r.upper()).astype(float).values
    out["bats_left"] = df.batting_style.fillna("").str.startswith("Left").astype(float).values
    bt = df.bowler_type.fillna("")
    out["bowls_spin"] = bt.str.startswith("spin").astype(float).values
    out["bowls_pace"] = bt.str.startswith("pace").astype(float).values
    pt = df.pitch_type.fillna("")
    for p in ("batting", "spin", "pace"):
        out[f"pitch_{p}"] = (pt == p).astype(float).values

    # ── Fallbacks: own → role prior → global ──────────────────────────────
    out["role"] = role.values
    gmean = frames.gmean
    role_prior = role.map(frames.role_mean).fillna(gmean)
    for c in ("fp_avg_3", "fp_avg_5", "fp_avg_10", "career_fp_avg", "venue_fp_avg"):
        out[c] = out[c].fillna(out["career_fp_avg"]).fillna(role_prior)
    out["fp_ceiling"] = out.fp_ceiling.fillna(out.fp_avg_10 * 1.9)
    out["fp_floor"] = out.fp_floor.fillna(out.fp_avg_10 * 0.15)
    out["fp_std_10"] = out.fp_std_10.fillna(out.fp_avg_10 * 0.7)
    out["fp_consistency"] = (out.fp_std_10 / out.fp_avg_10.replace(0, np.nan)).clip(0, 10).fillna(1.0)
    out["avg_sr_5"] = out.avg_sr_5.fillna(110.0)
    out["avg_economy_5"] = out.avg_economy_5.fillna(9.0)
    out["dot_ball_rate_5"] = out.dot_ball_rate_5.fillna(0.0)
    overall_sr = out.avg_sr_5
    out["sr_vs_spin"] = out.sr_vs_spin.fillna(overall_sr)
    out["sr_vs_pace"] = out.sr_vs_pace.fillna(overall_sr)
    out["opp_spin_share"] = out.opp_spin_share.fillna(0.35)
    out["expected_matchup_sr"] = out.opp_spin_share * out.sr_vs_spin + (1 - out.opp_spin_share) * out.sr_vs_pace
    out["venue_avg_first_innings"] = out.venue_avg_first_innings.fillna(out.venue_avg_first_innings.mean()).fillna(170.0)
    out["venue_chasing_win_pct"] = out.venue_chasing_win_pct.fillna(0.5)
    out["opposition_fp_allowed"] = out.opposition_fp_allowed.fillna(out.opposition_fp_allowed.mean()).fillna(gmean)
    out = out.fillna(0.0)

    result = pd.concat([df[["match_id", "player_id", "match_date", "match_type", "venue_name", "team",
                            "opposition", "fp", "is_pending"]], out], axis=1)
    result["low_data"] = result.career_matches < 3
    return result
