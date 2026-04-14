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
        8: {
            "suf": "one_against_many_8",
            "rest": {"tag_Rogue_Agents": [((1, 10), 5)], "drive_FWD/drive_4WD": [((1, 10), 5)]},
        },
        9: {
            "sr": 10,
            "suf": "the_system_scatters_9",
            "rest": {
                "tag_Rogue_Agents": [((1, 10), 5)],
                "tyres_Performance/tyres_Slick": [((1, 10), 5)],
            },
        },
        10: {
            "sr": 10,
            "suf": "urban_pursuit_10",
            "rest": {
                "tag_Rogue_Agents": [((1, 10), 5)],
            },
        },
        11: {
            "suf": "off_the_beaten_path_11",
            "rest": {"tag_Rogue_Agents": [((1, 10), 5)], "class_F": [((1, 10), 5)]},
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
    }
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
