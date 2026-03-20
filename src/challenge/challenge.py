"""Challenge."""

import json
import math

import numpy as np
import pandas as pd

from config.challenge import CHALLENGE_INFO, CHALLENGE_SETUP, COLOUR_RANGES, COPY_COLS
from config.paths import CHALLENGES_DIR, TRACK_UPPERS_PATH
from src.utils.timer import timer


@timer
def load_challenge_dict(challenge_cat: str, challenge_num: int) -> dict:
    """Loads challenge_dict for specific challenge_cat & challenge_num."""
    challenge_info = get_challenge_info(challenge_cat, challenge_num)
    with open(
        CHALLENGES_DIR / f"{challenge_info['name_start'].replace(' ', '_')}.json", encoding="utf-8"
    ) as f:
        return json.load(f)


def get_challenge_info(challenge_cat: str, challenge_num: int) -> dict:
    """
    Extrcats and merges base information for challenge_cat with specific challenge information for
    challenge_num, from CHALLENGE_INFO.
    """
    base_name_start, base_sr, base_er, base_restrictions = CHALLENGE_INFO[challenge_cat]["base"]
    num_name_start, num_sr, num_er, num_restrictions = CHALLENGE_INFO[challenge_cat][challenge_num]

    # Combine
    challenge_name_start = base_name_start + num_name_start
    start_round = base_sr if num_sr == 0 else num_sr
    end_round = base_er if num_er == 0 else num_er
    challenge_restrictions = base_restrictions | num_restrictions
    challenge_info = {
        "name_start": challenge_name_start,
        "start_round": start_round,
        "end_round": end_round,
        "challenge_restrictions": challenge_restrictions,
    }
    return challenge_info


def get_challenge_setup(
    encoded_df: pd.DataFrame, challenge_cat: str, challenge_num: int, owned_only: bool
) -> dict:
    """
    Extracts and merges base setup information for challenge_cat with specific challenge setup
    information for challenge_num, from CHALLENGE_SETUP.
    """
    base_dict = CHALLENGE_SETUP[challenge_cat]["base"]
    setup_dict = CHALLENGE_SETUP[challenge_cat].get(challenge_num, {})

    sr = setup_dict.get("sr", base_dict["sr"])
    er = setup_dict.get("er", base_dict["er"])

    if owned_only:
        # The combination produces a series of length df.shape[0]
        useful_mask = ((encoded_df["rq"] > 0) & False).astype(bool)
    else:
        # Include rq > 0 incase no other masks:
        mask_all = encoded_df["rq"] > 0
        mask_useful_base = base_dict["useful"](encoded_df).astype(bool)
        mask_useful_spec = setup_dict.get("useful", True)(encoded_df).astype(bool)
        useful_mask = (mask_all & mask_useful_base & mask_useful_spec).astype(bool)
    exclude_rounds = setup_dict.get("exc", [])
    challenge_setup = {
        "sr": sr,
        "er": er,
        "useful_mask": useful_mask,
        "exclude_rounds": exclude_rounds,
    }

    return challenge_setup


def _calc_points(
    track_time: float, track_name: str, time_to_beat: float, track_uppers: dict
) -> int:
    """Calculates the points scored by track_time against time_to_beat on a certain track."""

    # If nan, assume loss
    if pd.isna(track_time):
        return -50

    # Different function for test bowl
    if "Test Bowl" in track_name:
        # pts = 350 * x - 350
        # x = win / lose
        win = max(track_time, time_to_beat)
        lose = min(track_time, time_to_beat)
        if lose == 0:
            pts = 50
        else:
            x = win / lose
            pts = 350 * x - 350

        # Win/Lose
        if track_time < time_to_beat:
            pts *= -1

    else:
        # Get upper pts limit
        upper = track_uppers[track_name]
        # pts = upper * (-1 / (x + 1) + 1)
        # x = (lose - win) / win
        win = min(track_time, time_to_beat)
        lose = max(track_time, time_to_beat)
        if lose == np.inf:
            if win == np.inf:
                return -50
            else:
                pts = 250
        else:
            x = (lose - win) / win
            # print(x)
            pts = upper * (-1 / (x + 1) + 1)

        # Win/Lose
        if track_time > time_to_beat:
            pts *= -1

    # Round close results to 50/-50
    if -50 < pts < 0:
        pts = -50
    if 0 < pts < 50:
        pts = 50

    if pd.isna(pts):
        print("NA time passed:")
        print(track_time, track_name, time_to_beat, pts)
        print(win, lose)
        raise ValueError

    return math.floor(pts)


@timer
def _get_copy_cols(df: pd.DataFrame) -> list:
    """Creates a list of all columns to copy over to challenge df."""
    copy_cols = COPY_COLS["full_col"]
    copy_prefixes = COPY_COLS["col_prefix"]
    for col in df.columns:
        if any(col.startswith(pref) for pref in copy_prefixes):
            if col in ["make_model", "make"]:
                continue
            copy_cols.append(col)
    return copy_cols


@timer
def _filter_useful(encoded_df: pd.DataFrame, challenge_setup: dict) -> pd.Series:
    """
    Returns mask of DataFrame with only rows/cars that are owned or meet the useful mask from the
    challenge's CHALLENGE_SETUP.
    """
    useful_mask = challenge_setup["useful_mask"]
    owned_mask = encoded_df["owned"]

    return owned_mask | useful_mask


@timer
def _filter_penalty(encoded_df: pd.DataFrame, max_penalty: int) -> pd.Series:
    """Returns mask of DataFrame with only rows/cars with penaly below max penalty"""
    return encoded_df["penalty"] <= max_penalty


@timer
def _make_track_cols(
    encoded_df: pd.DataFrame, challenge_dict: dict, challenge_setup: dict
) -> dict[str, pd.Series]:
    """
    Creates a column for every track in every round, populating with points against the target
    time.
    """
    with open(TRACK_UPPERS_PATH, encoding="utf-8") as f:
        track_uppers = json.load(f)
    sr = challenge_setup["sr"]
    er = challenge_setup["er"]
    track_cols = {}
    for round_i, round_dict in challenge_dict.items():
        round_i = int(round_i)
        if round_i < sr or round_i > er:
            continue
        for track_j, (track_name, track_time) in round_dict["Tracks"].items():
            # Add column to dict
            track_col = encoded_df[track_name].apply(
                _calc_points, args=(track_name, track_time, track_uppers)
            )
            track_cols[f"{round_i}.{track_j}"] = track_col
    return track_cols


@timer
def _extract_restrictions(challenge_dict: dict) -> set[str]:
    """Gets a set of all restrictions that appear in the challenge."""
    all_restrictions = set()

    # Iterate through all rounds, getting the restrictions
    for round_dict in challenge_dict.values():
        round_restrictions = round_dict["Restrictions"]
        for restriction in round_restrictions:
            all_restrictions.add(restriction)

    return all_restrictions


def _col_in_range(df: pd.DataFrame, restriction: str) -> pd.Series:
    """Makes an int boolean column for a range restriction (RQ or year)."""
    col = restriction.split("_")[0].lower()
    lower = int(restriction.split("_")[2])
    upper = int(restriction.split("_")[3])
    rest_col = df[col].apply(lambda x: 1 if lower <= x <= upper else 0)
    return rest_col


@timer
def _make_restriction_col(df: pd.DataFrame, restriction: str) -> pd.Series:
    """
    Makes a column for any non-standard restriction (for ex. restA/restB/... or RQ_range_x_y).
    """
    df = df.copy()
    if "range" in restriction and len(restriction.split("_")) == 4:
        new_col = _col_in_range(df, restriction)
    elif "/" in restriction:
        sub_restrictions = restriction.split("/")
        # Check all sub-restrictions have a col
        for sub_restriction in sub_restrictions:
            if "range " in sub_restriction:
                df[sub_restriction] = _col_in_range(df, sub_restriction)
        # Now get full restriction
        new_col = df[sub_restrictions].max(axis=1)
    else:
        print(f"{restriction} invalid")
        raise KeyError

    return new_col


@timer
def _get_universal_restrictions(challenge_dict: dict, all_restrictions: set) -> set:
    """
    Makes a set of all restrictions that appear in every round in the challenge and need 5x the
    restriction.
    """
    universal_restrictions = all_restrictions.copy()
    for round_dict in challenge_dict.values():
        # Go through all universal restrictions and check if they are in this round
        for univ_restriction in list(universal_restrictions):
            if univ_restriction not in round_dict["Restrictions"].keys():
                universal_restrictions.remove(univ_restriction)
            else:
                if round_dict["Restrictions"][univ_restriction] != 5:
                    universal_restrictions.remove(univ_restriction)
    return universal_restrictions


def _filter_restrictions(challenge_df: pd.DataFrame, restrictions: set) -> pd.Series:
    """Returns a mask of the intersection of all restrictions passed."""
    masks = []
    for restriction in restrictions:
        masks.append(challenge_df[restriction].astype(bool))

    if len(masks) == 0:
        return pd.Series(True, index=challenge_df.index)

    if len(masks) == 1:
        return masks[0]

    combined_mask = masks[0]
    for mask in masks[1:]:
        combined_mask = combined_mask & mask
    return combined_mask


def _filter_winners(challenge_df: pd.DataFrame, track_names: list) -> pd.Series:
    """Returns a mask of the rows/cars that win at least one race"""
    lose_all_mask = challenge_df[track_names].max(axis=1) < 0
    return ~lose_all_mask


@timer
def make_challenge_df(
    encoded_df: pd.DataFrame,
    challenge_cat: str,
    challenge_num: int,
    only_owned: bool = False,
    max_penalty: int = 15000,
) -> pd.DataFrame:
    """
    Makes a challenge DataFrame from the full encoded DataFrame.
    - Extracts only needed columns
    - Adds a column for each track in challenge
    - Reduces rows to only useful rows/cars
    """
    # Load challenge dicts
    challenge_setup = get_challenge_setup(encoded_df, challenge_cat, challenge_num, only_owned)
    challenge_dict = load_challenge_dict(challenge_cat, challenge_num)

    # Set up df
    copy_cols = _get_copy_cols(encoded_df)
    challenge_df = encoded_df[copy_cols].copy()

    # Add track columns
    track_cols = _make_track_cols(encoded_df, challenge_dict, challenge_setup)
    for track, track_col in track_cols.items():
        challenge_df[track] = track_col

    # Get a set of all restrictions in challenge
    all_restrictions = _extract_restrictions(challenge_dict)
    # Make sure every restriction has a column
    for restriction in all_restrictions:
        if restriction not in challenge_df.columns:
            new_col = _make_restriction_col(challenge_df, restriction)
            challenge_df[restriction] = new_col

    # Get a set of universal restrictions (5x needed in every round)
    universal_restrictions = _get_universal_restrictions(challenge_dict, all_restrictions)

    # Get all filter masks
    full_useful_mask = _filter_useful(encoded_df, challenge_setup)
    low_penalty_mask = _filter_penalty(encoded_df, max_penalty)
    meets_restrictions_mask = _filter_restrictions(challenge_df, universal_restrictions)
    wins_a_race_mask = _filter_winners(challenge_df, list(track_cols.keys()))

    # Apply filters
    challenge_df = challenge_df[
        full_useful_mask & low_penalty_mask & meets_restrictions_mask & wins_a_race_mask
    ]

    return challenge_df


def get_rq_colour(rq: int) -> str:
    """Gets the 256-colour mode for an RQ."""
    return next(c for low, high, c in COLOUR_RANGES if low <= rq <= high)
