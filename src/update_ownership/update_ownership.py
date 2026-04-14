"""Functions for updating ownership lists."""

import json
from collections import defaultdict

import pandas as pd

from config.paths import OWNED_PATH, PREPROCESSED_PATH, RAW_CI_PATH, TD_JSON_PATH, TDR_JSON_PATH
from src.utils.timer import timer


def load_preprocessed() -> pd.DataFrame:
    """Loads DataFrame from PREPROCESSED_PATH."""
    preprocessed_df = pd.read_csv(PREPROCESSED_PATH)
    return preprocessed_df


def load_garage_jsons() -> dict:
    """Loads both jsons from TD_JSON_PATH and TDR_JSON_PATH, returning in one dict."""
    with open(TD_JSON_PATH, "r", encoding="utf-8") as f:
        garage_td = json.load(f)["playerDeck"]
    with open(TDR_JSON_PATH, "r", encoding="utf-8") as f:
        garage_td_records = json.load(f)["value"]["playerDeck"]
    return {"td": garage_td, "tdr": garage_td_records}


def load_owned_lists() -> dict:
    """Loads the json in OWNED_PATH."""
    with open(OWNED_PATH, "r", encoding="utf-8") as f:
        owned_lists = json.load(f)
    return owned_lists


@timer
def match_records() -> list:
    """Matches all elements in TD_JSON_PATH and TDR_JSON_PATH."""
    garages = load_garage_jsons()
    td = garages["td"]
    tdr = garages["tdr"]

    all_owned_matched = []
    while len(td) > 0:
        td_car = td.pop(0)
        if td_car["state"] == 0:  # state 0 means in holding area, not in garage
            continue
        else:
            for tdr_i, tdr_car in enumerate(tdr):
                if tdr_car["cardRecordId"].startswith(tdr_car["cardRecordId"]):
                    tdr.pop(tdr_i)
                    all_owned_matched.append((td_car, tdr_car))
                    break

    return all_owned_matched


def _find_rq(df: pd.DataFrame, rid: str, raise_no_match: bool) -> tuple[int, str, int]:
    """Use rid to get rq, mm, year, from processed data."""
    filtered = df[df["rid"].str.startswith(rid)]
    if filtered.empty:
        if raise_no_match:
            raise ValueError(f"No match found for rid: {rid}")
        else:
            return (0, "", 0)
    rq = int(filtered["rq"].iloc[0])

    return rq


def _get_tune(td: dict) -> str:
    """Extracts the tune from the car's info"""
    eng = td["engineMajor"]
    eng_m = td["engineMinor"]
    wei = td["weightMajor"]
    wei_m = td["weightMinor"]
    cha = td["chassisMajor"]
    cha_m = td["chassisMinor"]
    if (eng, wei, cha) == (1, 1, 1) and (eng_m, wei_m, cha_m) == (0, 0, 0):
        return "000"
    else:
        return f"{eng}{wei}{cha}"


@timer
def create_new_big_list(all_owned_matched: list, lowest_unlocked: int = 0) -> list:
    """Creates one list of all owned cars (all locked and all unlocked above a certain RQ)."""
    new_big_list = []
    unlocked = []
    with open(RAW_CI_PATH, "r", encoding="utf-8") as f:
        ci_list = json.load(f)
    ci_dict = {ci["rid"]: ci for ci in ci_list}

    # Iterate through list of joined jsons
    for td, tdr in all_owned_matched:
        rid = tdr["rid"].encode("utf-8").decode("latin-1")
        rq = ci_dict[rid]["rq"]

        # Skip unlocked cars past a certain RQ
        if rq < lowest_unlocked and not td["locked"]:
            unlocked.append(f"[{rq}] {rid}")
            continue

        # Add to new big list
        new_big_list.append((rq, rid, _get_tune(td)))

    # Sort: First by RQ (desc), then rid (asc), then tune (desc)
    new_big_list.sort(key=lambda x: (-x[0], x[1].lower(), -int(x[2])))
    return new_big_list


@timer
def create_owned_lists(big_list: list) -> dict:
    """
    Splits the big list of all owned cars into 3 lists: first version of owned cars, duplicate cars,
    double dupe cars. Ignores any past this.
    """
    owned = {1: [], 2: [], 3: []}

    counts = defaultdict(int)
    for car in big_list:
        rid = car[1]
        counts[rid] += 1
        count = counts[rid]
        if count <= 3:
            car = list(car)
            owned[count].append(car)

    return {
        "owned_cars_list": owned[1],
        "duplicate_cars": owned[2],
        "double_duplicate_cars": owned[3],
    }
