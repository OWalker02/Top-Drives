"""Xpaths for Selenium."""

_BASE = "/html/body/div/div[2]"

_MENU_BASE = _BASE + "/div[8]/div[2]/div/div"
MENU = {
    "open_menu": _BASE + "/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/button[1]",
    "clear_cars": _MENU_BASE + "/div[1]/div[1]/div/button[2]",
    "clear_tracks": _MENU_BASE + "/div[1]/div[1]/div/button[1]",
    "layout": _MENU_BASE + "/div[2]/div[1]/div[2]/button[3]",
}

TRACKS = {
    "add_tracks": _BASE + "/div[1]/div[1]/div[2]/div/div[2]/button",
    "tracks_box": "/html/body/div/div[5]/div[2]/div/div/div",
}

_SEARCH_BASE = _BASE + "/div[3]/div[2]/div/div"
SEARCH = {
    "car_search": _BASE + "/div[1]/div[2]/div[2]/div[1]/div/button",
    "open_filters": _SEARCH_BASE + "/div[1]/button",
    "clear_filters": _SEARCH_BASE + "/div[2]/div/div[1]/div/button",
    "filters_done": _SEARCH_BASE + "/div[1]/button",
    "car_count": _SEARCH_BASE + "/div[1]/button/div[2]",
    "show_more": _SEARCH_BASE + "/div[2]/div[2]/button",
    "search_results": _SEARCH_BASE + "/div[2]",
}

_FILTERS_BASE = _BASE + "/div[3]/div[2]/div/div/div[2]/div"
FILTERS = {
    "clear": _FILTERS_BASE + "/div[1]/div/button",
    "rarities": _FILTERS_BASE + "/div[2]",
    "tyres": _FILTERS_BASE + "/div[5]/div[1]",
    "drives": _FILTERS_BASE + "/div[5]/div[2]",
    "clearances": _FILTERS_BASE + "/div[5]/div[3]",
    "countries": _FILTERS_BASE + "/div[9]",
    "prize": _FILTERS_BASE + "/div[10]",
    "bodies": _FILTERS_BASE + "/div[11]",
    "fuels": _FILTERS_BASE + "/div[12]",
    "engine_pos": _FILTERS_BASE + "/div[13]/div[1]",
    "tags": [
        _FILTERS_BASE + "/div[15]",
        _FILTERS_BASE + "/div[16]",
        _FILTERS_BASE + "/div[17]",
        _FILTERS_BASE + "/div[18]",
    ],
    "makes": _FILTERS_BASE + "/div[20]",
}
FILTERS = {k: v if isinstance(v, list) else [v] for k, v in FILTERS.items()}

_TUNES_BASE = _BASE + "/div[1]/div[2]/div[2]"
TUNES = {
    "car_list": _TUNES_BASE,
    "first_tune_suf": "./div[2]/div/div[1]/div/div/button[1]",
    "settings_rep": _TUNES_BASE + "div[REPLACE]/div[2]/div/div[1]/div/div[2]/button",
    "tune_rep": _BASE + "/div[4]/div[2]/div/div/div/div[2]/button[REPLACE]",
    "car_info": _BASE + "/div[4]/div[2]/div/div/div[2]",
}
