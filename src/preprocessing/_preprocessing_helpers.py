"""Helper functions for preprocessing.py"""

from typing import Any, List, Set, Tuple

import numpy as np
import pandas as pd

from config.constants import RARITY_BOUNDS
from config.preprocessing import NON_TRACK_COLS, PENALTIES


def _convert_cols(df: pd.DataFrame, cols: List[str], dtype: type) -> pd.DataFrame:
    """Converts a list of columns to int, float, or bool."""
    if dtype not in [int, float, bool]:
        raise ValueError(f"dtype must be int, float, or bool, got {dtype}")

    df = df.copy()

    for col in cols:
        if dtype is bool:
            df[col] = df[col] == "Yes"
        else:
            df[col] = df[col].astype(dtype)
    return df


def _get_standard_tracks(df: pd.DataFrame) -> List:
    """Extracts all non-test bowl tracks from df columns."""
    track_cols = [col for col in df.columns if col not in NON_TRACK_COLS]
    standard_tracks = [track for track in track_cols if not track.startswith("Test")]

    return standard_tracks


def _remove_invalid_cars(df: pd.DataFrame) -> pd.DataFrame:
    """
    Removes all cars which cannot be obtained.
    e.g. if a car is owned at tune 332, version 0 of that car cannot be obtained at 323 or 233).
    """
    df = df.copy()

    mask = (df["engine_diff"] < 0) | (df["weight_diff"] < 0) | (df["chassis_diff"] < 0)
    return df.loc[~mask]


def _get_car_mask(df: pd.DataFrame, car: Tuple[int, str, int, Any]) -> pd.Series:
    """Mask for a specific car."""
    df = df.copy()

    rq, make_model, year, _ = car
    return (df["rq"] == rq) & (df["make_model"] == make_model) & (df["year"] == year)


def _add_owned_stats(df, car_list):
    """Adds the owned and owned tune columns."""
    df = df.copy()

    for car in car_list:
        car_mask = _get_car_mask(df, car)
        df.loc[car_mask, "owned"] = True
        df.loc[car_mask, "owned_engine_up"] = int(car[3][0])
        df.loc[car_mask, "owned_weight_up"] = int(car[3][1])
        df.loc[car_mask, "owned_chassis_up"] = int(car[3][2])
    return df


def _calc_upgrade_diffs(df: pd.DataFrame):
    """Adds columns for differences between owned and max tune levels."""
    df = df.copy()

    df["engine_diff"] = df["engine_up"] - df["owned_engine_up"].clip(lower=1)
    df["weight_diff"] = df["weight_up"] - df["owned_weight_up"].clip(lower=1)
    df["chassis_diff"] = df["chassis_up"] - df["owned_chassis_up"].clip(lower=1)
    df["ups_left"] = df[["engine_diff", "weight_diff", "chassis_diff"]].sum(axis=1)
    return df


def _add_rarity(df: pd.DataFrame) -> pd.DataFrame:
    """Adds rarity column."""
    df = df.copy()

    df["rarity"] = ""

    for rarity, (lb, ub) in RARITY_BOUNDS.items():
        mask = df["rq"].between(lb, ub)
        df.loc[mask, "rarity"] = rarity

    return df


def _calc_unowned_pen(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates the unowned penalty for each row (if unowned)."""
    df = df.copy()

    df["unowned_pen"] = 0

    for rarity, pen in PENALTIES["unowned"].items():
        mask = (df["rarity"] == rarity) & (df["owned"] is False)
        df.loc[mask, "unowned_pen"] = pen

    # Prize car penalties
    mask = df["prize"] & (df["owned"] is False)
    df["unowned_pen"] = df["unowned_pen"].astype(float)
    df.loc[mask, "unowned_pen"] = np.inf

    return df


def _calc_upgrade_pen(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates the upgrade penalty for each row."""
    df = df.copy()

    df["upgrade_pen"] = 0

    for rarity, pen in PENALTIES["upgrade"].items():
        for ups_left in range(0, 6):
            mask = (df["rarity"] == rarity) & (df["ups_left"] == ups_left)
            df.loc[mask, "upgrade_pen"] = ups_left * pen * df.loc[mask, "car_version"]

    return df


def _joined_col_to_set(df_col: pd.Series) -> Set:
    """Splits a string in the form item1/item2/... into a set."""
    all_elements = set()
    for unique_str in df_col.unique():
        strings = unique_str.split("/")
        for string in strings:
            all_elements.add(string)

    return all_elements
