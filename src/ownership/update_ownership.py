"""Functions for updating ownership lists."""

import json
from collections import defaultdict
from typing import Any

from config.paths import (
    OWNED_DIR,
    OWNED_PATH,
    RAW_CI_PATH,
    TD_JSON_PATH,
    TDR_JSON_PATH,
)
from src.utils.timer import timer


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


def _get_tune(car: dict) -> str:
    """Extracts the tune from the car's info"""
    eng = car["engineMajor"]
    eng_m = car["engineMinor"]
    wei = car["weightMajor"]
    wei_m = car["weightMinor"]
    cha = car["chassisMajor"]
    cha_m = car["chassisMinor"]
    if (eng, wei, cha) == (1, 1, 1) and (eng_m, wei_m, cha_m) == (0, 0, 0):
        return "000"
    else:
        return f"{eng}{wei}{cha}"


def create_new_big_list(id_map: dict, player_deck: list[dict], lowest_unlocked: int) -> list:
    """Creates list of every car in garage."""
    with open(RAW_CI_PATH, "r", encoding="utf-8") as f:
        ci_list = json.load(f)
    ci_dict = {ci["rid"]: ci for ci in ci_list}

    new_big_list = []
    for car in player_deck:
        rid = id_map[car["cardId"]]
        rq = ci_dict[rid]["rq"]
        if rq < lowest_unlocked and not car["locked"]:
            continue

        new_big_list.append((rq, rid, _get_tune(car)))

    # Sort: First by RQ (desc), then rid (asc), then tune (desc)
    new_big_list.sort(key=lambda x: (-x[0], x[1].lower(), -int(x[2])))
    return new_big_list


def create_owned_lists(big_list: list) -> dict[str, list]:
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


def save_garage_json_strs(td_str: str, tdr_str: str) -> None:
    """Saves JSONs formatted as strings to JSON files."""
    td = json.loads(td_str)
    tdr = json.loads(tdr_str)

    with open(OWNED_DIR / "garage_td.json", "w", encoding="utf-8") as f:
        json.dump(td, f)
    with open(OWNED_DIR / "garage_td_records.json", "w", encoding="utf-8") as f:
        json.dump(tdr, f)


def update_guid_rid_map(car_infos: list[dict[str, Any]]) -> dict[str, str]:
    """Uses the latest car infos to update the guid -> rid map"""
    id_rid_map = {}
    for car_dict in car_infos:
        id_rid_map[car_dict["guid"]] = car_dict["rid"]

    with open(OWNED_DIR / "id_map.json", "w", encoding="utf-8") as f:
        json.dump(id_rid_map, f)
    return id_rid_map


def open_garage_dat() -> list[dict[str, Any]]:
    """Opens and parses the Garage.dat file"""
    with open(OWNED_DIR / "Garage.dat", "r", encoding="utf-8") as f:
        dat = f.read()
    dat = dat[dat.find("[") :]
    dat = json.loads(dat)
    return dat


@timer
def update_ownership(lowest_unlocked: int = 0) -> None:
    """Updates the owned lists with latest Garage.dat file."""
    player_deck = open_garage_dat()
    with open(RAW_CI_PATH, "r", encoding="utf-8") as f:
        ci_list = json.load(f)
    id_map = update_guid_rid_map(ci_list)

    new_big_list = create_new_big_list(id_map, player_deck, lowest_unlocked)
    owned_lists = create_owned_lists(new_big_list)

    with open(OWNED_PATH, "w", encoding="utf-8") as f:
        json.dump(owned_lists, f)


def upload_garage(contents: bytes) -> None:
    """Saves contents to OWNED_DIR/Garage.dat."""
    garage_path = OWNED_DIR / "Garage.dat"
    garage_path.write_bytes(contents)
