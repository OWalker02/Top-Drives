# TDR — Top Drives Records Toolkit

A Python toolkit for scraping, processing, and solving optimisation problems for the [Top Drives](https://www.topdrivesrecords.com/) mobile car game. Built as a portfolio project combining web scraping, data engineering, and combinatorial optimisation.

---

## What it does

Top Drives is a card-collecting racing game where players build a garage of cars and compete in challenges. Each challenge consists of multiple rounds, each with 5 tracks and an RQ (rating) limit. The goal is to assign the right car to each track to score 250+ points per round, while minimising the cost of using cars you don't own or haven't upgraded.

This project:

- **Scrapes** car stats and track times from topdrivesrecords.com using Selenium
- **Preprocesses** raw scraped data into a clean, analysis-ready DataFrame
- **Scrapes challenge data** (tracks, RQ limits, restrictions) for a given challenge
- **Solves** the car assignment problem using linear programming (PuLP), finding the optimal lineup with minimum penalty

---

## Project structure

``` text
TDR/
├── config/ . . . . . . . . . . . . . # Configuration: paths, constants, challenge definitions
│   ├── challenge.py
│   ├── constants.py
│   ├── logging.py
│   ├── paths.py
│   ├── preprocessing.py
│   ├── scraping.py
│   ├── update_ownership.py
│   └── xpaths.py
│
|
|
├── data/ . . . . . . . . . . . . . . # All data files, jsons/csvs
│   ├── cache/                        # Scraping progress json (gitignored)
│   ├── challenges/                   # Scraped challenge JSON files (gitignored)
│   ├── misc/                         # Static reference data (e.g. track_uppers.json) (not
|   |                                 # gitignored)
│   ├── ownership/                    # Json files from intercepted http requests (one from the
|   |                                 # game, one from TDR), and one to use to add ownership info
|   |                                 # to data (gitignored except owned_cars.json for example on
|   |                                 # how the project runs)
│   ├── processed/                    # Preprocessed csv files (gitignored)
│   └── raw/                          # Raw scraped JSON (gitignored)
│
|
|
├── notebooks/. . . . . . . . . . . . # Jupyter notebooks (runners only, logic lives in src/)
│   ├── car_scraping.ipynb            # Scrapes car data (info + times) on TDR
│   ├── challenge_scraping.ipynb      # Scrapes information on a challenge (tracks + times) using
|   |                                 # restrictions from config/challenge/CHALLENGE_INFO
│   ├── challenge.ipynb               # Solves a challenge (provided the challenge data has been
|   |                                 # scraped)
│   ├── preprocess.ipynb              # Takes raw scraped json data and produces a preprocessed csv
|   |                                 # with ownership info & penalties, and a one-hot encoded
|   |                                 # version of this csv too
│   └── update_ownership.ipynb        # Takes json files from data/ownership to create lists of
|                                     # owned cars
│
|
|
├── scripts/. . . . . . . . . . . . . # Will contain scripts to do similar processes as the
|                                     # notebooks
|
|
|
├── src/. . . . . . . . . . . . . . . # All the functions / classes to use across the project
│   ├── challenge/
│   │   ├── _challenge_helpers.py
│   │   ├── challenge.py
│   │   └── solver.py                 # ChallengeSolver class
|   |
│   ├── preprocessing/
│   │   |── _preprocessing_helpers.py
│   │   └── preprocessing.py
|   |
│   ├── scraping/
│   │   |── _scraping_helpers.py
│   │   ├── scrapers.py               # TDRScraper & ChallengeScraper classes
│   │   └── scraping.py
│   │
│   └── utils/
│       └── timer.py                  # @timer decorator
│
|
|
├── .pre-commit-config.yaml
├── pyproject.toml
└── README.md
```

---

## Setup

**Requirements:** Python 3.12+, Firefox (for Selenium scraping)

```bash
# Clone the repo
git clone https://github.com/yourusername/TDR.git
cd TDR

# Install with pip
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

---

## Usage

The project runs as three sequential stages, each with a corresponding notebook in `notebooks/`.

1. **`car_scraping.ipynb`** — scrapes car stats and track times from topdrivesrecords.com
2. **`challenge_scraping.ipynb`** - scrapes challenge data (must have info in config/challenge/CHALLENGE_INFO to work)
3. **`preprocess.ipynb`** — cleans and encodes the raw scraped data
4. **`challenge.ipynb`** — solves the challenge passed, and prints results

Run them in order. Each notebook is a thin runner — all logic lives in `src/`.

---

## How the solver works

The car assignment problem is formulated as an integer linear programme using [PuLP](https://coin-or.github.io/PuLP/):

### Variables

- `x[car, track]` — binary, 1 if car is assigned to track
- `y[car]` — binary, 1 if car is used anywhere in the challenge

### Objective

Minimise total penalty of cars used (unowned or not fully upgraded cars carry a penalty based on rarity).

### Constraints

1. Each track has exactly one car assigned
2. Each car can be used at most once per round
3. Each round must score ≥ 250 points
4. Total RQ per round must not exceed the round's RQ limit
5. Per-round restrictions must be met (e.g. minimum number of a certain tag/rarity)
6. Each physical car (by ID) can only be used once across the challenge

---

## Key dependencies

| Package | Purpose |
| --- | --- |
| `selenium` | Browser automation for scraping |
| `beautifulsoup4` | HTML parsing for challenge scraper |
| `pandas` | Data processing |
| `numpy` | Numerical operations |
| `pulp` | Linear programming solver |
| `pyautogui` | Mouse control during scraping |
| `tqdm` | Progress bars |

---

## Data

Raw and processed data files are gitignored as they are reproducible by running the pipeline. To generate from scratch:

1. Run `notebooks/scraping.ipynb` to collect car data
2. Run `notebooks/preprocess.ipynb` to process it
3. Run `notebooks/challenge.ipynb` to solve a specific challenge

The only committed data files are `data/misc/track_uppers.json` which contains the upper points bounds per track used in the points calculation formula, and `data/ownership/owned_cars.json` which contains my owned cars list (for reference and test running) and should be replaced with the user's lists through `notebooks/update_ownership.ipynb`.
