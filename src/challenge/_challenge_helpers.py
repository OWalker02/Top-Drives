"""Helper functions for challenge solving."""

import json
import math
from typing import Literal

import numpy as np
import pandas as pd

from config.challenge import COPY_COLS
from config.paths import TRACK_UPPERS_PATH
from src.utils.timer import timer


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


# region Restrictions


def _extract_restrictions(challenge_dict: dict) -> set[str]:
    """Gets a set of all restrictions that appear in the challenge."""
    all_restrictions = set()

    # Iterate through all rounds, getting the restrictions
    for round_dict in challenge_dict.values():
        round_restrictions = round_dict["Restrictions"]
        for restriction in round_restrictions:
            all_restrictions.add(restriction)

    return all_restrictions


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


# endregion


# region DF Creation
def _calc_points(
    track_time: float, track_name: str, time_to_beat: float, track_uppers: dict
) -> int:
    """Calculates the points scored by track_time against time_to_beat on a certain track."""
    # Convert 0 -> np.inf
    track_time = np.inf if track_time == 0 else track_time
    time_to_beat = np.inf if time_to_beat == 0 else time_to_beat

    # If nan, assume loss
    if pd.isna(track_time):
        return -50

    upper = track_uppers[track_name.split("_")[0]]

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
            pts = upper * x - upper

        # Win/Lose
        if track_time < time_to_beat:
            pts *= -1

    else:
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


def _col_in_range(df: pd.DataFrame, restriction: str) -> pd.Series:
    """Makes an int boolean column for a range restriction (RQ or year)."""
    col = restriction.split("_")[0].lower()
    lower = int(restriction.split("_")[2])
    upper = int(restriction.split("_")[3])
    rest_col = df[col].apply(lambda x: 1 if lower <= x <= upper else 0)
    return rest_col


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
def _make_track_cols(
    encoded_df: pd.DataFrame, challenge_dict: dict, challenge_info: dict
) -> dict[str, pd.Series]:
    """
    Creates a column for every track in every round, populating with points against the target
    time.
    """
    with open(TRACK_UPPERS_PATH, encoding="utf-8") as f:
        track_uppers = json.load(f)
    sr = challenge_info["start_round"]
    er = challenge_info["end_round"]
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


# endregion


# region Filters


def _filter_penalty(encoded_df: pd.DataFrame, max_penalty: int) -> pd.Series:
    """Returns mask of DataFrame with only rows/cars with penaly below max penalty"""
    return encoded_df["penalty"] <= max_penalty


def _filter_restrictions(
    challenge_df: pd.DataFrame, restrictions: set, set_op: Literal["union", "intersection"]
) -> pd.Series:
    """Returns a mask of the intersection or union of all restrictions passed."""
    masks = []
    for restriction in restrictions:
        masks.append(challenge_df[restriction].astype(bool))

    if len(masks) == 0:
        return pd.Series(True, index=challenge_df.index)

    if len(masks) == 1:
        return masks[0]

    combined_mask = masks[0]
    if set_op == "intersection":
        for mask in masks[1:]:
            combined_mask = combined_mask & mask
    elif set_op == "union":
        for mask in masks[1:]:
            combined_mask = combined_mask | mask

    return combined_mask


def _filter_winners(challenge_df: pd.DataFrame, track_names: list) -> pd.Series:
    """Returns a mask of the rows/cars that win at least one race"""
    lose_all_mask = challenge_df[track_names].max(axis=1) < 0
    return ~lose_all_mask


def _filter_challenge_df(
    challenge_df: pd.DataFrame,
    encoded_df: pd.DataFrame,
    track_keys: list,
    all_restrictions: set,
    universal_restrictions: set,
    max_penalty: int,
    only_owned: bool,
) -> pd.DataFrame:
    """Filters the challenge DataFrame to remove unnecessary rows."""
    if only_owned:
        return challenge_df[challenge_df["owned"]]

    # Get all filter masks
    full_useful_mask = _filter_restrictions(challenge_df, all_restrictions, "union")
    low_penalty_mask = _filter_penalty(encoded_df, max_penalty)
    meets_univ_restrictions_mask = _filter_restrictions(
        challenge_df, universal_restrictions, "intersection"
    )
    wins_a_race_mask = _filter_winners(challenge_df, track_keys)

    # Apply filters
    return challenge_df[
        full_useful_mask & low_penalty_mask & meets_univ_restrictions_mask & wins_a_race_mask
    ]

    return (
        challenge_df[full_useful_mask],
        challenge_df[low_penalty_mask],
        challenge_df[meets_univ_restrictions_mask],
        challenge_df[wins_a_race_mask],
    )


# endregion
