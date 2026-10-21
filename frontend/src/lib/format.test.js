import { describe, expect, it } from 'vitest'
import {
  confidenceLevel, countdownParts, fmt, initials, pct, registerMatches, relativeDay, scoreInnings, scoreLine,
  shortVenue, team, teamToText,
} from './format'

describe('team identity', () => {
  it('uses known franchise colours and codes, including former names', () => {
    expect(team('Chennai Super Kings')).toMatchObject({ short: 'CSK', color: '#e5b80b' })
    expect(team('Royal Challengers Bangalore').short).toBe('RCB')
  })

  it('derives a stable code and colour for unknown teams and strips "Women"', () => {
    const a = team('Melbourne Renegades Women')
    expect(a.short).toBe('MR')
    expect(team('Melbourne Renegades Women').color).toBe(a.color)
    expect(team('Namibia').short).toBe('NAM')
  })

  it('prefers provider short codes and logos once registered', () => {
    registerMatches([{ team_info: { 'Hobart Hurricanes': { short: 'HBH-W', img: 'https://img/hh.png' } } }])
    expect(team('Hobart Hurricanes')).toMatchObject({ short: 'HBH-W', img: 'https://img/hh.png' })
  })
})

describe('live score formatting (real CricketData shapes)', () => {
  const m = {
    team_a: 'India', team_b: 'Zimbabwe',
    live_state: {
      score: [
        { r: 216, w: 7, o: 20, inning: 'india women Inning 1' },
        // the provider sometimes names both sides in the second-innings label
        { r: 73, w: 2, o: 12.2, inning: 'India Women,Zimbabwe Women Inning 1' },
      ],
    },
  }

  it('attributes each innings to the right side', () => {
    expect(scoreInnings(m).map((i) => i.team)).toEqual(['India', 'Zimbabwe'])
  })

  it('builds a compact score line', () => {
    expect(scoreLine(m)).toBe('IND 216/7 (20) · ZIM 73/2 (12.2)')
  })

  it('handles matches without a score yet', () => {
    expect(scoreInnings({ team_a: 'A', team_b: 'B' })).toEqual([])
    expect(scoreLine({})).toBe('')
  })
})

describe('confidence bands follow UI_UX_GUIDELINES', () => {
  it.each([[95, 'High'], [80, 'High'], [79, 'Medium'], [60, 'Medium'], [59, 'Low'], [40, 'Low'], [39, 'Very Low'], [0, 'Very Low']])(
    '%i%% → %s', (value, label) => expect(confidenceLevel(value).label).toBe(label),
  )
})

describe('number and text helpers', () => {
  it('formats numbers defensively', () => {
    expect(fmt(51.26)).toBe('51.3')
    expect(fmt(null)).toBe('—')
    expect(pct(0.133)).toBe('13%')
    expect(initials('SV Samson')).toBe('SS')
    expect(shortVenue('MA Chidambaram Stadium, Chepauk, Chennai')).toBe('MA Chidambaram Stadium')
  })

  it('labels relative days', () => {
    expect(relativeDay(new Date())).toBe('Today')
    expect(relativeDay(new Date(Date.now() + 86_400_000))).toBe('Tomorrow')
  })

  it('counts down to a start time and stops at zero', () => {
    const p = countdownParts(new Date(Date.now() + (26 * 3600 + 5 * 60) * 1000))
    expect(p).toMatchObject({ done: false, d: 1, h: 2 })
    expect(countdownParts(new Date(Date.now() - 1000)).done).toBe(true)
  })
})

describe('clipboard team summary', () => {
  it('groups by role and tags captain / vice-captain', () => {
    const p = (id, full_name, role) => ({ player_id: id, full_name, role })
    const t = {
      players: [p('1', 'SV Samson', 'WK'), p('2', 'RD Gaikwad', 'BAT'), p('3', 'HH Pandya', 'AR'), p('4', 'JJ Bumrah', 'BOWL')],
      captain: { player_id: '1' }, vice_captain: { player_id: '4' }, total_credits: 94.5, predicted_total_fp: 507.2,
    }
    const text = teamToText({ team_a: 'Chennai Super Kings', team_b: 'Mumbai Indians' }, 'safe', t)
    expect(text).toContain('XithSense Safe XI — Chennai Super Kings vs Mumbai Indians')
    expect(text).toContain('WK: SV Samson (C)')
    expect(text).toContain('BOWL: JJ Bumrah (VC)')
    expect(text).toContain('Credits 94.5 · Projected 507 pts')
  })
})
