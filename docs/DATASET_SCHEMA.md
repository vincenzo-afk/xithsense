# Dataset Schema

## Cricsheet JSON v1.2.0 — Complete Field Reference

Source: https://cricsheet.org/format/json/

---

## Top-Level Structure

```json
{
  "meta": { ... },
  "info": { ... },
  "innings": [ ... ]
}
```

---

## `meta` Object

| Field | Type | Example | Description |
|-------|------|---------|-------------|
| `data_version` | string | `"1.2.0"` | Cricsheet schema version |
| `created` | string (date) | `"2026-05-25"` | When this file was created |
| `revision` | integer | `2` | Revision number of this file |

---

## `info` Object

| Field | Type | Example | Always Present |
|-------|------|---------|---------------|
| `balls_per_over` | integer | `6` | ✅ |
| `city` | string | `"Ahmedabad"` | Sometimes |
| `dates` | string[] | `["2026-05-25"]` | ✅ |
| `event.name` | string | `"Indian Premier League"` | Sometimes |
| `event.stage` | string | `"Final"` | Sometimes |
| `event.match_number` | integer | `74` | Sometimes |
| `gender` | string | `"male"` | ✅ |
| `match_type` | string | `"T20"` | ✅ |
| `match_type_number` | integer | `1703` | Sometimes |
| `missing` | string[] | `["super substitutes"]` | Sometimes |
| `officials.umpires` | string[] | `["KN Ananthapadmanabhan","Nitin Menon"]` | Sometimes |
| `officials.tv_umpires` | string[] | `["J Madanagopal"]` | Sometimes |
| `officials.reserve_umpires` | string[] | `["VK Sharma"]` | Sometimes |
| `officials.match_referees` | string[] | `["J Srinath"]` | Sometimes |
| `outcome.winner` | string | `"Royal Challengers Bengaluru"` | If match completed |
| `outcome.by.wickets` | integer | `5` | If chasing team won |
| `outcome.by.runs` | integer | `23` | If batting-first team won |
| `outcome.result` | string | `"no result"` | If match abandoned |
| `outcome.eliminator` | string | `"Royal Challengers Bengaluru"` | Super Over tiebreaker |
| `player_of_match` | string[] | `["Kohli, V"]` | Sometimes |
| `players` | object | `{"Gujarat Titans": [...], ...}` | ✅ |
| `registry.people` | object | `{"Kohli, V": {"key": {"cricinfo": "253802"}}}` | ✅ |
| `season` | string | `"2026"` | ✅ |
| `team_type` | string | `"club"` | ✅ |
| `teams` | string[] | `["Gujarat Titans","Royal Challengers Bengaluru"]` | ✅ |
| `toss.decision` | string | `"field"` | ✅ |
| `toss.winner` | string | `"Royal Challengers Bengaluru"` | ✅ |
| `toss.uncontested` | boolean | `false` | Sometimes |
| `venue` | string | `"Narendra Modi Stadium, Ahmedabad"` | ✅ |

---

## `innings` Array

Each element in `innings`:

| Field | Type | Description |
|-------|------|-------------|
| `team` | string | Batting team name |
| `overs` | object[] | Array of over objects |
| `powerplays` | object[] | Powerplay phase definitions `[{from, to, type}]` |
| `declared` | boolean | True if innings declared (Tests) |
| `forfeited` | boolean | True if innings forfeited |
| `target` | object | `{runs, overs}` for D/L adjusted targets |

---

## `delivery` Object (within `overs[].deliveries`)

| Field | Type | Always | Description |
|-------|------|--------|-------------|
| `actual_delivery` | string | ✅ | Over.ball notation e.g. `"2.3"` |
| `batter` | string | ✅ | Batsman facing |
| `bowler` | string | ✅ | Bowler delivering |
| `non_striker` | string | ✅ | Non-striking batsman |
| `runs.batter` | integer | ✅ | Runs scored by batter |
| `runs.extras` | integer | ✅ | Extra runs on this ball |
| `runs.total` | integer | ✅ | Total runs (batter + extras) |
| `extras.wides` | integer | Sometimes | Wide runs |
| `extras.no_balls` | integer | Sometimes | No ball runs |
| `extras.byes` | integer | Sometimes | Bye runs |
| `extras.leg_byes` | integer | Sometimes | Leg bye runs |
| `extras.penalty` | integer | Sometimes | Penalty runs |
| `wickets` | object[] | Sometimes | Array of wicket objects |
| `wickets[].player_out` | string | — | Dismissed player |
| `wickets[].kind` | string | — | Dismissal type |
| `wickets[].fielders` | object[] | — | `[{name, substitute}]` |
| `review.by` | string | Sometimes | Team requesting DRS |
| `review.umpire` | string | Sometimes | Umpire involved |
| `review.batter` | string | Sometimes | Batter under review |
| `review.decision` | string | Sometimes | `"upheld"` or `"struck out"` |
| `review.type` | string | Sometimes | `"wicket"` or `"no_ball"` |
| `replacements` | object | Sometimes | Concussion/COVID substitute info |

---

## Dismissal Kinds (Complete List)

`caught`, `bowled`, `lbw`, `run out`, `stumped`, `hit wicket`, `obstructing the field`, `handled the ball`, `hit the ball twice`, `timed out`, `retired hurt`, `retired out`
