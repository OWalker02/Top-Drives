import json
import os

import requests

from config.challenge import CHALLENGE_INFO
from config.paths import CHALLENGES_DIR
from config.scraping import CAR_HEADERS, CHALLENGE_HEADERS
from src.scraping._scraping_helpers import _load_raw_tas, _scrape_car
from src.utils.timer import timer


def _get_full_name(challenge_base: dict, challenge_specific: dict) -> str:
    """Gets the full name from the base challenge and numbered challenge info dicts."""
    challenge_pref = challenge_base.get("pref", "")
    challenge_suf = challenge_specific.get("suf", "")
    return challenge_pref + challenge_suf


@timer
def _request_challenge(payload: dict) -> dict:
    """Requests the payload from the TDR challenge url."""
    r = requests.post(
        "https://charlie.topdrivesrecords.com/getCgById",
        headers=CHALLENGE_HEADERS,
        json=payload,
        timeout=10,
    )
    if r.status_code != 200:
        print(f"Status code: {r.status_code}")
        raise ValueError
    return r.json()


def _extract_time_from_tas(tas, chal_rid, chal_track, chal_tune) -> float:
    """
    Finds the dict in tas that matches given rid and extracts the time for the given track and
    tune.
    """
    for car_dict in tas[chal_rid]["dicts"]:
        car_tune = car_dict["engine_up"] + car_dict["weight_up"] + car_dict["chassis_up"]
        if car_tune == chal_tune:
            return car_dict[chal_track]
    raise KeyError


def _save_challenge_dict(challenge_dict: dict, challenge_name: str, challenge_cat: str) -> None:
    """Saves the challenge dict as a json, creating new category folder if it doesn't exist."""
    if not os.path.exists(CHALLENGES_DIR / challenge_cat):
        os.makedirs(CHALLENGES_DIR / challenge_cat)

    with open(
        CHALLENGES_DIR / challenge_cat / f"{challenge_name}.json", "w", encoding="utf-8"
    ) as f:
        json.dump(challenge_dict, f)


@timer
def _create_challenge_dict(
    scraped_challenge: dict, challenge_base: dict, challenge_specific: dict
) -> dict:
    """Creates the challenge dict from the scraped challenge information."""
    challenge_dict = {}
    session = requests.Session()
    session.headers.update(CAR_HEADERS)
    tas = _load_raw_tas()

    # Go through rounds to create the challenge dict
    for round_i, round_info in enumerate(scraped_challenge["rounds"]):
        round_num = round_i + 1
        # RQ
        round_dict = {"RQ limit": round_info["rqLimit"], "Tracks": {}, "Restrictions": {}}
        round_dict["RQ range"] = round_info["filter"].get("rqModel", [10, 150])

        # Restrictions
        round_restrictions = challenge_base.get("rest", {}) | challenge_specific.get("rest", {})
        for restriction, quantity_list in round_restrictions.items():
            for quantity_tuple in quantity_list:
                if quantity_tuple[0][0] <= round_num <= quantity_tuple[0][1]:
                    round_dict["Restrictions"][restriction] = quantity_tuple[1]

        # Races
        for race_i, race_dict in enumerate(round_info["races"]):
            challenge_time = None

            if race_dict["time"]:
                challenge_time = race_dict["time"]
            else:
                try:
                    challenge_time = _extract_time_from_tas(
                        tas, race_dict["rid"], race_dict["track"], race_dict["tune"]
                    )
                except KeyError:
                    print(
                        f"Time for {race_dict['rid']} on {race_dict['track']} not given and not "
                        "scraped. Scraping new."
                    )
                    car_tas = {"updated": None, "dicts": _scrape_car(session, race_dict["rid"])}
                    challenge_time = _extract_time_from_tas(
                        car_tas, race_dict["rid"], race_dict["track"], race_dict["tune"]
                    )

            if challenge_time or challenge_time == 0:
                round_dict["Tracks"][str(race_i + 1)] = [race_dict["track"], challenge_time]
            else:
                raise KeyError

        challenge_dict[str(round_num)] = round_dict

    return challenge_dict


@timer
def get_challenge_dict(challenge_cat: str, challenge_num: int) -> dict:
    """
    Scrapes challenge information and creates a json file with important info in for challenge
    solving.
    """
    challenge_base = CHALLENGE_INFO[challenge_cat]["base"]
    challenge_specific = CHALLENGE_INFO[challenge_cat][challenge_num]

    # Request challenge info
    challenge_name = _get_full_name(challenge_base, challenge_specific)
    challenge_payload = {"date": challenge_name}
    scraped_challenge = _request_challenge(challenge_payload)

    challenge_dict = _create_challenge_dict(scraped_challenge, challenge_base, challenge_specific)

    _save_challenge_dict(challenge_dict, challenge_name, challenge_cat)
    return challenge_dict
