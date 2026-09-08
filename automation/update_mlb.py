#!/usr/bin/env python3
"""Refresh MLB career totals for NPB players linked by Chadwick's register."""

import csv
import io
import json
import time
import urllib.request
import zipfile
from pathlib import Path

DB_PATH = Path("dist/npb_players_full.json")
REGISTER_URL = "https://github.com/chadwickbureau/register/archive/refs/heads/master.zip"
STATS_URL = "https://statsapi.mlb.com/api/v1/people"
HEADERS = {"User-Agent": "NPBOrderBuilderDataUpdater/1.0 (+scheduled once daily)"}


def fetch(url, attempts=3):
    error = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except Exception as exc:
            error = exc
            time.sleep(2 + attempt * 2)
    raise RuntimeError(f"failed to fetch {url}: {error}")


def register_links():
    links = {}
    with zipfile.ZipFile(io.BytesIO(fetch(REGISTER_URL))) as archive:
        for name in archive.namelist():
            if "/data/people-" not in name or not name.endswith(".csv"):
                continue
            stream = io.TextIOWrapper(archive.open(name), encoding="utf-8-sig")
            for row in csv.DictReader(stream):
                npb_id = (row.get("key_npb") or "").strip()
                mlb_id = (row.get("key_mlbam") or "").strip()
                played = (row.get("mlb_played_first") or "").strip()
                if npb_id and mlb_id and played:
                    links[npb_id.zfill(8)] = mlb_id
    return links


def stat_group(person, group):
    for item in person.get("stats", []):
        display_name = item.get("group", {}).get("displayName")
        if display_name == group and item.get("splits"):
            return item["splits"][0].get("stat", {})
    return {}


def batting_text(stat):
    if not stat:
        return ""
    return (
        f"打率 {stat.get('avg', '.000')} / {int(stat.get('hits', 0)):,}安打 / "
        f"{int(stat.get('homeRuns', 0)):,}本塁打 / {int(stat.get('rbi', 0)):,}打点 / "
        f"{int(stat.get('stolenBases', 0)):,}盗塁"
    )


def pitching_text(stat):
    if not stat:
        return ""
    return (
        f"{int(stat.get('wins', 0)):,}勝{int(stat.get('losses', 0)):,}敗 / "
        f"{int(stat.get('saves', 0)):,}セーブ / 防御率 {stat.get('era', '0.00')} / "
        f"{int(stat.get('strikeOuts', 0)):,}奪三振"
    )


def main():
    with open(DB_PATH, encoding="utf-8") as source:
        database = json.load(source)
    players = database["players"]
    by_npb = {
        player["id"].removeprefix("pey_").zfill(8): player
        for player in players
        if player.get("id", "").startswith("pey_")
    }
    links = register_links()
    targets = {
        links[npb_id]: player
        for npb_id, player in by_npb.items()
        if npb_id in links
    }
    if len(targets) < 50:
        raise RuntimeError(f"unsafe NPB/MLB link count: {len(targets)}")

    updated = 0
    failed_batches = 0
    ids = list(targets)
    for start in range(0, len(ids), 40):
        batch = ids[start:start + 40]
        url = (
            f"{STATS_URL}?personIds={','.join(batch)}"
            "&hydrate=stats(group=[hitting,pitching],type=[career])"
        )
        try:
            people = json.loads(fetch(url)).get("people", [])
            for person in people:
                player = targets.get(str(person.get("id")))
                if not player:
                    continue
                batting = batting_text(stat_group(person, "hitting"))
                pitching = pitching_text(stat_group(person, "pitching"))
                if batting:
                    player["mlb_batting"] = batting
                if pitching:
                    player["mlb_pitching"] = pitching
                updated += 1
        except Exception:
            failed_batches += 1
    if failed_batches > max(2, (len(ids) // 40) // 5):
        raise RuntimeError(f"too many MLB API batch failures: {failed_batches}")

    database.setdefault("update_status", {})["mlb_players_refreshed"] = updated
    with open(DB_PATH, "w", encoding="utf-8") as output:
        json.dump(database, output, ensure_ascii=False, separators=(",", ":"))
    print(
        f"mlb_links={len(targets)} refreshed={updated} "
        f"failed_batches={failed_batches}"
    )


if __name__ == "__main__":
    main()
