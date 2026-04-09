"""Constants for challenge scraping and solving."""

CHALLENGE_INFO = {
    "Rogue": {
        "base": {"pref": "rogue_agents_"},
        6: {
            "sr": 1,
            "suf": "following_the_breadcrumbs_6",
            "rest": {
                "tag_Rogue_Agents": [((1, 10), 5)],
                "tyres_Standard/tyres_All-surface/tyres_Off-road": [((1, 10), 5)],
            },
        },
        7: {
            "suf": "first_contact_7",
        },
    }
}
"""
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
    "Rogue": {
        "base": {"sr": 1, "er": 10, "useful": lambda df: df["tag_Ministry_of_Racing"]},
        6: {
            "useful": lambda df: (
                df["tyres_Standard"] | df["tyres_All-surface"] | df["tyres_Off-road"]
            )
        },
    },
}
"""

COPY_COLS = {
    "full_col": [
        "rq",
        "brand",
        "rid",
        "year",
        "engine_up",
        "weight_up",
        "chassis_up",
        "penalty",
        "car_version",
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
        "engine",
        "brake",
        "tag",
        "body",
        "class",
        "brand",
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
    "RQ",
    "Rid",
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
