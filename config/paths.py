"""File paths."""

from pathlib import Path

ROOT = Path(__file__).parent.parent

DATA = ROOT / "data"

OWNED_DIR = DATA / "ownership"
OWNED_PATH = OWNED_DIR / "owned_cars.json"
TD_JSON_PATH = OWNED_DIR / "garage_td.json"
TDR_JSON_PATH = OWNED_DIR / "garage_td_records.json"

CACHE_DIR = DATA / "cache"

RAW_DATA_DIR = DATA / "raw"
RAW_SCRAPED_JSON_PATH = RAW_DATA_DIR / "scraped.json"
SCRAPING_PROGRESS_PATH = CACHE_DIR / "scraping_progress.json"

PROCESSED_DIR = DATA / "processed"
PREPROCESSED_PATH = PROCESSED_DIR / "preprocessed.csv"
PREPROCESSED_ENC_PATH = PROCESSED_DIR / "preprocessed_enc.csv"

CHALLENGES_DIR = DATA / "challenges"

MISC_DIR = DATA / "misc"
TRACK_UPPERS_PATH = MISC_DIR / "track_uppers.json"
