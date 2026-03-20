"""Constants for challenge scraping and solving."""

CHALLENGE_INFO = {
    "Skyline": {
        "base": ["Skyline Nismo ", 1, 10, {"tags_Japan_Pro_Tour": [((1, 10), 5)]}],
        4: [
            "4",
            8,
            0,
            {
                "rarity_D": [((1, 1), 1), ((2, 2), 2), ((3, 3), 3)],
                "rarity_C": [((4, 4), 2), ((5, 5), 3), ((6, 6), 4), ((7, 7), 5)],
                "rarity_B": [((8, 8), 3), ((9, 9), 4), ((10, 10), 5)],
                "year_range_2010_2030": [((1, 10), 5)],
            },
        ],
        6: [
            "6",
            0,
            0,
            {
                "rarity_D": [((1, 1), 3), ((2, 2), 4), ((3, 3), 5)],
                "rarity_C": [((4, 4), 2), ((5, 5), 3), ((6, 6), 4), ((7, 7), 5)],
                "rarity_B": [((8, 8), 1), ((9, 9), 2), ((10, 10), 3)],
                "year_range_1980_1999": [((1, 10), 5)],
            },
        ],
    },
    "YotH": {
        "base": ["Horsepower: ", 1, 12, {"tags_Year_of_the_Horsepower": [((1, 12), 5)]}],
        4: ["", 0, 0, {}],
        5: ["Mounted", 0, 0, {}],
        6: [
            "Uphill",
            0,
            0,
            {
                "rarity_F": [((1, 6), 1)],
                "rarity_E": [((1, 12), 1)],
                "rarity_D": [((1, 12), 1)],
                "rarity_C": [((1, 12), 1)],
                "rarity_B": [((1, 12), 1)],
                "rarity_A": [((7, 12), 1)],
            },
        ],
        7: ["", 0, 0, {"RQ_range_10_": [((1, 6), 5)], "rarity_F": [((1, 12), 5)]}],
        8: ["", 0, 0, {"RQ_range_20_25": [((1, 6), 5)], "rarity_E": [((1, 12), 5)]}],
        9: ["", 0, 0, {"RQ_range_30_34": [((1, 6), 5)], "rarity_D": [((1, 12), 5)]}],
        10: ["", 0, 0, {"RQ_range_40_": [((1, 6), 5)], "rarity_C": [((1, 12), 5)]}],
        11: ["Wild", 0, 0, {"RQ_range_50_": [((1, 6), 5)], "rarity_B": [((1, 12), 5)]}],
        12: ["Bucking", 0, 0, {"RQ_range_65_115": [((1, 12), 5)]}],
    },
    "Rogue": {
        "base": ["Rogue Skies: ", 1, 20, {"prize_No": [((1, 20), 5)]}],
        1: [
            "Flash",
            0,
            0,
            {
                "make_BMW/make_Mitsubishi/make_Lincoln": [((1, 20), 5)],
                "body_Saloon": [((1, 20), 5)],
                "tyres_Standard": [((1, 20), 5)],
            },
        ],
        2: ["Storm", 0, 0, {"country_GB/country_IT": [((1, 20), 5)], "body_SUV": [((1, 20), 5)]}],
        3: ["Eye", 0, 0, {"body_Roadster": [((1, 20), 5)], "year_range_2007_2014": [((1, 20), 5)]}],
    },
}

CHALLENGE_SETUP = {
    "Skyline": {
        "base": {"sr": 1, "er": 10, "useful": lambda df: df["tags_Japan_Pro_Tour"]},
        4: {
            "sr": 8,
            "er": 10,
            "useful": lambda df: (df["year"] >= 2010) & (df["rq"].between(50, 64)),
        },
        7: {},
    },
    "Touma": {
        "base": {"sr": 1, "er": 12, "useful": lambda df: df["tags_Touma's_Collection_2"]},
        4: {},
        5: {},
        6: {},
        7: {"useful": lambda df: df["rarity_F"]},
        8: {"useful": lambda df: df["rarity_E"]},
        9: {"useful": lambda df: df["rarity_D"]},
        10: {"useful": lambda df: df["rarity_C"]},
        11: {"useful": lambda df: df["rarity_B"]},
        12: {"useful": lambda df: df["rq"].between(65, 115)},
    },
}


CONDITION_MAP = {
    "00": "Dry",
    "01": "Wet",
    "10": "Dirt",
    "20": "Gravel",
    "50": "Sand",
    "60": "Snow",
    "11": "Dirt Wet",
    "30": "Ice",
    "41": "Aspht Dirt Wet",
    "c0": "Aspht Sand",
    "40": "Aspht Dirt",
    "i0": "Aspht",
    "e0": "Sand Dirt",
    "f0": "Aspht Grass Dirt",
    "c1": "Aspht Sand Wet",
    "70": "Grass",
    "b0": "Aspht Gravel",
    "d0": "Aspht Snow",
    "71": "Grass Wet",
    "h1": "Snow Dirt Wet",
    "51": "Sand Wet",
    "m0": "Aspht Dirt",
    "k0": "Dirt",
    "g0": "Ice Snow",
}

COPY_COLS = {
    "full_col": [
        "rq",
        "make",
        "model",
        "make_model",
        "year",
        "engine_up",
        "weight_up",
        "chassis_up",
        "penalty",
        "car_version",
        "rid",
        "owned",
    ],
    "col_prefix": [
        "prize",
        "country",
        "tyres",
        "drive",
        "abs",
        "tcs",
        "clearance",
        "fuel",
        "seats",
        "engine_pos",
        "brakes",
        "tag",
        "body",
        "rarity",
        "make",
    ],
}

COLOUR_RANGES = [
    (0, 19, "240"),
    (20, 29, "34"),
    (30, 39, "27"),
    (40, 49, "226"),
    (50, 64, "196"),
    (65, 79, "129"),
    (80, 150, "214"),
]

PRINT_COLS = [
    "Index",
    "Year",
    "RQ",
    "Make",
    "Model",
    "Track",
    "Challenge Time",
    "Track Time",
    "Points",
    "Engine Up",
    "Weight Up",
    "Chassis Up",
    "Penalty",
    "Version",
]
