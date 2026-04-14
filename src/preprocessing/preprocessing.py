"""
Functions for preprocessing from raw scraped json data to a preprocessed csv file, and/or a one-hot
encoded version.
"""

import json

import numpy as np
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer

from config.paths import OWNED_PATH, RAW_CI_PATH, RAW_TAS_PATH
from config.preprocessing import (
    FLOAT_COLS,
    INT_COLS,
    SIMPLE_ENCODE_COLS,
    TEMP_COLS,
)
from src.preprocessing._preprocessing_helpers import (
    _add_owned_stats,
    _add_rarity,
    _calc_rq_pen,
    _calc_unowned_pen,
    _calc_upgrade_diffs,
    _calc_upgrade_pen,
    _convert_cols,
    _get_tracks,
    _remove_invalid_cars,
    _time_str_to_secs,
)
from src.utils.timer import timer


@timer
def _merge_times_and_info() -> pd.DataFrame:
    """
    Merges times/stats and info lists (from config.paths.RAW_SCRAPED_JSON_PATH) of dicts into a
    single DataFrame.
    Joins on shared core keys.
    """
    with open(RAW_TAS_PATH, "r", encoding="utf-8") as f:
        raw_tas = json.load(f)
    tas_only = [d for v in raw_tas.values() for d in v["dicts"]]

    with open(RAW_CI_PATH, "r", encoding="utf-8") as f:
        raw_ci = json.load(f)

    # Convert to DFs
    tas_df = pd.DataFrame(tas_only)
    info_df = pd.DataFrame(raw_ci)

    # Merge
    merged = tas_df.merge(info_df, how="outer", on="rid")
    return merged


@timer
def _handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Handles missing values in (future) float columns and test bowl tracks."""
    df = df.copy()

    _, test_tracks = _get_tracks(df)

    for col in FLOAT_COLS:
        df[col] = df[col].replace(["-", ""], np.nan)

    for col in test_tracks:
        df[col] = df[col].replace({"DNF": 0, "": np.nan}).astype(float)

    return df


@timer
def _convert_col_types(df: pd.DataFrame) -> pd.DataFrame:
    """Converts all non-tracktime columns to correct dtypes."""
    df = df.copy()

    df = _convert_cols(df, INT_COLS, int)
    df = _convert_cols(df, FLOAT_COLS, float)
    # df = _convert_cols(df, BOOL_COLS, bool)

    return df


@timer
def _convert_to_secs(df: pd.DataFrame) -> pd.DataFrame:
    """Converts all times (MM:SS.dd) to seconds."""
    df = df.copy()
    standard_tracks, _ = _get_tracks(df)

    for col in standard_tracks:
        df[col] = df[col].apply(_time_str_to_secs)
        df.loc[df[col] == 0, col] = np.nan

    return df


@timer
def _add_owned_info(df: pd.DataFrame) -> pd.DataFrame:
    """Adds all info from owned data (config.paths.OWNED_PATH)."""
    with open(OWNED_PATH, "r", encoding="utf-8") as f:
        owned_lists = json.load(f)

    df = df.copy()

    for col in TEMP_COLS:
        df[col] = 0

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
    unowned_pen = _calc_unowned_pen(df)
    upgrade_pen = _calc_upgrade_pen(df)
    rq_pen = _calc_rq_pen(df)

    # Add all unowned and upgrade penalties, then add rq penalty to any non-zero penalties
    df["penalty"] = unowned_pen + upgrade_pen
    non_zero = df["penalty"] > 0
    df.loc[non_zero, "penalty"] += rq_pen[non_zero]

    return df.drop(TEMP_COLS, axis=1)


@timer
def _add_uid(df: pd.DataFrame) -> pd.DataFrame:
    """Updates rids with the car versions."""
    df = df.copy()

    uids = (
        df["rid"]
        + "_"
        + df["car_version"].astype(str)
        + "_"
        + df["engine_up"].astype(str)
        + df["weight_up"].astype(str)
        + df["chassis_up"].astype(str)
    )
    df["uid"] = uids

    return df


@timer
def preprocess(test_mode: bool = False) -> pd.DataFrame:
    """
    The full preprocessing pipeline from raw json data to clean csv. test_mode only runs the first
    1000 rows of the merged df.
    """
    df = _merge_times_and_info()
    df = df[~df["engine_up"].isna()]
    if test_mode:
        df = pd.concat([df.head(1000), df[df["make_model"] == "Nissan Cima VIP (Y51)"]])
    df = _handle_missing_values(df)
    df = _convert_col_types(df)
    # df = _convert_to_secs(df)
    df = _add_owned_info(df)
    df = _calc_penalties(df)
    df = _add_uid(df)
    return df


@timer
def encode_df(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encodes all categorical columns,
    splitting up any list-like strings (e.g. "item1/item2/...").
    """
    df = df.copy()

    # One-hot encode all simple columns
    # Get make col to add back in
    brand = df["brand"]
    for col in SIMPLE_ENCODE_COLS:
        df[col] = df[col].astype("category")
        df = pd.get_dummies(df, columns=[col], prefix=col, dtype="int")
    df["brand"] = brand

    # Encode tags & body
    for list_col in [{"col": "tags", "pref": "tag"}, {"col": "bodyTypes", "pref": "body"}]:
        mlb = MultiLabelBinarizer()
        encoded_category_df = pd.DataFrame(
            mlb.fit_transform(df[list_col["col"]]),
            columns=[f"{list_col['pref']}_{c.replace(' ', '_')}" for c in mlb.classes_],
            index=df.index,
        )
        df = pd.concat([df, encoded_category_df], axis=1)
    return df
