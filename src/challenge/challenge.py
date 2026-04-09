"""
Functions for preparing the challenge DataFrame and other useful functions for the ChallengeSolver.
"""

import json

import pandas as pd

from config.challenge import CHALLENGE_INFO, COLOUR_RANGES
from config.paths import CHALLENGES_DIR
from src.challenge._challenge_helpers import (
    _extract_restrictions,
    _filter_challenge_df,
    _get_copy_cols,
    _get_universal_restrictions,
    _make_restriction_col,
    _make_track_cols,
)
from src.utils.timer import timer


@timer
def load_challenge_dict(challenge_info: dict) -> dict:
    """Loads challenge_dict for specific challenge_cat & challenge_num."""
    with open(
        CHALLENGES_DIR / f"{challenge_info['name']}.json",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def get_challenge_info(challenge_cat: str, challenge_num: int) -> dict:
    """
    Extrcats and merges base information for challenge_cat with specific challenge information for
    challenge_num, from CHALLENGE_INFO.
    """
    # Base info
    base_dict = CHALLENGE_INFO[challenge_cat]["base"]
    name_pref = base_dict.get("pref", "")
    base_sr = base_dict.get("sr", 1)
    base_er = base_dict.get("er", 99)
    base_restrictions = base_dict.get("rest", {})

    # Specific challenge info
    spec_dict = CHALLENGE_INFO[challenge_cat][challenge_num]
    name_suf = spec_dict.get("suf", "")
    spec_restrictions = spec_dict.get("rest", {})

    # Combine
    challenge_info = {
        "name": name_pref + name_suf,
        "start_round": spec_dict.get("sr", base_sr),
        "end_round": spec_dict.get("er", base_er),
        "challenge_restrictions": base_restrictions | spec_restrictions,
    }
    return challenge_info


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
    # challenge_setup = get_challenge_setup(encoded_df, challenge_cat, challenge_num, only_owned)
    challenge_info = get_challenge_info(challenge_cat, challenge_num)
    challenge_dict = load_challenge_dict(challenge_info)

    # Set up df
    copy_cols = _get_copy_cols(encoded_df)
    challenge_df = encoded_df[copy_cols].copy()

    # Add track columns
    track_cols = _make_track_cols(encoded_df, challenge_dict, challenge_info)
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
    # Filter
    challenge_df = _filter_challenge_df(
        challenge_df,
        encoded_df,
        list(track_cols.keys()),
        all_restrictions,
        universal_restrictions,
        max_penalty,
        only_owned,
    )

    return challenge_df


def get_rq_colour(rq: int) -> str:
    """Gets the 256-colour mode for an RQ."""
    return next(c for low, high, c in COLOUR_RANGES if low <= rq <= high)


def load_filtered_challenge_dict(challenge_info: dict):
    """Filters the challenge_dict to within the desired start and end round in the setup dict."""
    challenge_dict = load_challenge_dict(challenge_info)
    return {
        k: v
        for k, v in challenge_dict.items()
        if challenge_info["start_round"] <= int(k) <= challenge_info["end_round"]
    }
