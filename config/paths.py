"""File paths."""

from pathlib import Path

ROOT = Path(__file__).parent.parent

DATA = ROOT / "data"

OWNED_PATH = DATA / "owned_cars.json"

CACHE_DIR = DATA / "cache"

RAW_DATA_DIR = DATA / "raw"
RAW_SCRAPED_JSON_PATH = RAW_DATA_DIR / "scraped.json"
SCRAPING_PROGRESS_PATH = CACHE_DIR / "scraping_progress.json"

PROCESSED_DIR = DATA / "processed"
PREPROCESSED_PATH = PROCESSED_DIR / "preprocessed.csv"
PREPROCESSED_ENC_PATH = PROCESSED_DIR / "preprocessed_enc.csv"
