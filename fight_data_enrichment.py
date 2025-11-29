"""Utilities for enriching UFC fight data with detailed stats and odds.

This module is designed to be run after ``UFC_SCRAPE.py`` so that the
``ufc_fights.csv`` output already contains a ``fight_url`` column. Using the
fight detail pages lets us capture per-fight statistics (significant strikes,
takedowns, control time, etc.) that can feed the prediction model. The module
also supports optionally attaching closing odds via TheOddsAPI when an API key
is available.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import pandas as pd
import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/90.0.4430.93 Safari/537.36"
    )
}

# TheOddsAPI documentation: https://the-odds-api.com/
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/odds"


def _to_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    value = value.strip()
    if value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_landed_attempts(raw: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    if not raw or "of" not in raw:
        return None, None
    try:
        landed_str, attempted_str = raw.split("of")
        return int(landed_str.strip()), int(attempted_str.strip())
    except ValueError:
        return None, None


def _parse_control_time(raw: Optional[str]) -> Optional[int]:
    if not raw or ":" not in raw:
        return None
    try:
        minutes, seconds = raw.strip().split(":")
        return int(minutes) * 60 + int(seconds)
    except ValueError:
        return None


def _extract_totals_row(soup: BeautifulSoup) -> Optional[BeautifulSoup]:
    table = soup.find("table", class_="b-fight-details__table")
    if not table:
        return None

    tbody = table.find("tbody")
    if not tbody:
        return None

    rows = tbody.find_all("tr")
    for row in rows:
        first_cell = row.find("td")
        if first_cell and first_cell.text.strip().lower() in {"totals", "total"}:
            return row
    return rows[-1] if rows else None


def _map_stat_pairs(row: BeautifulSoup) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
    """Return a mapping of stat name -> (fighter_1_value, fighter_2_value)."""

    stat_map: Dict[str, Tuple[Optional[str], Optional[str]]] = {}
    stat_values: Dict[str, list[str]] = {}

    for cell in row.find_all("td"):
        stat_name = cell.get("data-stat")
        if not stat_name:
            continue
        stat_values.setdefault(stat_name.lower(), []).append(cell.text.strip())

    for key, values in stat_values.items():
        first = values[0] if len(values) > 0 else None
        second = values[1] if len(values) > 1 else None
        stat_map[key] = (first, second)
    return stat_map


def _stat_pair(stat_pairs: Dict[str, Tuple[Optional[str], Optional[str]]], *keys: str) -> Tuple[Optional[str], Optional[str]]:
    for key in keys:
        if key in stat_pairs:
            return stat_pairs[key]
    return (None, None)


def scrape_fight_totals(fight_url: Optional[str]) -> Dict[str, Optional[int]]:
    """Pull aggregate stats from a UFCStats fight detail page.

    Parameters
    ----------
    fight_url:
        The fight detail URL (usually captured as ``data-link`` on the event
        table row). If ``None`` or if parsing fails, the function returns an
        empty dictionary so the enrichment pipeline can continue gracefully.
    """

    if not fight_url:
        return {}

    try:
        response = requests.get(fight_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:  # type: ignore[attr-defined]
        print(f"[WARN] Unable to fetch fight details for {fight_url}: {exc}")
        return {}

    soup = BeautifulSoup(response.content, "html.parser")
    totals_row = _extract_totals_row(soup)
    if not totals_row:
        return {}

    stat_pairs = _map_stat_pairs(totals_row)

    sig_pair = _stat_pair(stat_pairs, "sig_str", "sig. str.")
    total_pair = _stat_pair(stat_pairs, "total_str", "total str.")
    td_pair = _stat_pair(stat_pairs, "td", "takedowns")

    sig_1 = _parse_landed_attempts(sig_pair[0])
    sig_2 = _parse_landed_attempts(sig_pair[1])
    total_1 = _parse_landed_attempts(total_pair[0])
    total_2 = _parse_landed_attempts(total_pair[1])
    td_1 = _parse_landed_attempts(td_pair[0])
    td_2 = _parse_landed_attempts(td_pair[1])

    ctrl_1_raw, ctrl_2_raw = _stat_pair(stat_pairs, "ctrl", "control")
    kd_1_raw, kd_2_raw = _stat_pair(stat_pairs, "kd", "knockdowns")

    return {
        "fighter_1_sig_strikes_landed": sig_1[0],
        "fighter_1_sig_strikes_attempted": sig_1[1],
        "fighter_2_sig_strikes_landed": sig_2[0],
        "fighter_2_sig_strikes_attempted": sig_2[1],
        "fighter_1_total_strikes_landed": total_1[0],
        "fighter_1_total_strikes_attempted": total_1[1],
        "fighter_2_total_strikes_landed": total_2[0],
        "fighter_2_total_strikes_attempted": total_2[1],
        "fighter_1_takedowns_landed": td_1[0],
        "fighter_1_takedowns_attempted": td_1[1],
        "fighter_2_takedowns_landed": td_2[0],
        "fighter_2_takedowns_attempted": td_2[1],
        "fighter_1_control_seconds": _parse_control_time(ctrl_1_raw),
        "fighter_2_control_seconds": _parse_control_time(ctrl_2_raw),
        "fighter_1_knockdowns": _to_int(kd_1_raw),
        "fighter_2_knockdowns": _to_int(kd_2_raw),
    }


def _normalize_name(name: str) -> str:
    return name.lower().replace(" ", "")


def _outcome_price(outcomes: Iterable[dict], target: str) -> Optional[float]:
    for outcome in outcomes:
        if _normalize_name(outcome.get("name", "")) == _normalize_name(target):
            return outcome.get("price")
    return None


def fetch_closing_odds(
    fighter_1: str, fighter_2: str, event_date: Optional[str], api_key: Optional[str]
) -> Dict[str, Optional[float]]:
    """Fetch closing moneyline odds for a bout using TheOddsAPI.

    The function requires the ``ODDS_API_KEY`` environment variable or a
    provided ``api_key`` argument. If no key is available or if the API cannot
    be reached, the function returns an empty dictionary.
    """

    key = api_key or os.getenv("ODDS_API_KEY")
    if not key:
        return {}

    params = {
        "apiKey": key,
        "regions": "us,eu,uk",
        "markets": "h2h",
        "oddsFormat": "decimal",
    }
    if event_date:
        params["date"] = event_date

    try:
        response = requests.get(ODDS_API_URL, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:  # type: ignore[attr-defined]
        print(f"[WARN] Unable to fetch odds for {fighter_1} vs {fighter_2}: {exc}")
        return {}

    events = response.json()
    for event in events:
        participants = [event.get("home_team"), event.get("away_team")]
        names = [_normalize_name(p or "") for p in participants]
        if _normalize_name(fighter_1) not in names or _normalize_name(fighter_2) not in names:
            continue

        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            continue

        # Use the most recent bookmaker snapshot
        market = bookmakers[0].get("markets", [])
        if not market:
            continue
        outcomes = market[0].get("outcomes", [])

        fighter_1_price = _outcome_price(outcomes, fighter_1)
        fighter_2_price = _outcome_price(outcomes, fighter_2)
        if fighter_1_price is None or fighter_2_price is None:
            continue

        return {
            "fighter_1_closing_odds": fighter_1_price,
            "fighter_2_closing_odds": fighter_2_price,
        }
    return {}


def enrich_fight_file(
    base_csv: str = "ufc_fights.csv",
    output_csv: str = "ufc_fights_enriched.csv",
    api_key: Optional[str] = None,
    limit: Optional[int] = None,
) -> None:
    """Enrich the base fight CSV with detailed stats and optional odds."""

    df = pd.read_csv(base_csv)
    records = []
    for idx, row in df.iterrows():
        if limit and idx >= limit:
            break

        fight_url = row.get("fight_url") if isinstance(row, pd.Series) else None
        stats = scrape_fight_totals(fight_url)
        odds = fetch_closing_odds(row["fighter_1"], row["fighter_2"], row.get("event_date"), api_key)
        combined = {**row.to_dict(), **stats, **odds}
        records.append(combined)

    enriched_df = pd.DataFrame(records)
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    enriched_df.to_csv(output_csv, index=False)
    print(f"[INFO] Saved enriched fights to {output_csv} ({len(enriched_df)} rows)")


if __name__ == "__main__":
    # Basic CLI usage for manual runs
    enrich_fight_file()
