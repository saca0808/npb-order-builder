#!/usr/bin/env python3
"""Conservatively display historical non-pitcher positions.

The legacy fielding source counts appearances that may include pre-game
scouting substitutions. Without a play-by-play or a scorebook, an isolated
non-pitcher appearance cannot be called a defensive appearance. Preserve the
original evidence separately so that a later documented review can restore
the position without guessing.

This is a *display confidence* rule, not a claim that every hidden position
was a scouting assignment. A player's batting totals cannot prove that they
defended any particular position.
"""

import json
import re
from pathlib import Path

DB_PATH = Path('dist/npb_players_full.json')
# A pitcher who later appeared as a position player can have fewer than 100
# career hits. Keep reviewed conversions by unique player ID, never by name.
KNOWN_CONVERSIONS = {'pey_11415113': {'外野手'}}  # 三浦貴: pitcher to outfielder.
# These entries record *individual scouting starts*, not proof that a player
# never defended that position during another game of his career.
SCOUTING_STARTS = {
    'pey_91993845': [
        {'position': '外野手', 'game': '1981-06-03', 'url': 'https://sta-men.jp/1981dragons.html'},
        {'position': '外野手', 'game': '1985-05-09', 'url': 'https://sta-men.jp/1985dragons.html'},
    ],
    'pey_41543847': [
        {'position': '三塁手', 'game': '1985-08-02', 'url': 'https://sta-men.jp/1985dragons.html'},
    ],
}
NOTE = '投手以外の登録は守備出場の確認が必要なため非表示'
NPB_DH_FIRST_YEAR = 1975


def remove_impossible_dh(database):
    """Remove DH from players whose NPB career ended before its 1975 debut."""
    corrected = 0
    for player in database['players']:
        if player.get('active') or '指名打者' not in player.get('positions', []):
            continue
        years = [int(year) for year in re.findall(r'\d{4}', str(player.get('years', '')))]
        if not years or max(years) >= NPB_DH_FIRST_YEAR:
            continue
        player['positions'] = [position for position in player['positions'] if position != '指名打者']
        if 'career_positions' in player:
            player['career_positions'] = [position for position in player['career_positions']
                                          if position != '指名打者']
        if 'unverified_positions' in player:
            player['unverified_positions'] = [position for position in player['unverified_positions']
                                              if position != '指名打者']
        corrected += 1
    database['dh_position_rule'] = (
        'DH removed from players whose NPB career ended before the Pacific League '
        'introduced the designated hitter in 1975.'
    )
    return corrected


def review(database):
    reviewed_players = 0
    hidden_positions = 0
    for player in database['players']:
        if player.get('active') or '投手' not in player.get('positions', []):
            continue
        if player['id'] in SCOUTING_STARTS:
            player['scouting_starts_checked'] = SCOUTING_STARTS[player['id']]
        known = KNOWN_CONVERSIONS.get(player['id'], set())
        verified = player.get('defensive_evidence', {})
        extra = [position for position in player['positions'] if position not in ('投手', '指名打者')
                 and position not in known and position not in verified]
        if not extra:
            continue
        player['unverified_positions'] = list(dict.fromkeys(player.get('unverified_positions', []) + extra))
        player['positions'] = [position for position in player['positions'] if position not in extra]
        player['position_note'] = NOTE
        reviewed_players += 1
        hidden_positions += len(extra)
    database['position_rule_ob_pitchers'] = (
        'Conservative display: non-pitcher positions without defensive chances or '
        'individually documented conversion hidden for former pitchers; '
        'original values retained in unverified_positions. '
        'A hidden position is not proven to be a scouting assignment.'
    )
    return reviewed_players, hidden_positions


def main():
    with DB_PATH.open(encoding='utf-8') as source:
        database = json.load(source)
    dh_count = remove_impossible_dh(database)
    count, positions = review(database)
    with DB_PATH.open('w', encoding='utf-8') as target:
        json.dump(database, target, ensure_ascii=False, separators=(',', ':'))
    print(f'OB pitcher review: {count} players, {positions} unverified positions hidden; '
          f'{dh_count} pre-1975 DH positions removed')


if __name__ == '__main__':
    main()
