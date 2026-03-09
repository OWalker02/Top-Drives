"""
Functions for preprocessing from raw scraped json data to a preprocessed csv file, and/or a one-hot
encoded version.
"""

import json

import numpy as np
import pandas as pd

from config.paths import OWNED_PATH, RAW_SCRAPED_JSON_PATH
from config.preprocessing import (
    BOOL_COLS,
    FLOAT_COLS,
    INT_COLS,
    SIMPLE_ENCODE_COLS,
    TEMP_COLS,
)
from src.preprocessing._preprocessing_helpers import (
    _add_owned_stats,
    _add_rarity,
    _calc_unowned_pen,
    _calc_upgrade_diffs,
    _calc_upgrade_pen,
    _convert_cols,
    _get_standard_tracks,
    _joined_col_to_set,
    _remove_invalid_cars,
)
from src.utils.timer import timer


@timer
def _merge_times_and_info() -> pd.DataFrame:
    """
    Merges times/stats and info lists (from config.paths.RAW_SCRAPED_JSON_PATH) of dicts into a
    single DataFrame.
    Joins on shared core keys.
    """
    with open(RAW_SCRAPED_JSON_PATH, "r", encoding="utf-8") as f:
        raw_jsons = json.load(f)
    tas_dict = raw_jsons["car_times_and_stats_dicts"]
    info_dict = raw_jsons["car_info_dicts"]

    # Convert to dfs
    tas_df = pd.DataFrame(tas_dict)
    info_df = pd.DataFrame(info_dict)

    # Merge
    merged = tas_df.merge(info_df, how="outer", on=["rq", "make_model", "year"])
    return merged


@timer
def _handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Handles missing values in (future) float columns and test bowl tracks."""
    df = df.copy()

    for col in FLOAT_COLS:
        missing = (df[col] == "-") | (df[col] == "")
        df.loc[missing, col] = np.nan

    for col in df.columns:
        if col.startswith("Test"):
            mask = df[col] == ""
            df.loc[mask, col] = np.nan

    return df


@timer
def _convert_col_types(df: pd.DataFrame) -> pd.DataFrame:
    """Converts all non-tracktime columns to correct dtypes."""
    df = df.copy()

    df = _convert_cols(df, INT_COLS, int)
    df = _convert_cols(df, FLOAT_COLS, float)
    df = _convert_cols(df, BOOL_COLS, bool)
    return df


@timer
def _convert_to_secs(df: pd.DataFrame) -> pd.DataFrame:
    """Converts all times (MM:SS.dd) to seconds."""
    df = df.copy()

    standard_tracks = _get_standard_tracks(df)

    for col in standard_tracks:
        # Get DNFs then remove them for calculations
        dnfs = df[col] == "DNF"
        df.loc[dnfs, col] = ""

        # Split
        split = df[col].str.split(":", expand=True)
        for segment in split.columns:
            split[segment] = pd.to_numeric(split[segment], errors="coerce")

        # Sum
        if split.shape[1] == 1:
            df[col] = np.nan
        else:
            split[0] = split[0] * 60
            split[2] = split[2] / 100
            df[col] = split.sum(axis=1)

        # Change 0.0 for nans, and add back inf DNFs as inf
        df.loc[df[col] == 0, col] = np.nan
        df.loc[dnfs, col] = np.inf

    return df


@timer
def _add_owned_info(df: pd.DataFrame) -> pd.DataFrame:
    """Adds all info from owned data (config.paths.OWNED_PATH)."""
    with open(OWNED_PATH, "r", encoding="utf-8") as f:
        owned_lists = json.load(f)

    df = df.copy()

    for col in TEMP_COLS:
        df[col] = 0

    # Add new columns
    df["owned"] = False
    df["owned_engine_up"] = 0
    df["owned_weight_up"] = 0
    df["owned_chassis_up"] = 0

    df_sections = []

    for i, car_list in enumerate(owned_lists.values()):
        df_sec = df.copy()
        df_sec["car_version"] = i

        df_sec = _add_owned_stats(df_sec, car_list)
        df_sec = _calc_upgrade_diffs(df_sec)
        df_sec = _remove_invalid_cars(df_sec)

        df_sections.append(df_sec)

    return pd.concat(df_sections)


@timer
def _calc_penalties(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates full penalties for each row"""
    df = df.copy()

    df = _add_rarity(df)
    df = _calc_unowned_pen(df)
    df = _calc_upgrade_pen(df)

    df["penalty"] = df["unowned_pen"] + df["upgrade_pen"]

    return df.drop(TEMP_COLS, axis=1)


@timer
def preprocess() -> pd.DataFrame:
    """The full preprocessing pipeline from raw json data to clean csv."""
    df = _merge_times_and_info()
    df = _handle_missing_values(df)
    df = _convert_col_types(df)
    df = _convert_to_secs(df)
    df = _add_owned_info(df)
    df = _calc_penalties(df)
    return df


@timer
def encode_df(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encodes all categorical columns,
    splitting up any list-like strings (e.g. "item1/item2/...").
    """
    df = df.copy()

    # One-hot encode all simple columns
    for col in SIMPLE_ENCODE_COLS:
        df[col] = df[col].astype("category")
        df = pd.get_dummies(df, columns=[col], prefix=col, dtype="int")

    # Encode tags & body
    encode_sets = {"tags": _joined_col_to_set(df["tags"]), "body": _joined_col_to_set(df["body"])}
    for cat, cat_set in encode_sets.items():
        for indiv in cat_set:
            indiv_col_str = f"{cat}_{indiv.replace(' ', '_')}"
            df[indiv_col_str] = 0
            mask = df[cat].str.contains(indiv)
            df.loc[mask, indiv_col_str] = 1

    return df
