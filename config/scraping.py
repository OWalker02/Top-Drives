"""Constants for scraping."""

CLICK_OFF_COORDS = (500, 1000)

CORE_KEYS = {
    "tas": ["rq", "make", "model", "make_model", "year", "engine_up", "weight_up", "chassis_up"],
    "info": ["rid"],
}

BASE_URL = "https://www.topdrivesrecords.com"

FILTER_STRS = {
    "index": ('crossorigin src="', False, '">', False),
    "components": ('modulepreload" crossorigin href="', False, '">', False),
    "car_info": ('[{"class":"S"', True, "}]", True),
    "track_types": ('[{"id":"drag100b","types":["00"', True, "]}]", True),
    "track_upper_codes": ("))))})},", False, "{drag100b", False),
    "track_upper_map": ("{drag100b", True, "}", True),
    "id_name_maps": ("Ib=", False, ",xb", False),
}

CAR_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.topdrivesrecords.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36 OPR/129.0.0.0"
    ),
}

CHALLENGE_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.topdrivesrecords.com",
    "Referer": "https://www.topdrivesrecords.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36 OPR/129.0.0.0"
    ),
}
