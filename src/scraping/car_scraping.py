import json
import time
from datetime import datetime

import numpy as np
import requests
from tqdm import tqdm

from config.constants import SURFACE_MAP
from config.paths import (
    COMPONENTS_FULL_PATH,
    INDEX_FULL_PATH,
    RAW_CI_PATH,
    TRACKSET_PATH,
)
from config.scraping import CAR_HEADERS
from src.scraping._scraping_helpers import (
    _filter_ci_dicts,
    _filter_str,
    _get_index_comp_urls,
    _get_track_maps,
    _get_uppers_map,
    _load_raw_tas,
    _scrape_car,
    _update_and_save,
)
from src.utils.timer import timer


@timer
def update_js_files() -> None:
    """
    Uses requests to get the components.js and index.js files, saving their contents as a txt file.
    """
    components_url, index_url = _get_index_comp_urls()
    r = requests.get(components_url, headers=CAR_HEADERS, timeout=10)
    components_js = r.text
    with open(COMPONENTS_FULL_PATH, "w", encoding="utf-8") as f:
        f.write(components_js)

    r = requests.get(index_url, headers=CAR_HEADERS, timeout=10)
    index_js = r.text
    with open(INDEX_FULL_PATH, "w", encoding="utf-8") as f:
        f.write(index_js)


@timer
def load_js_files() -> tuple[str, str]:
    """Loads components and index js strings, returns (components, index)."""
    with open(COMPONENTS_FULL_PATH, "r", encoding="utf-8") as f:
        components_js = f.read()

    with open(INDEX_FULL_PATH, "r", encoding="utf-8") as f:
        index_js = f.read()

    return components_js, index_js


@timer
def update_car_info(index_full: str) -> list[dict]:
    """Update the car information dictionary."""

    # Extract just car list
    raw_list = _filter_str(index_full, "car_info")

    list_str = raw_list.encode("utf-8").decode("unicode_escape")

    # Convert to dict
    cars = json.loads(list_str)

    with open(RAW_CI_PATH, "w", encoding="utf-8") as f:
        json.dump(cars, f)

    return cars


@timer
def update_track_info(components_full: str, index_full: str) -> list[dict[str, str]]:
    """Update the trackset information."""
    tracks = []

    raw_list = _filter_str(components_full, "track_types")
    track_list = json.loads(raw_list)
    track_map = _get_track_maps(index_full)
    uppers_map = _get_uppers_map(index_full)

    for track_dict in track_list:
        full_track_id = track_dict["id"]
        track_id = full_track_id.split("Z50")[0]
        for surface in track_dict["types"]:
            try:
                track_name = f"{track_map[track_id]} / {SURFACE_MAP[surface]}"
            except KeyError as e:
                print(track_id, surface)
                raise e
            tracks.append(
                {
                    "id": f"{track_id}_a{surface}",
                    "name": track_name,
                    "upper": uppers_map[full_track_id],
                }
            )
    with open(TRACKSET_PATH, "w", encoding="utf-8") as f:
        json.dump(tracks, f)

    return tracks


@timer
def scrape(
    car_info_dicts: list[dict[str, str]], delay: float = 0.5, skip_seconds: int = 3600
) -> dict:
    """
    Scrapes all cars in car_info_dicts, with delay between each request, returning the list of tas
    dicts.
    """
    session = requests.Session()
    session.headers.update(CAR_HEADERS)
    tas_dicts = _load_raw_tas()
    new_tas = {}
    i, rid = None, None
    prev_class = "X"
    pbar = None

    filtered_info_dicts = _filter_ci_dicts(car_info_dicts, tas_dicts, skip_seconds)
    print(f"Scraping {len(filtered_info_dicts)} cars.")

    try:
        for i, car in enumerate(filtered_info_dicts):
            rid = car["rid"]
            car_class = car["class"]
            if car_class != prev_class:
                prev_class = car_class
                class_dicts = [cd for cd in filtered_info_dicts if cd["class"] == car_class]
                if pbar:  # type: ignore # noqa: F821
                    pbar.close()  # noqa: F821
                pbar = tqdm(range(len(class_dicts)), desc=f"  Scraping Class {car_class}")

            car_dicts = _scrape_car(session, rid)

            if car_dicts:
                new_tas[rid] = {
                    "updated": datetime.today().strftime("%Y-%m-%d-%H:%M"),
                    "dicts": car_dicts,
                }
            else:
                new_tas[rid] = {"updated": datetime.today().strftime("%Y-%m-%d-%H:%M"), "dicts": []}

            pbar.update(1)  # type: ignore
            rand_delay = np.random.gamma(shape=8, scale=0.1) * delay * 10 / 8
            time.sleep(rand_delay)

            if i % 100 == 0:
                _update_and_save(tas_dicts, new_tas)

    except Exception as e:
        print(f"Error occured on car {i}: {rid}")
        raise e

    finally:
        # Save progress no matter what
        _update_and_save(tas_dicts, new_tas)

    return tas_dicts
