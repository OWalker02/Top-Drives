"""Helper functions for preprocessing.py"""

from typing import Any

import numpy as np
import pandas as pd

from config.constants import RARITY_BOUNDS
from config.preprocessing import NON_TRACK_COLS, PENALTIES


def _deduplicate_car_lists(car_list: list) -> list:
    """Removes all duplicate dictionaries from a list."""
    seen_car_values = set()
    deduplicated = []
    for car_dict in car_list:
        car_values = tuple(car_dict.values())
        if car_values not in seen_car_values:
            seen_car_values.add(car_values)
            deduplicated.append(car_dict)
    return deduplicated


def _convert_cols(df: pd.DataFrame, cols: list[str], dtype: type) -> pd.DataFrame:
    """Converts a list of columns to int, float, or bool."""
    if dtype not in [int, float, bool]:
        raise ValueError(f"dtype must be int, float, or bool, got {dtype}")

    df = df.copy()

    for col in cols:
        if dtype is bool:
            df[col] = df[col] == "true"
        else:
            df[col] = df[col].astype(dtype, errors="ignore")
    return df


def _get_tracks(df: pd.DataFrame) -> tuple[list, list]:
    """Extracts all non-test bowl tracks from df columns."""
    track_cols = [col for col in df.columns if col not in NON_TRACK_COLS]
    standard_tracks = [track for track in track_cols if not track.startswith("Test")]
    test_tracks = [track for track in track_cols if track.startswith("Test")]

    return standard_tracks, test_tracks


def _remove_invalid_cars(df: pd.DataFrame) -> pd.DataFrame:
    """
    Removes all cars which cannot be obtained.
    e.g. if a car is owned at tune 332, version 0 of that car cannot be obtained at 323 or 233).
    """
    df = df.copy()

    mask = (df["engine_diff"] < 0) | (df["weight_diff"] < 0) | (df["chassis_diff"] < 0)
    return df.loc[~mask]


def _get_car_mask(df: pd.DataFrame, car: tuple[int, str, int, Any]) -> pd.Series:
    """Mask for a specific car."""
    df = df.copy()

    rq, make_model, year, _ = car
    return (df["rq"] == rq) & (df["make_model"] == make_model) & (df["year"] == year)


def _make_owned_df(car_list: list[tuple]) -> pd.DataFrame:
    """Makes a dataframe with information of only owned cars."""
    owned_rows = []
    for car in car_list:
        owned_row = {
            "rid": car[1],
            "owned": True,
            "owned_engine_up": int(car[2][0]),
            "owned_weight_up": int(car[2][1]),
            "owned_chassis_up": int(car[2][2]),
        }
        owned_rows.append(owned_row)
    return pd.DataFrame(owned_rows)


def _add_owned_stats(df: pd.DataFrame, car_list: list[tuple]) -> pd.DataFrame:
    """Adds the owned and owned tune columns."""
    df = df.copy()

    owned_df = _make_owned_df(car_list)
    # Update full df with new owned cars info
    merged = df.merge(owned_df, on="rid", how="left")
    # Clean nans
    merged["owned"] = merged["owned"].fillna(False)
    merged["owned"] = merged["owned"].astype(bool)
    for col in ["owned_engine_up", "owned_weight_up", "owned_chassis_up"]:
        merged[col] = merged[col].fillna(0).astype(int)

    return merged


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


def _calc_unowned_pen(df: pd.DataFrame) -> pd.Series:
    """Calculates the unowned penalty for each row (if unowned)."""
    unowned_pen = pd.Series(0.0, index=df.index)

    for rarity, pen in PENALTIES["unowned"].items():
        mask = (df["rarity"] == rarity) & (~df["owned"])
        unowned_pen[mask] = pen

    # Prize car penalties
    mask = df["prize"] & (~df["owned"])
    unowned_pen[mask] = np.inf

    return unowned_pen


def _calc_upgrade_pen(df: pd.DataFrame) -> pd.Series:
    """Calculates the upgrade penalty for each row."""
    upgrade_pen = pd.Series(0.0, index=df.index)

    for rarity, pen in PENALTIES["upgrade"].items():
        for ups_left in range(0, 6):
            mask = (df["rarity"] == rarity) & (df["ups_left"] == ups_left)
            upgrade_pen[mask] = ups_left * pen * (df.loc[mask, "car_version"] + 1)

    return upgrade_pen


def _calc_rq_pen(df: pd.DataFrame) -> pd.Series:
    """Calculates the RQ based penalty for each row."""
    rq_pen = pd.Series(0.0, index=df.index)

    for rarity, (lb, ub) in RARITY_BOUNDS.items():
        mask = df["rarity"] == rarity
        rq_pen[mask] = ub - df.loc[mask, "rq"]

    return rq_pen


def _joined_col_to_set(df_col: pd.Series) -> set:
    """Splits a string in the form item1/item2/... into a set."""
    all_elements = set()
    for unique_str in df_col.unique():
        strings = unique_str.split("/")
        for string in strings:
            all_elements.add(string)

    return all_elements


def _list_col_to_set(df_col: pd.Series) -> set:
    """Makes a set of all elements in all lists in a column."""
    all_elements = set()
    for unique_list in df_col.unique():
        all_elements.update(unique_list)

    return all_elements


def _time_str_to_secs(time_str: str) -> float:
    """Converts one time string (MM:SS:ds) to seconds float."""
    if time_str == "DNF":
        return np.inf
    if not time_str:
        return np.nan
    try:
        parts = time_str.split(":")
        return float(parts[0]) * 60 + float(parts[1]) + float(parts[2]) / 100
    except Exception as e:
        print("Encountered exception:", e)
        return np.nan
