"""Constants for challenge scraping and solving."""

CHALLENGE_INFO = {
    "Rogue": {
        "base": {"pref": "rogue_agents_"},
        10: {
            "sr": 10,
            "suf": "urban_pursuit_10",
            "rest": {
                "tag_Rogue_Agents": [((1, 10), 5)],
            },
        },
        14: {
            "suf": "the_double_agent_14",
            "rest": {"tag_Rogue_Agents": [((1, 10), 5)], "class_B": [((1, 10), 5)]},
        },
        18: {
            "suf": "critical_intelligence_18",
            "rest": {"tag_Crown_Pursuit": [((1, 10), 5)], "class_B": [((1, 10), 5)]},
        },
        19: {
            "suf": "rounding_them_up_19",
            "rest": {"tag_Crown_Pursuit": [((1, 10), 5)], "rq_range_50_150": [((1, 10), 5)]},
        },
        20: {
            "suf": "costly_vindication_20",
            "rest": {
                "tag_Rogue_Agents": [((1, 10), 5)],
                "rq_range_50_150": [((1, 10), 5)],
                "prize_False": [((1, 10), 5)],
            },
        },
    },
    "Avatar": {
        "base": {"pref": "avatar_challenge_"},
        3: {
            "sr": 8,
            "suf": "porsche_3",
            "rest": {
                "country_DE": [((1, 10), 5)],
                "year_range_1910_1999": [((1, 10), 5)],
                "rq_range_40_150": [((1, 10), 5)],
                "tyres_Performance": [((1, 10), 5)],
            },
        },
        4: {
            "sr": 6,
            "suf": "volvo_4",
            "rest": {
                "country_SE": [((1, 10), 5)],
                "rq_range_40_150": [((1, 10), 5)],
            },
        },
    },
}

COPY_COLS = {
    "full_col": [
        "rq",
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
