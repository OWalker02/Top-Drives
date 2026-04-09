"""Constants for preprocessing."""

NON_TRACK_COLS = [
    "rq",
    "make",
    "model",
    "rid",
    "year",
    "top_speed",
    "zero_sixty",
    "handling",
    "engine_up",
    "weight_up",
    "chassis_up",
    "rid",
    "country",
    "tyres",
    "drive",
    "prize",
    "tags",
    "abs",
    "tcs",
    "clearance",
    "mra",
    "weight",
    "fuel",
    "seats",
    "engine_pos",
    "body",
    "brakes",
]

INT_COLS = ["rq", "year", "engine_up", "weight_up", "chassis_up", "weight", "seats"]

FLOAT_COLS = ["top_speed", "zero_sixty", "handling", "mra"]

BOOL_COLS = ["prize", "abs", "tcs"]

REDUCE_PENALTY_TAGS = ["prize", "tag_year_of_the_Horsepower"]

PENALTIES = {
    "unowned": {"S": 100000, "A": 20000, "B": 3000, "C": 750, "D": 300, "E": 100, "F": 150},
    "upgrade": {"S": 10000, "A": 300, "B": 60, "C": 20, "D": 6, "E": 2, "F": 4},
}

TEMP_COLS = ["engine_diff", "weight_diff", "chassis_diff", "ups_left"]

SIMPLE_ENCODE_COLS = [
    "class",
    "country",
    "tyres",
    "drive",
    "clearance",
    "fuel",
    "seats",
    "engine",
    "brake",
    "brand",
]
