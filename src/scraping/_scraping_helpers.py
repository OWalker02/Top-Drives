"""Helper functions for scrapers.py"""

import numpy as np
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from config.challenge import CONDITION_MAP


def _get_other_conditions(track_div: WebElement) -> str:
    """Returns condition suffix string ' (C)', ' (R)', or '' for a track div."""
    i_elements = track_div.find_elements(By.TAG_NAME, "i")
    if i_elements:
        i_class = i_elements[0].get_attribute("class") or ""
        if "tdicon-clearance" in i_class.split(" "):
            return " (C)"
        elif "tdicon-roll" in i_class.split(" "):
            return " (R)"
    return ""


def _split_into_groups(car_count: int) -> list[tuple[int, int]]:
    """
    Splits car_count into groups of 7, using 8 where needed to avoid remainders.
    Falls back to variable-size final group if unsolvable.
    """
    groups = []
    if car_count % 7 == 0:
        for i in range(0, car_count, 7):
            groups.append((i, i + 7))
    else:
        solved = False
        max_eights = car_count // 8  # Check the max number of groups size 8
        # Check all combos of groups of size 7 and 8
        for num_add_one in range(1, max_eights + 1):
            # If using this combo works, make it
            if (car_count - num_add_one * 8) % 7 == 0:
                for i in range(0, car_count - num_add_one * 8, 7):
                    groups.append((i, i + 7))
                for j in range(car_count - num_add_one * 8, car_count, 8):
                    groups.append((j, j + 8))
                solved = True
                break
        if not solved:
            for i in range(0, car_count, 7):
                groups.append((i, min(i + 7, car_count)))
    return groups


def _get_challenge_name(challenge_element: WebElement) -> str:
    challenge_span = challenge_element.find_element(By.XPATH, "./div/span")
    right_span = challenge_span.find_element(By.XPATH, "./span")
    name_start = right_span.get_attribute("innerHTML").strip()  # type: ignore
    name_end = challenge_span.get_attribute("innerHTML").split(">")[-1].strip()  # type: ignore
    return f"{name_start} {name_end}"


def _split_car_row_html(car_row_html: str, tune: tuple[int, int, int]) -> dict[str, str]:
    """Parses a car row's HTML and returns a dict of core stats and tune values."""
    stats = car_row_html.split("Car_HeaderBackDropRight")[1].split('Car_HeaderStatValue">')[1:]
    stats = [s.split("<")[0] for s in stats]
    stats_dict = {
        "rq": car_row_html.split('BaseCard_Header2Right2">')[1].split("</div>")[0].strip(),
        "make": car_row_html.split("</b>")[1].split("</div>")[0].strip(),
        "model": car_row_html.split('_Header2Bottom">')[1].split("</div>")[0].strip(),
        "make_model": (
            car_row_html.split('class="Car_HeaderName')[1].split(">")[1].split("</div")[0].strip()
        ),
        "year": (
            car_row_html.split('Car_HeaderBlockYear"')[1].split(">")[1].split("</div")[0].strip()
        ),
        "top_speed": stats[0],
        "zero_sixty": stats[1],
        "handling": stats[2],
        "engine_up": tune[0],
        "weight_up": tune[1],
        "chassis_up": tune[2],
    }
    return stats_dict


def _get_rq_limit(soup):
    """Extracts a round's RQ limit from a page soup."""
    return int(soup.find(class_="Cg_RqText").get_text().split("/")[1])


def _convert_to_seconds(time_str):
    """
    Tries to convert a string in format "MM:SS:ds" to a float, returning np.inf if invalid string
    passed.
    """
    try:
        time_in_seconds = 0
        time_in_seconds += float(time_str.split(":")[0]) * 60  # minutes to seconds
        time_in_seconds += float(time_str.split(":")[1])  # seconds
        time_in_seconds += float(time_str.split(":")[2]) / 100  # deci-
        time_in_seconds = round(time_in_seconds, 2)
        return round(float(time_in_seconds), 2)
    except (ValueError, IndexError, AttributeError):
        return np.inf


def _get_restrictions(challenge_info, r):
    """Extracts the restrictions for a specific round."""
    restrictions = {}
    rq_range = [0, 150]
    for restriction, value_tuples in challenge_info["challenge_restrictions"].items():
        # Find the tuple for the current round
        for value_tuple in value_tuples:
            if value_tuple[0][0] <= r + 1 <= value_tuple[0][1]:
                # If rq involved, treat differently
                if "RQ range" in restriction:
                    rq_range = [int(rq) for rq in restriction.split(" ")[2:]]
                else:
                    restrictions[restriction] = value_tuple[1]
    return restrictions, rq_range


def _get_track_name(track, t, row_contents):
    name_base = row_contents[t * 3]
    if name_base.endswith("%"):
        name_base = name_base[:-3]

    extra = ""
    if track.find(class_="tdicon-roll"):
        extra = " (R)"
    elif track.find(class_="tdicon-clearance"):
        extra = " (C)"

    track_id = track.get("data")
    condition = CONDITION_MAP[track_id.split("_")[-1][1:]]

    return f"{name_base}{extra} / {condition}"


def _get_track_time(track_name, t, row_contents):
    if track_name.startswith("Test"):
        return int(row_contents[t * 3 + 1])
    else:
        return _convert_to_seconds(row_contents[t * 3 + 1])
