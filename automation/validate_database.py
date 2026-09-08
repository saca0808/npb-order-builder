#!/usr/bin/env python3
import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

PATH = "dist/npb_players_full.json"

with open(PATH, encoding="utf-8") as source:
    data = json.load(source)

players = data.get("players")
if not isinstance(players, list) or len(players) < 7000:
    raise SystemExit(f"player count is unsafe: {len(players) if isinstance(players, list) else 'invalid'}")

ids = [player.get("id") for player in players]
if len(ids) != len(set(ids)) or any(not value for value in ids):
    raise SystemExit("missing or duplicate player id")

active = [player for player in players if player.get("active")]
npb_active = [player for player in active if player.get("current_team")]
if not 650 <= len(npb_active) <= 1400:
    raise SystemExit(f"current NPB roster count is unsafe: {len(npb_active)}")

allowed_positions = {"投手", "捕手", "一塁手", "二塁手", "三塁手", "遊撃手", "外野手", "指名打者"}
for player in players:
    if not player.get("name"):
        raise SystemExit(f"missing name: {player.get('id')}")
    if any(position not in allowed_positions for position in player.get("positions", [])):
        raise SystemExit(f"invalid position: {player.get('id')}")
    birth = player.get("birth")
    if birth and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", birth):
        raise SystemExit(f"invalid birth date: {player.get('id')} {birth}")

updated = data.get("updated_at")
today_jst = datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat()
if updated != today_jst:
    raise SystemExit(f"database was not updated today: {updated}")

print(f"validation ok: players={len(players)} active_npb={len(npb_active)} updated={updated}")
