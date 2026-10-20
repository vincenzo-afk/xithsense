"""
Infer pace vs spin for bowlers from ball-by-ball patterns (Cricsheet has no bowling styles).

A logistic-regression classifier is trained on bowlers whose style is common
knowledge (labels below) using behavioural signals visible in the deliveries:
stumping share of wickets, powerplay / death-overs usage, bowled+LBW share,
economy, wides per ball and dot-ball rate. Styles from the live API
(style_source="api") or metadata always take precedence and are never overwritten.
"""
from __future__ import annotations

import logging
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import case, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Delivery, Player

logger = logging.getLogger(__name__)

SPIN = [
    "Rashid Khan", "YS Chahal", "R Ashwin", "RA Jadeja", "Kuldeep Yadav", "SP Narine", "Shakib Al Hasan",
    "Imran Tahir", "A Zampa", "Mujeeb Ur Rahman", "Noor Ahmad", "M Theekshana", "PWH de Silva", "Washington Sundar",
    "AR Patel", "KH Pandya", "Mohammad Nabi", "Shadab Khan", "MJ Santner", "Mehedi Hasan Miraz", "NM Lyon",
    "Harbhajan Singh", "PP Chawla", "A Mishra", "CV Varun", "Ravi Bishnoi", "AU Rashid", "T Shamsi", "MM Ali",
    "KA Maharaj", "Mohammad Nawaz", "R Sai Kishore", "Abrar Ahmed", "Wanindu Hasaranga", "Sufiyan Muqeem",
    "IS Sodhi", "AC Agar", "Taijul Islam",
]
PACE = [
    "JJ Bumrah", "B Kumar", "TA Boult", "MA Starc", "PJ Cummins", "Mohammed Shami", "JR Hazlewood", "K Rabada",
    "Shaheen Shah Afridi", "Haris Rauf", "TG Southee", "JM Anderson", "SCJ Broad", "Mohammed Siraj", "A Nortje",
    "LH Ferguson", "Mustafizur Rahman", "DL Chahar", "Arshdeep Singh", "Avesh Khan", "HV Patel", "Mohammad Amir",
    "Naseem Shah", "CR Woakes", "MA Wood", "JC Archer", "DW Steyn", "L Ngidi", "M Pathirana", "Umran Malik",
    "T Natarajan", "Sandeep Sharma", "UT Yadav", "I Sharma", "MM Sharma", "DJ Bravo", "AD Russell", "HH Pandya",
    "BA Stokes", "SM Curran", "MP Stoinis", "Taskin Ahmed", "Fazalhaq Farooqi", "Naveen-ul-Haq", "CJ Jordan",
    "Harshit Rana", "Yash Dayal", "M Prasidh Krishna", "Mukesh Kumar", "KK Ahmed",
]

FEATURES = ["stump_share", "pp_share", "death_share", "bowled_lbw_share", "economy", "wide_rate", "dot_rate",
            "caught_share"]


async def bowler_stats(db: AsyncSession, min_balls: int = 120) -> pd.DataFrame:
    D = Delivery
    legal = (D.is_wide.is_(False)) & (D.is_no_ball.is_(False))
    rows = (await db.execute(
        select(D.bowler_id,
               func.sum(case((legal, 1), else_=0)),
               func.sum(case((legal & (D.phase == "powerplay"), 1), else_=0)),
               func.sum(case((legal & (D.phase == "death"), 1), else_=0)),
               func.sum(D.runs_batter + D.extra_wides + D.extra_no_balls),
               func.sum(case((D.is_wide.is_(True), 1), else_=0)),
               func.sum(case((legal & (D.runs_total == 0), 1), else_=0)),
               func.sum(case((D.wicket_kind.in_(("caught", "caught and bowled", "bowled", "lbw", "stumped",
                                                 "hit wicket")), 1), else_=0)),
               func.sum(case((D.wicket_kind == "stumped", 1), else_=0)),
               func.sum(case((D.wicket_kind.in_(("bowled", "lbw")), 1), else_=0)),
               func.sum(case((D.wicket_kind == "caught", 1), else_=0)))
        .where(D.phase.in_(("powerplay", "middle", "death")), D.bowler_id.is_not(None))
        .group_by(D.bowler_id)
    )).all()
    df = pd.DataFrame(rows, columns=["player_id", "balls", "pp", "death", "runs", "wides", "dots", "wkts", "stumped",
                                     "bowled_lbw", "caught"])
    df = df[df.balls >= min_balls].copy()
    w = df.wkts.replace(0, np.nan)
    df["stump_share"] = (df.stumped / w).fillna(0)
    df["bowled_lbw_share"] = (df.bowled_lbw / w).fillna(0.3)
    df["caught_share"] = (df.caught / w).fillna(0.6)
    df["pp_share"] = df.pp / df.balls
    df["death_share"] = df.death / df.balls
    df["economy"] = df.runs / (df.balls / 6)
    df["wide_rate"] = df.wides / df.balls
    df["dot_rate"] = df.dots / df.balls
    return df


async def infer_bowling_styles(db: AsyncSession) -> Dict[str, float]:
    """Fit on labelled bowlers, write bowler_type 'spin' / 'pace' for unlabelled players. Returns metrics."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    stats = await bowler_stats(db)
    if stats.empty:
        return {"labelled": 0, "inferred": 0}
    players = pd.DataFrame((await db.execute(select(Player.id, Player.cricsheet_key, Player.full_name,
                                                    Player.bowler_type, Player.style_source))).all(),
                           columns=["player_id", "key", "name", "bowler_type", "style_source"])
    df = stats.merge(players, on="player_id", how="left")
    label = {n: 1 for n in SPIN} | {n: 0 for n in PACE}
    df["label"] = df.key.map(label)
    known = df[df.style_source.isin(["api", "metadata"]) & df.bowler_type.notna()]
    df.loc[known.index, "label"] = known.bowler_type.str.startswith("spin").astype(float)
    train = df[df.label.notna()]
    if train.label.nunique() < 2 or len(train) < 20:
        logger.warning("Not enough labelled bowlers (%d) to infer styles", len(train))
        return {"labelled": int(len(train)), "inferred": 0}
    model = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000, class_weight="balanced"))
    cv = cross_val_score(model, train[FEATURES], train.label.astype(int), cv=min(5, int(train.label.value_counts().min())))
    model.fit(train[FEATURES], train.label.astype(int))
    df["p_spin"] = model.predict_proba(df[FEATURES])[:, 1]

    todo = df[~df.style_source.isin(["api", "metadata"])]
    spin_ids = [pid for pid in todo[todo.p_spin >= 0.5].player_id]
    pace_ids = [pid for pid in todo[todo.p_spin < 0.5].player_id]
    for ids, t in ((spin_ids, "spin"), (pace_ids, "pace")):
        for i in range(0, len(ids), 500):
            await db.execute(update(Player).where(Player.id.in_(ids[i:i + 500]))
                             .values(bowler_type=t, style_source="inferred"))
    await db.commit()
    metrics = {"labelled": int(len(train)), "cv_accuracy": round(float(cv.mean()), 3),
               "inferred_spin": len(spin_ids), "inferred_pace": len(pace_ids)}
    logger.info("Bowling styles inferred: %s", metrics)
    return metrics
