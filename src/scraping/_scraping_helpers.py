import json
import os
from datetime import datetime

import requests
from requests import Session

from config.paths import RAW_TAS_PATH, TRACK_UPPERS_PATH
from config.scraping import BASE_URL, FILTER_STRS
from src.utils.timer import timer


def _filter_str(unfiltered: str, filter_key: str) -> str:
    """Uses strings from FILTER_KEYS to filter the string."""
    start_str, inc_start, end_str, inc_end = FILTER_STRS[filter_key]

    start_i = unfiltered.find(start_str)
    if not inc_start:
        start_i += len(start_str)
    end_i = unfiltered.find(end_str, start_i)
    if inc_end:
        end_i += len(end_str)

    return unfiltered[start_i:end_i]


def _get_index_comp_urls() -> tuple[str, str]:
    """
    Scrapes the main TDR page to get the current index and components urls, returns (components,
    index).
    """

    r = requests.get(BASE_URL, timeout=10)
    base = r.text

    components_url = f"{BASE_URL}{_filter_str(base, 'components')}"
    index_url = f"{BASE_URL}{_filter_str(base, 'index')}"

    return components_url, index_url


def _get_track_maps(index_full: str) -> dict:
    """Extracts mapping of track ids (e.g. "drag30130") to names ("30-130mph (R)")"""

    all_maps = _filter_str(index_full, "id_name_maps")

    track_maps_str = [m for m in all_maps[1:-1].split(",") if m.startswith("t_")]
    track_maps = {m.split(":")[0][2:]: m.split(":")[1][1:-1] for m in track_maps_str}

    return track_maps


def _get_uppers_map(index_full: str) -> dict:
    """Extracts upper points limits for tracks."""

    codes_str = _filter_str(index_full, "track_upper_codes")[:-4]
    codes = {c.split("=")[0]: c.split("=")[1] for c in codes_str.split(",")}

    tracks_str = _filter_str(index_full, "track_upper_map")[1:-1]
    tracks = {t.split(":")[0]: t.split(":")[1] for t in tracks_str.split(",")}

    uppers_map = {k_t: int(float(codes[v_t])) for k_t, v_t in tracks.items()}

    with open(TRACK_UPPERS_PATH, "w", encoding="utf-8") as f:
        json.dump(uppers_map, f)

    return uppers_map


@timer
def _scrape_car(session: Session, rid: str) -> list[dict] | None:
    """Scrapes one car from its rid, returning a list of dicts, one for each tune."""
    r = session.get(f"https://api.topdrivesrecords.com/car/{rid}", timeout=10).text
    if not r:
        return None
    car_data = json.loads(r)["data"]
    car_dicts = []

    # Loop through all tunes in car data
    for tune, tune_dict in car_data.items():
        if tune.startswith("v"):
            continue

        info = tune_dict.get("info", {})
        times = tune_dict.get("times", {})

        # Start with stats
        stats_dict = {
            "rid": rid,
            "top_speed": info.get("topSpeed", {"t": "-"})["t"],
            "zero_sixty": info.get("acel", {"t": "-"})["t"],
            "handling": info.get("hand", {"t": "-"})["t"],
            "engine_up": tune[0],
            "weight_up": tune[1],
            "chassis_up": tune[2],
        }
        # Then times
        just_times = {
            track_id: track_dict["t"] for track_id, track_dict in times.items() if "t" in track_dict
        }

        car_dicts.append(stats_dict | just_times)

    return car_dicts


def _load_raw_tas() -> dict:
    """
    Loads existing raw times and stats JSON dict from config.paths.RAW_TAS_PATH, or returns empty
    dict if file does not exist.
    """
    if os.path.isfile(RAW_TAS_PATH):
        with open(RAW_TAS_PATH, "r", encoding="utf-8") as f:
            tas = json.load(f)
    else:
        tas = {}
    return tas


def _save_raw_tas(tas_dicts: dict) -> None:
    """Saves tas_dicts to config.paths.RAW_TAS_PATH."""
    with open(RAW_TAS_PATH, "w", encoding="utf-8") as f:
        json.dump(tas_dicts, f)


def _scraped_recently(date_str: str, bound: int) -> bool:
    """
    Given a string datetime in format %Y-%m-%d-%H:%M, and a bound, returns True/False if datetime
    is recent.
    """
    now = datetime.today()
    then = datetime.strptime(date_str, "%Y-%m-%d-%H:%M")
    delta = now - then
    if delta.total_seconds() >= bound:
        return False
    else:
        return True


def _update_and_save(old_tas: dict, new_tas: dict) -> None:
    """Updates old tas with new tas and saves."""
    old_tas.update(new_tas)
    _save_raw_tas(old_tas)


def _filter_ci_dicts(ci_dicts: list[dict], tas_dicts: dict, skip_seconds: int):
    """Filters ci_dicts to just those that have not been updated recently"""
    # tas_dicts = {rid: {'rid': rid, 'updated': "%Y-%m-%d", ...}, ...}
    # ci_dicts = [{'rid': rid, ...}, ...]

    updated_recently = {
        rid
        for rid, tas_dict in tas_dicts.items()
        if _scraped_recently(tas_dict["updated"], skip_seconds)
    }

    return [ci_dict for ci_dict in ci_dicts if ci_dict["rid"] not in updated_recently]
