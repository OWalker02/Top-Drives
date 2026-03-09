"""
Selenium-based scraper for topdrivesrecords.com.

Handles browser setup, track selection, car filtering, and time/stats collection.
Run via TDRScraper.scrape() after instantiation.
"""

import pickle
import time
from typing import Dict, List, Tuple

import pyautogui
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from config.constants import RARITIES
from config.paths import SCRAPING_PROGRESS_PATH
from config.scraping import CONDITION_MAP
from config.xpaths import FILTERS, MENU, SEARCH, TRACKS, TUNES
from src.utils.timer import timer


class TDRScraper:
    """
    Scraper for topdrivesrecords.com.

    Collects car times, stats, and info across all rarities and tracks.
    Instantiate with a WebDriver and screen coordinates, then call scrape().
    """

    def __init__(
        self,
        driver: WebDriver,
        click_off_coords: Tuple[int, int],
        filters: Dict | None = None,
        scrape_new: bool = True,
        test_mode: bool = False,
    ):
        """
        Args:
            driver: Selenium WebDriver instance.
            click_off_coords: (x, y) screen coordinates to click off open menus.
            filters: Optional dict of filter_type -> list of targets. May include 'rarities' key to
                     restrict which rarities are scraped.
            scrape_new: If False, loads existing progress from SCRAPING_PROGRESS_PATH before
                        scraping.
            test_mode: If True, only scrapes first track and first group per rarity.
        """
        self.driver = driver
        self.off_x, self.off_y = click_off_coords
        filters = dict(filters) if filters else {}
        self.scrape_rarities = filters.pop("rarities", RARITIES)
        self.filters = filters
        self.scrape_new = scrape_new
        self.test_mode = test_mode
        self.trackset: List[str] = []
        self.car_times_and_stats_dicts: List[Dict] = []
        self.car_info_dicts: List[Dict] = []
        self.scraped_groups: Dict[str, List[Tuple]] = {r: [] for r in RARITIES}
        self.completed_rarities: List[str] = []

    def load_progress(self) -> None:
        """Loads scraping progress from SCRAPING_PROGRESS_PATH into instance state."""
        with open(SCRAPING_PROGRESS_PATH, "rb") as f:
            progress = pickle.load(f)
        self.car_times_and_stats_dicts = progress["car_times_and_stats_dicts"]
        self.car_info_dicts = progress["car_info_dicts"]
        self.scraped_groups = progress["scraped_groups"]
        self.completed_rarities = progress["completed_rarities"]

    def _open_tdr(self) -> None:
        """Opens TDR site and hides horizontal scrollbar."""
        self.driver.maximize_window()
        self.driver.execute_script("document.body.style.overflowX = 'hidden';")
        self.driver.get("https://www.topdrivesrecords.com/")

    def _click(self, element: WebElement, delay: float = 0, wiggle_on_fail: bool = False) -> None:
        """
        Attempts to click an element up to 3 times.
        Pauses between retries based on error type, or wiggles the page if wiggle_on_fail=True.
        Raises the last exception if all attempts fail.
        """
        last_exception = None
        for _ in range(3):
            try:
                element.click()
                if delay:
                    time.sleep(delay)
                return
            except Exception as e:
                if wiggle_on_fail:
                    self._click_off()
                    self.driver.execute_script("window.scrollBy(0, 1)")
                    self.driver.execute_script("window.scrollBy(0, -1);")
                else:
                    if "BaseDialog_Back" in str(e):
                        last_exception = e
                        time.sleep(0.1)
                    elif "ElementClickInterceptedException" in str(e):
                        last_exception = e
                        time.sleep(1)
                    else:
                        raise e
        raise last_exception  # type: ignore

    def _click_by_xpath(self, xpath: str, delay: float = 0, wiggle_on_fail: bool = False) -> None:
        """Finds an element by xpath and clicks it."""
        element = self.driver.find_element(By.XPATH, xpath)
        self._click(element, delay, wiggle_on_fail)

    def _click_off(self, delay: float = 0) -> None:
        """Clicks coordinates to close any open menus."""
        pyautogui.click(self.off_x, self.off_y)
        if delay:
            time.sleep(delay)

    def _initial_menu_setup(self) -> None:
        """Clears cars, tracks, and sets layout via the menu."""
        self._click_by_xpath(MENU["open_menu"])
        self._click_by_xpath(MENU["clear_cars"])
        self._click_by_xpath(MENU["clear_tracks"])
        self._click_by_xpath(MENU["layout"])
        self._click_off()

    def _get_track_divs(self) -> List[WebElement]:
        """Returns all track row divs, excluding the search box."""
        tracks_box = self.driver.find_element(By.XPATH, TRACKS["tracks_box"])
        divs = tracks_box.find_elements(By.XPATH, "./div")
        return [d for d in divs if d.get_attribute("class") != "Track_SearchBox"]

    def _get_other_conditions(self, track_div: WebElement) -> str:
        """Returns condition suffix string ' (C)', ' (R)', or '' for a track div."""
        i_elements = track_div.find_elements(By.TAG_NAME, "i")
        if i_elements:
            i_class = i_elements[0].get_attribute("class")
            if i_class == "clearance":
                return " (C)"
            elif i_class == "roll":
                return " (R)"
        return ""

    def _get_names_and_click(self, track_div: WebElement) -> List[str]:
        """
        Clicks all condition buttons for a track and returns their formatted names.
        Returns empty list if the div is dynamic or a search box.
        """
        div_1_class = track_div.find_element(By.XPATH, "./div[1]").get_attribute("class")
        if div_1_class in ["Main_CustomTrackLeftDynamic", "Track_SearchBox"]:
            return []

        track_name = track_div.find_element(By.XPATH, "./div[1]/div").text
        track_conditions = self._get_other_conditions(track_div)
        button_container_div = track_div.find_element(By.XPATH, "./div[2]/div")
        button_divs = button_container_div.find_elements(By.XPATH, "./div")

        track_names = []
        for b_div in button_divs:
            self._click(b_div)
            condition = b_div.get_attribute("class").split(" ")[2]  # type: ignore
            track_names.append(f"{track_name}{track_conditions} / {CONDITION_MAP[condition]}")

        return track_names

    @timer
    def _set_all_tracks(self) -> None:
        """Selects all tracks on the site and populates self.trackset."""
        self._click_by_xpath(TRACKS["add_tracks"], 0.1)
        for track_div in self._get_track_divs():
            self.trackset.extend(self._get_names_and_click(track_div))
            if self.test_mode:
                break
        self._click_off()

    @timer
    def setup_page(self) -> None:
        """
        Opens TDR, runs initial menu setup, and sets all tracks.
        Loads progress if scrape_new=False.
        """
        if not self.scrape_new:
            self.load_progress()
        self._open_tdr()
        self._initial_menu_setup()
        time.sleep(0.1)
        self._set_all_tracks()
        time.sleep(0.1)

    def _open_car_search(self) -> None:
        """Opens the car search panel."""
        self._click_by_xpath(SEARCH["car_search"], wiggle_on_fail=True)

    def _clear_filters(self) -> None:
        """Clears all active filters on the filters page."""
        self._click_by_xpath(FILTERS["clear"][0])

    def _select_rarity(self, r: int, delay: float = 0) -> None:
        """Selects a rarity filter button by index into RARITIES."""
        rarity_xpath = FILTERS["rarities"][0] + f"/button[{7 - r}]"
        self._click_by_xpath(rarity_xpath, delay)

    def _select_filter(self, container_xpath_list: List[str], target_list: List[str]) -> None:
        """Clicks all filter buttons whose label text matches any item in target_list."""
        for container_xpath in container_xpath_list:
            container = self.driver.find_element(By.XPATH, container_xpath)
            for button in container.find_elements(By.XPATH, ".//button"):
                if button.find_element(By.TAG_NAME, "span").text in target_list:
                    self._click(button)

    @timer
    def _add_filters(self, r: int) -> None:
        """Opens filters, applies self.filters and selects rarity r, then closes."""
        self._click_by_xpath(SEARCH["open_filters"])
        self._clear_filters()
        for filter_type, filter_targets in self.filters.items():
            self._select_filter(FILTERS[filter_type], filter_targets)
        self._select_rarity(r, 0.5)
        time.sleep(0.1)
        self._click_by_xpath(SEARCH["filters_done"], 0.5)

    def _get_car_count(self) -> int:
        """Returns number of cars matching current filter selection."""
        car_count_el = self.driver.find_elements(By.XPATH, SEARCH["car_count"])
        return int(car_count_el[0].text[1:-1]) if car_count_el else 0

    def _split_into_groups(self, car_count: int) -> List[Tuple[int, int]]:
        """
        Splits car_count into groups of 7, using 8 where needed to avoid remainders.
        Falls back to variable-size final group if unsolvable.
        """
        groups = []
        if car_count % 7 == 0:
            for i in range(0, car_count, 7):
                groups.append((i, i + 7))
        else:
            solved = False
            max_eights = car_count // 8  # Check the max number of groups size 8
            # Check all combos of groups of size 7 and 8
            for num_add_one in range(1, max_eights + 1):
                # If using this combo works, make it
                if (car_count - num_add_one * 8) % 7 == 0:
                    for i in range(0, car_count - num_add_one * 8, 7):
                        groups.append((i, i + 7))
                    for j in range(car_count - num_add_one * 8, car_count, 8):
                        groups.append((j, j + 8))
                    solved = True
                    break
            if not solved:
                for i in range(0, car_count, 7):
                    groups.append((i, min(i + 7, car_count)))
        return groups

    def _show_all_cars(self) -> None:
        """Repeatedly clicks 'show more' until all cars are visible in search results."""
        while True:
            try:
                self._click_by_xpath(SEARCH["show_more"], 0.1)
            except NoSuchElementException:
                return

    def _add_car(self, car: WebElement) -> None:
        """Clicks a car button, scrolling down if it's obscured."""
        car_added = False
        while not car_added:
            try:
                self._click(car)
                car_added = True
            except Exception as e:
                if "obscures" in str(e):
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.1)
                else:
                    raise e

    def _add_car_group(self, group: Tuple[int, int]) -> None:
        """Adds a slice of cars from search results to the comparison."""
        search_results = self.driver.find_element(By.XPATH, SEARCH["search_results"])
        buttons = search_results.find_elements(By.XPATH, "./button")[group[0] : group[1]]
        for button in buttons:
            self._add_car(button)

    def _select_first_tunes(self) -> None:
        """Selects the first tune for every car in the comparison list."""
        car_list = self.driver.find_element(By.XPATH, TUNES["car_list"])
        car_rows = car_list.find_elements(By.XPATH, "./div")[:-1]
        for car_row in car_rows:
            first_tune = car_row.find_element(By.XPATH, TUNES["first_tune_suf"])
            self._click(first_tune, wiggle_on_fail=True)
        pyautogui.moveTo(100, 100)
        pyautogui.moveRel(200, 200, duration=0.1)

    def _split_car_row_html(self, car_row_html: str, tune: Tuple[int, int, int]) -> Dict[str, str]:
        """Parses a car row's HTML and returns a dict of core stats and tune values."""
        stats = car_row_html.split("Car_HeaderBackDropRight")[1].split('Car_HeaderStatValue">')[1:]
        stats = [s.split("<")[0] for s in stats]
        stats_dict = {
            "rq": car_row_html.split('BaseCard_Header2Right2">')[1].split("</div>")[0].strip(),
            "make": car_row_html.split("</b>")[1].split("</div>")[0].strip(),
            "model": car_row_html.split('_Header2Bottom">')[1].split("</div>")[0].strip(),
            "make_model": (
                car_row_html.split('class="Car_HeaderName')[1]
                .split(">")[1]
                .split("</div")[0]
                .strip()
            ),
            "year": (
                car_row_html.split('Car_HeaderBlockYear"')[1]
                .split(">")[1]
                .split("</div")[0]
                .strip()
            ),
            "top_speed": stats[0],
            "zero_sixty": stats[1],
            "handling": stats[2],
            "engine_up": tune[0],
            "weight_up": tune[1],
            "chassis_up": tune[2],
        }
        return stats_dict

    def _extract_times(self, car_row_html: str) -> Dict[str, str]:
        """Parses a car row's HTML and returns a dict of track name -> time."""
        tracks_html_list = car_row_html.split('class="Row_Content"')[1:]
        times = [t.split("<!---->")[0].split(">")[1] for t in tracks_html_list]
        return dict(zip(self.trackset, times))

    def _get_times(self, tune: Tuple[int, int, int]) -> None:
        """
        Scrapes times for all cars in the current comparison
        and appends to car_times_and_stats_dicts.
        """
        main_car_list = self.driver.find_element(By.XPATH, TUNES["car_list"])
        car_row_htmls = (
            main_car_list.get_attribute("innerHTML").split('<div id="Car_Layout')[1:]  # type: ignore
        )
        for car_row_html in car_row_htmls:
            car_stats = self._split_car_row_html(car_row_html, tune)
            car_times = self._extract_times(car_row_html)
            car_dict = car_stats | car_times
            self.car_times_and_stats_dicts.append(car_dict)

    def _count_car_divs(self) -> int:
        """Returns the number of cars currently in the comparison."""
        car_container = self.driver.find_element(By.CSS_SELECTOR, ".Main_CarList")
        car_divs = [
            d for d in car_container.find_elements(By.XPATH, "./div") if d.get_attribute("id")
        ]
        return len(car_divs)

    def _get_info(self) -> None:
        """Scrapes detailed car info from the open tune dialog and appends to car_info_dicts."""
        car = self.driver.find_element(By.XPATH, TUNES["car_info"])
        car_html = car.get_attribute("innerHTML")
        car_card = car_html.split("Row_DialogCardCard")[1]  # type: ignore
        tags_div = (
            car_html.split("Row_DialogCardTags")[1].split("Row_DialogCardDual")[0]  # type: ignore
        )
        other_stats_htmls = (
            car_html.split("Row_DialogCardBottom")[1].split("Row_DialogCardStatValue")[1:]  # type: ignore
        )

        # MRA value has no span if not present
        try:
            mra = other_stats_htmls[3].split("span")[1].split(">")[1].split("<")[0].strip()
        except IndexError:
            mra = ""

        self.car_info_dicts.append(
            {
                "rid": car_card.split(".jpg")[0].split("/")[-1].strip(),
                "rq": (
                    car_card.split('class="Car_HeaderRQValue')[1]
                    .split(">")[1]
                    .split("</div")[0]
                    .strip()
                ),
                "make_model": (
                    car_card.split('class="Car_HeaderName')[1]
                    .split(">")[1]
                    .split("</div")[0]
                    .strip()
                ),
                "year": (
                    car_card.split("Car_HeaderBlockYear")[1].split(">")[1].split("</div")[0].strip()
                ),
                "country": (
                    car_card.split("Car_HeaderBlockCountry")[1]
                    .split(">")[1]
                    .split("</div")[0]
                    .strip()
                ),
                "tyres": (
                    car_card.split("Car_HeaderBlockTiresValue")[1]
                    .split(">")[1]
                    .split("</span")[0]
                    .strip()
                ),
                "drive": (
                    car_card.split("Car_HeaderStatLabelDrive")[1]
                    .split(">")[1]
                    .split("</div")[0]
                    .strip()
                ),
                "prize": "Yes" if "Car_HeaderBlockPrize" in car_card else "No",
                "tags": "/".join([t.split(">")[-1].strip() for t in tags_div.split("</div>")[:-2]]),
                "abs": other_stats_htmls[0].split(">")[1].split("</div")[0].strip(),
                "tcs": other_stats_htmls[1].split(">")[1].split("</div")[0].strip(),
                "clearance": other_stats_htmls[2].split(">")[1].split("</div")[0].strip(),
                "mra": mra,
                "weight": other_stats_htmls[4].split(">")[1].split("</div")[0].strip(),
                "fuel": other_stats_htmls[5].split(">")[1].split("</div")[0].strip(),
                "seats": other_stats_htmls[6].split(">")[1].split("</div")[0].strip(),
                "engine_pos": other_stats_htmls[7].split(">")[1].split("</div")[0].strip(),
                "body": (
                    other_stats_htmls[8]
                    .split("</div")[0]
                    .split(">")[-1]
                    .strip()
                    .replace(",&nbsp;", "/")
                ),
                "brakes": other_stats_htmls[9].split(">")[1].split("<")[0].strip(),
            }
        )

    def _change_tune(self, tune_num: int, get_info: bool = False) -> None:
        """Changes all cars in the comparison to tune_num, optionally scraping car info."""
        for i in range(self._count_car_divs()):
            settings_xpath = TUNES["settings_rep"].replace("REPLACE", str(i + 1))
            self._click(self.driver.find_element(By.XPATH, settings_xpath), wiggle_on_fail=True)
            tune_xpath = TUNES["tune_rep"].replace("REPLACE", str(tune_num))
            self._click(self.driver.find_element(By.XPATH, tune_xpath), wiggle_on_fail=True)
            if get_info:
                self._get_info()
            self._click_off()

    @timer
    def _scrape_group(self, rarity: str, group: Tuple[int, int], g: int, num_groups: int) -> None:
        """Scrapes all tunes for a group of cars and saves progress."""
        self._add_car_group(group)
        self._click_off(0.1)

        for t, tune in enumerate([(3, 3, 2), (3, 2, 3), (2, 3, 3), (1, 1, 1)]):
            # Only do tune 3 (1,1,1) if rarity A or S
            if t == 3 and rarity not in ["A", "S"]:
                continue
            if t == 0:
                self._select_first_tunes()
            else:
                # Only need to get info once, so get it when changing from tune 0 to 1
                self._change_tune(t + 1, t == 1)
            self._get_times(tune)

        self._click_by_xpath(MENU["open_menu"])
        self._click_by_xpath(MENU["clear_cars"])
        self._click_off(0.1)
        if g + 1 != num_groups:
            self._open_car_search()

        self.scraped_groups[rarity].append(group)
        self.save_progress()

    def save_progress(self) -> None:
        """Saves current scraping progress to SCRAPING_PROGRESS_PATH."""
        progress = {
            "car_times_and_stats_dicts": self.car_times_and_stats_dicts,
            "car_info_dicts": self.car_info_dicts,
            "scraped_groups": self.scraped_groups,
            "completed_rarities": self.completed_rarities,
        }
        with open(SCRAPING_PROGRESS_PATH, "wb") as f:
            pickle.dump(progress, f)

    def scrape(self) -> None:
        """Main entry point. Runs full scrape across all target rarities."""
        self.setup_page()

        for r, rarity in enumerate(RARITIES):
            if rarity not in self.scrape_rarities:
                continue
            if rarity in self.completed_rarities:
                continue

            self._open_car_search()
            self._add_filters(r)

            car_count = self._get_car_count()
            if car_count == 0:
                self._click_off(0.1)
                continue

            groups = self._split_into_groups(car_count)
            self._show_all_cars()

            num_groups = len(groups)
            for g, group in enumerate(groups):
                if group in self.scraped_groups[rarity]:
                    continue
                self._scrape_group(rarity, group, g, num_groups)

            self.completed_rarities.append(rarity)
            self.save_progress()
