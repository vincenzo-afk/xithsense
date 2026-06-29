# Data Sources

## Primary Source: Cricsheet

| Property | Value |
|----------|-------|
| URL | https://cricsheet.org/downloads/all_json.zip |
| Format | JSON v1.2.0 (ball-by-ball) |
| Total matches | 22,062 (as of June 2026) |
| Date range | 2001-12-19 to 2026-06-15 |
| Match types | T20 (5,428), ODI (3,145), NTB (1,509), CCH (1,420), IPL (1,243), Test (904), BBL (662), ODM (478), CPL (407), PSL (357), IT20 (320), IPT (106), WOD (96), WPL (88), WTB (82), MDM (17) |
| Gender split | 17,649 male, 4,413 female |
| Team type | 11,770 club, 10,292 international |
| License | Cricsheet open data license |
| Update frequency | New matches added within 24–48h of completion |

### File Structure (per match)
```
{match_id}.json
├── meta.data_version     "1.2.0"
├── meta.created          ISO date
├── info.match_type       T20 | ODI | Test | ...
├── info.teams            [team_a, team_b]
├── info.venue            venue name string
├── info.toss             {winner, decision}
├── info.outcome          {winner, by}
├── info.season           year string
├── info.event            {name, stage}
├── info.player_of_match  [player_key]
├── info.gender           male | female
├── info.team_type        club | international
└── innings[]
    ├── team              team name
    ├── powerplays[]      {from, to, type}
    └── overs[]
        ├── over          integer
        └── deliveries[]
            ├── actual_delivery   "0.1" to "19.6"
            ├── batter            player name
            ├── bowler            player name
            ├── non_striker       player name
            ├── runs.batter       integer
            ├── runs.extras       integer
            ├── runs.total        integer
            ├── extras?           {wides, no_balls, byes, leg_byes}
            ├── wickets?[]        {player_out, kind, fielders}
            └── review?           {by, umpire, batter, decision, type}
```

## Secondary Sources (Phase 2)

| Source | Type | Purpose |
|--------|------|---------|
| OpenWeatherMap API | REST | Pre-match weather (temperature, humidity, wind, rain probability) |
| ESPNcricinfo | Scrape (unofficial) | Playing XI confirmation, squad lists |
| Cricbuzz | Scrape (unofficial) | Real-time score updates (Phase 2) |
| Twitter/X | Scrape | Official team XI announcements (Phase 2) |
| Admin manual entry | API | Playing XI when scraping unavailable |

## Data Download Script

```bash
# Download latest Cricsheet data
curl -L https://cricsheet.org/downloads/all_json.zip -o data/raw/all_json.zip

# Extract
unzip -o data/raw/all_json.zip -d data/raw/all_json/

# Verify count
ls data/raw/all_json/*.json | wc -l
```
