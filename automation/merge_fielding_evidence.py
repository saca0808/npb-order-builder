#!/usr/bin/env python3
"""Restore an OB pitcher's position only when defensive fielding is documented.

Accepts one or more ProEyeKyuu Player Fielding Stats CSV files. A season with
PO + A + E > 0 proves the player actually defended that position. Zero
chances do NOT prove the player was a scouting substitute; leave such cases
unverified. This script reads user-provided files and performs no downloads.

Usage: python automation/merge_fielding_evidence.py /path/to/player_fielding.zip
"""

import argparse
import csv
import json
import re
import io
import zipfile
from collections import defaultdict
from pathlib import Path

DB = Path('dist/npb_players_full.json')
POS = {'1B': '一塁手', '2B': '二塁手', '3B': '三塁手', 'SS': '遊撃手',
       'C': '捕手', 'OF': '外野手', 'LF': '外野手', 'CF': '外野手', 'RF': '外野手'}
COL = {'PlayerID': ('PlayerID', 'プレイヤーID'), 'Position': ('Position', '位置'),
       'Season': ('Season', 'Year', '季節'), 'Game Type': ('Game Type', 'GameType', 'ゲームタイプ'),
       'PO': ('PO',), 'A': ('A',), 'E': ('E',)}


def count(value):
    if value is None or not re.fullmatch(r'[\d,]+(?:\.0)?', str(value).strip()):
        raise ValueError(f'invalid defensive count: {value!r}')
    return int(float(str(value).replace(',', '')))


def columns(fieldnames):
    selected = {key: next((name for name in names if name in fieldnames), None)
                for key, names in COL.items()}
    missing = [key for key in ('PlayerID', 'Position', 'Season', 'PO', 'A', 'E')
               if selected[key] is None]
    if missing:
        raise ValueError(f'missing required columns: {missing}; got {fieldnames}')
    return selected


def evidence(paths):
    result = defaultdict(list)
    coverage = {'rows': 0, 'player_ids': set(), 'seasons': set(), 'missing_counts': 0}
    for path in paths:
        if path.suffix.lower() == '.zip':
            with zipfile.ZipFile(path) as archive:
                members = [member for member in archive.namelist() if member.lower().endswith('.csv')]
                if not members:
                    raise ValueError(f'no CSV files in {path}')
                for member in members:
                    with archive.open(member) as raw:
                        parse_csv(io.TextIOWrapper(raw, encoding='utf-8-sig', newline=''),
                                  f'{path}:{member}', result, coverage)
        else:
            with open(path, encoding='utf-8-sig', newline='') as source:
                parse_csv(source, str(path), result, coverage)
    return result, coverage


def parse_csv(source, source_name, result, coverage):
    reader = csv.DictReader(source)
    col = columns(reader.fieldnames or [])
    for row in reader:
        raw_id = (row[col['PlayerID']] or '').strip()
        if not raw_id.isdigit():
            continue
        season = str(row[col['Season']] or '').strip()
        if not re.fullmatch(r'\d{4}(?:\s+(?:Spring|Fall))?', season, re.IGNORECASE):
            raise ValueError(f'invalid season in {source_name}: {season!r}')
        coverage['rows'] += 1
        coverage['player_ids'].add(raw_id.zfill(8))
        coverage['seasons'].add(season[:4])
        position = POS.get((row[col['Position']] or '').strip().upper())
        if not position:
            continue
        game_type = (row.get(col['Game Type']) or '').strip().lower() if col['Game Type'] else ''
        if game_type and game_type not in ('reg season', 'regular season'):
            continue
        # Empty counts are unavailable data, not proof of zero fielding chances.
        values = [(row[col[key]] or '').strip() for key in ('PO', 'A', 'E')]
        if not any(values):
            coverage['missing_counts'] += 1
            continue
        if not all(values):
            raise ValueError(f'partially missing defensive counts in {source_name}: {row!r}')
        total = sum(count(value) for value in values)
        if total == 0:
            continue
        result[(f'pey_{raw_id.zfill(8)}', position)].append({'season': season, 'chances': total})


def merge(database, records):
    restored = []
    for player in database['players']:
        if player.get('active') or '投手' not in player.get('positions', []):
            continue
        hidden = player.get('unverified_positions', [])
        confirmed = [p for p in hidden if (player['id'], p) in records]
        if not confirmed:
            continue
        player['positions'] = list(dict.fromkeys(player['positions'] + confirmed))
        player['unverified_positions'] = [p for p in hidden if p not in confirmed]
        player.setdefault('defensive_evidence', {}).update({
            p: min(records[player['id'], p], key=lambda item: item['season']) for p in confirmed
        })
        if not player['unverified_positions']:
            player.pop('position_note', None)
        restored.extend((player['id'], p) for p in confirmed)
    return restored


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', nargs='+', type=Path)
    parser.add_argument('--allow-partial', action='store_true', help='use an incomplete export for incremental review')
    args = parser.parse_args()
    with DB.open(encoding='utf-8') as source:
        database = json.load(source)
    records, coverage = evidence(args.csv)
    print(f"input: {coverage['rows']} rows, {len(coverage['player_ids'])} players, "
          f"{len(coverage['seasons'])} years, {coverage['missing_counts']} rows with unavailable counts")
    if not args.allow_partial and (len(coverage['player_ids']) < 5000 or len(coverage['seasons']) < 80):
        raise SystemExit('incomplete historical export; database unchanged (use --allow-partial for targeted review)')
    restored = merge(database, records)
    database['ob_pitcher_fielding_review'] = {
        'source': 'ProEyeKyuu Player Fielding Stats (user-provided CSV exports)',
        'seasons': f"{min(coverage['seasons'])}-{max(coverage['seasons'])}",
        'rows': coverage['rows'],
        'player_ids': len(coverage['player_ids']),
        'unknown_defensive_counts': coverage['missing_counts'],
        'criterion': 'At least one PO, A or E in a regular season confirms defensive activity; other positions remain unverified.'
    }
    with DB.open('w', encoding='utf-8') as target:
        json.dump(database, target, ensure_ascii=False, separators=(',', ':'))
    print(f'restored {len(restored)} positions with recorded defensive chances from {len(args.csv)} CSV(s)')


if __name__ == '__main__':
    main()
