#!/usr/bin/env python3
"""Daily updater for the NPB order builder.

Updates current NPB roster status, development/controlled registration,
official registration position, first/farm fielding positions and NPB career
totals. Existing historical data is preserved when a source is temporarily
unavailable. A validation step blocks deployment of unsafe output.
"""

import html
import json
import re
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

DB_PATH = Path("dist/npb_players_full.json")
JST = ZoneInfo("Asia/Tokyo")
YEAR = datetime.now(JST).year
TODAY = datetime.now(JST).date().isoformat()
TEAM_CODES = {"f": "F", "e": "E", "l": "L", "m": "M", "b": "B", "h": "H", "t": "T", "db": "DB", "g": "G", "d": "D", "c": "C", "s": "S"}
INFIELD = ["一塁手", "二塁手", "三塁手", "遊撃手"]
POSITIONS = ["投手", "捕手", "一塁手", "二塁手", "三塁手", "遊撃手", "外野手"]
HEADERS = {"User-Agent": "NPBOrderBuilderDataUpdater/1.0 (+scheduled once daily)"}


def fetch_text(url, attempts=3):
    error = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read().decode("utf-8")
        except Exception as exc:
            error = exc
            time.sleep(2 + attempt * 2)
    raise RuntimeError(f"failed to fetch {url}: {error}")


def norm(value):
    return re.sub(r"[\s\u3000*＊※]+", "", html.unescape(value or ""))


class RosterParser(HTMLParser):
    def __init__(self, team):
        super().__init__()
        self.team = team
        self.kind = "支配下"
        self.position = ""
        self.row = None
        self.cell = None
        self.players = []
        self.in_heading = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h3":
            self.in_heading = True
        if tag == "tr":
            self.row = {"class": attrs.get("class", ""), "cells": [], "id": ""}
        if self.row is not None and tag in ("td", "th"):
            self.cell = []
            self.row["cells"].append(self.cell)
        if self.row is not None and tag == "a":
            match = re.search(r"/bis/players/(\d+)\.html", attrs.get("href", ""))
            if match:
                self.row["id"] = match.group(1)

    def handle_endtag(self, tag):
        if tag == "h3":
            self.in_heading = False
        if tag in ("td", "th"):
            self.cell = None
        if tag == "tr" and self.row:
            cells = ["".join(cell).strip() for cell in self.row["cells"]]
            if "rosterMainHead" in self.row["class"] and len(cells) > 1 and cells[1] in ("投手", "捕手", "内野手", "外野手"):
                self.position = cells[1]
            elif "rosterPlayer" in self.row["class"] and self.row["id"] and len(cells) >= 7 and self.position:
                self.players.append({"npb_id": self.row["id"], "name": cells[1].replace("\u3000", " "), "team": self.team,
                                     "position": self.position, "kind": self.kind, "birth": cells[2].replace(".", "-"),
                                     "throws": cells[5], "bats": cells[6]})
            self.row = None

    def handle_data(self, data):
        value = html.unescape(data).strip()
        if self.in_heading and "育成選手" in value:
            self.kind = "育成"
        if self.cell is not None:
            self.cell.append(value)


def fetch_roster(item):
    code, team = item
    parser = RosterParser(team)
    parser.feed(fetch_text(f"https://npb.jp/bis/teams/rst_{code}.html"))
    return parser.players


def numeric(text):
    value = re.sub(r"[^0-9.-]", "", text or "")
    try:
        return int(float(value))
    except ValueError:
        return 0


def innings_text(cell):
    integer = cell.select_one(".integer")
    fraction = cell.select_one(".fraction")
    whole = numeric(integer.get_text()) if integer else numeric(cell.get_text())
    frac = numeric(fraction.get_text()) if fraction else 0
    return f"{whole}.{frac}" if frac in (1, 2) else str(whole)


def parse_profile(player_id):
    page = fetch_text(f"https://npb.jp/bis/players/{player_id}.html")
    soup = BeautifulSoup(page, "html.parser")
    kana_node = soup.select_one("#pc_v_kana")
    kana = re.sub(r"\s+", " ", kana_node.get_text(" ", strip=True).replace("・", " ")) if kana_node else ""
    result = {"kana": kana}
    batting = soup.select_one("#tablefix_b tfoot tr")
    if batting:
        cells = batting.find_all(["th", "td"], recursive=False)
        values = [cell.get_text(" ", strip=True) for cell in cells]
        if len(values) >= 22:
            result["npb_batting"] = f"打率 {values[20]} / {numeric(values[6]):,}安打 / {numeric(values[9]):,}本塁打 / {numeric(values[11]):,}打点 / {numeric(values[12]):,}盗塁"
    pitching = soup.select_one("#tablefix_p tfoot tr")
    if pitching:
        cells = pitching.find_all(["th", "td"], recursive=False)
        values = [cell.get_text(" ", strip=True) for cell in cells]
        if len(values) >= 24:
            result["npb_pitching"] = f"{numeric(values[3]):,}勝{numeric(values[4]):,}敗 / {numeric(values[5]):,}セーブ / 防御率 {values[-1]} / {numeric(values[18]):,}奪三振"
    return player_id, result


def parse_fielding_page(url):
    soup = BeautifulSoup(fetch_text(url), "html.parser")
    found = defaultdict(set)
    for heading in soup.find_all("h5"):
        position = heading.get_text(strip=True)
        if position not in POSITIONS:
            continue
        table = heading.find_next("table")
        if not table:
            continue
        for row in table.select("tbody tr"):
            cells = row.find_all(["th", "td"], recursive=False)
            if len(cells) >= 2 and numeric(cells[1].get_text()) > 0:
                found[norm(cells[0].get_text())].add(position)
    return found


def main():
    with open(DB_PATH, encoding="utf-8") as source:
        database = json.load(source)
    players = database["players"]
    by_id = {player["id"].removeprefix("pey_"): player for player in players if player["id"].startswith("pey_")}

    roster = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        for records in executor.map(fetch_roster, TEAM_CODES.items()):
            for record in records:
                roster[record["npb_id"]] = record
    if not 650 <= len(roster) <= 1400:
        raise RuntimeError(f"unsafe roster count: {len(roster)}")

    fielding = defaultdict(set)
    jobs = [(team, level, code) for code, team in TEAM_CODES.items() for level in (1, 2)]
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_map = {executor.submit(parse_fielding_page, f"https://npb.jp/bis/{YEAR}/stats/idf{level}_{code}.html"): team for team, level, code in jobs}
        for future in as_completed(future_map):
            team = future_map[future]
            for name, positions in future.result().items():
                fielding[(team, name)].update(positions)

    for player in players:
        if player.get("current_team"):
            player["active"] = False
            player["current_team"] = None
            player["roster_kind"] = ""

    for player_id, record in roster.items():
        player = by_id.get(player_id)
        if not player:
            player = {"id": f"pey_{player_id}", "name": record["name"], "kana": record["name"], "birth": record["birth"],
                      "active": True, "current_team": record["team"], "current_team_name": "", "roster_kind": record["kind"],
                      "official_position": record["position"], "career_positions": [], "positions": [], "throws": record["throws"],
                      "bats": record["bats"], "clubs": [record["team"]], "club_history": [record["team"]],
                      "npb_batting": "", "npb_pitching": "", "mlb_batting": "", "mlb_pitching": "", "years": f"{YEAR}–"}
            players.append(player)
            by_id[player_id] = player
        player.update(active=True, current_team=record["team"], roster_kind=record["kind"], official_position=record["position"],
                      birth=record["birth"], throws=record["throws"], bats=record["bats"])
        if record["team"] not in player.setdefault("clubs", []):
            player["clubs"].append(record["team"])
        if record["team"] not in player.setdefault("club_history", []):
            player["club_history"].append(record["team"])
        actual = [position for position in POSITIONS if position in fielding.get((record["team"], norm(record["name"])), set())]
        old_dh = "指名打者" in player.get("positions", [])
        fallback = {"投手": ["投手"], "捕手": ["捕手"], "内野手": INFIELD, "外野手": ["外野手"]}[record["position"]]
        player["positions"] = actual or fallback
        if old_dh:
            player["positions"].append("指名打者")
        player["position_note"] = f"{YEAR}年一・二軍守備記録に基づく出場ポジション"

    failures = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_map = {executor.submit(parse_profile, player_id): player_id for player_id in roster}
        for future in as_completed(future_map):
            player_id = future_map[future]
            try:
                _, profile = future.result()
                player = by_id[player_id]
                for key, value in profile.items():
                    if value:
                        player[key] = value
            except Exception as exc:
                failures.append(f"{player_id}: {exc}")
    if len(failures) > max(10, len(roster) // 50):
        raise RuntimeError(f"too many profile failures: {len(failures)}; first={failures[0]}")

    players.sort(key=lambda player: (not player.get("active"), player.get("name", "")))
    database["roster_as_of"] = TODAY
    database["updated_at"] = TODAY
    database["update_status"] = {"npb_roster": len(roster), "profile_failures": len(failures), "season": YEAR}
    with open(DB_PATH, "w", encoding="utf-8") as output:
        json.dump(database, output, ensure_ascii=False, separators=(",", ":"))
    print(f"updated={TODAY} roster={len(roster)} players={len(players)} profile_failures={len(failures)}")


if __name__ == "__main__":
    main()
