"""
Functions for updating the raw scraped JSON database with newly scraped data.
"""

import json
import os

import pandas as pd

from config.paths import RAW_SCRAPED_JSON_PATH
from config.scraping import CORE_KEYS
from src.utils.timer import timer
from src.zzz_selenium_scraping.scrapers import TDRScraper


@timer
def load_db() -> dict | None:
    """
    Loads existing raw scraped JSON from config.paths.RAW_SCRAPED_JSON_PATH, or returns empty db if
    file doesn't exist.
    """
    if os.path.isfile(RAW_SCRAPED_JSON_PATH):
        with open(RAW_SCRAPED_JSON_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
    else:
        db = None
    return db


@timer
def _merge_new_into_old(
    new_df: pd.DataFrame, old_df: pd.DataFrame, core_keys: list[str]
) -> pd.DataFrame:
    """
    Merges new scraped data into existing data on core_keys.
    New data takes priority for any conflicting columns.
    Returns old data unchanged if it is empty.
    """
    if old_df.shape[0] == 0:
        return new_df.copy()

    merged = new_df.merge(old_df, on=core_keys, how="outer", suffixes=(None, "_old"))

    conflict_cols = [c for c in merged.columns if str(c).endswith("_old")]
    for col in conflict_cols:
        original = col.replace("_old", "")
        merged[original] = merged[original].combine_first(merged[col])
        merged.drop(columns=col, inplace=True)

    return merged.drop_duplicates(ignore_index=True)


@timer
def update_db(scraper: TDRScraper) -> dict:
    """
    Merges newly scraped data from scraper into the raw JSON db and saves.
    New data takes priority over existing data for any conflicts.
    """
    db = load_db()

    if db is None:
        db = {
            "car_times_and_stats_dicts": [],
            "car_info_dicts": [],
        }

    old_tas_df = pd.DataFrame(db["car_times_and_stats_dicts"])
    old_info_df = pd.DataFrame(db["car_info_dicts"])

    new_tas_df = pd.DataFrame(scraper.car_times_and_stats_dicts)
    new_info_df = pd.DataFrame(scraper.car_info_dicts)

    merged_tas = _merge_new_into_old(new_tas_df, old_tas_df, CORE_KEYS["tas"])
    merged_info = _merge_new_into_old(new_info_df, old_info_df, CORE_KEYS["info"])

    db["car_times_and_stats_dicts"] = merged_tas.to_dict(orient="records")
    db["car_info_dicts"] = merged_info.to_dict(orient="records")

    return db
