"""File paths."""

from pathlib import Path

ROOT = Path(__file__).parent.parent

DATA = ROOT / "data"

OWNED_DIR = DATA / "ownership"
OWNED_PATH = OWNED_DIR / "owned_cars.json"
TD_JSON_PATH = OWNED_DIR / "garage_td.json"
TDR_JSON_PATH = OWNED_DIR / "garage_td_records.json"

CACHE_DIR = DATA / "cache"
SCRAPING_PROGRESS_PATH = CACHE_DIR / "scraping_progress.json"

RAW_DATA_DIR = DATA / "raw"
RAW_SCRAPED_JSON_PATH = RAW_DATA_DIR / "scraped.json"
RAW_TAS_PATH = RAW_DATA_DIR / "tas.json"
RAW_CI_PATH = RAW_DATA_DIR / "ci.json"

PROCESSED_DIR = DATA / "processed"
PREPROCESSED_PATH = PROCESSED_DIR / "preprocessed.csv"
PREPROCESSED_ENC_PATH = PROCESSED_DIR / "preprocessed_enc.csv"

ROOT_CHALLENGES_DIR = DATA / "challenges"
CHALLENGES_DIR = ROOT_CHALLENGES_DIR / "challenge_dicts"
SOLUTIONS_DIR = ROOT_CHALLENGES_DIR / "solutions"

TRACKS_DIR = DATA / "tracks"
TRACK_UPPERS_PATH = TRACKS_DIR / "track_uppers.json"
TRACKSET_PATH = TRACKS_DIR / "trackset.json"

TDR_DIR = DATA / "tdr"
INDEX_FULL_PATH = TDR_DIR / "index.txt"
COMPONENTS_FULL_PATH = TDR_DIR / "components.txt"
CAR_INFO_JSON = TDR_DIR / "car_info.json"
