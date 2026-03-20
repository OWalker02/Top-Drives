"""Solver for TD Challenges using PuLP."""

from collections import defaultdict

import pandas as pd
import pulp

from config.challenge import PRINT_COLS
from src.challenge.challenge import (
    get_challenge_info,
    get_challenge_setup,
    get_rq_colour,
    load_challenge_dict,
)
from src.utils.timer import timer


class ChallengeSolver:
    """
    Solver for a Top Drives Challenge.

    Uses a pulp.PULP_CBC_CMD solver to find optimal solution to passed challenge.
    """

    def __init__(
        self,
        encoded_df: pd.DataFrame,
        challenge_df: pd.DataFrame,
        challenge_cat: str,
        challenge_num: int,
        only_owned: bool = False,
        time_limit: int = 600,
    ):
        """
        Args:
            encoded_df: Preprocessed encoded DataFrame.
            challenge_df: Challenge DataFrame from make_challenge_df().
            challenge_cat: The challenge category identifier.
            challenge_num: The number of challenge in the category.
            only_owned: Boolean, whether to only include owned cars in challenge solve.
            time_limit: Max time for the solver to run before printing/returning most recent
                        solution.
        """
        self.encoded_df = encoded_df
        self.data = challenge_df.to_dict(orient="index")
        self.challenge_cat = challenge_cat
        self.challenge_num = challenge_num
        self.challenge_info = get_challenge_info(challenge_cat, challenge_num)
        self.challenge_setup = get_challenge_setup(
            encoded_df, challenge_cat, challenge_num, only_owned
        )
        self.challenge_dict = {
            k: v
            for k, v in load_challenge_dict(challenge_cat, challenge_num).items()
            if self.challenge_setup["sr"] <= int(k) <= self.challenge_setup["er"]
        }
        self.time_limit = time_limit
        self.problem = pulp.LpProblem("Challenge", pulp.LpMinimize)
        self.car_keys = list(self.data.keys())
        self.round_keys = list(self.challenge_dict.keys())
        self.track_ids = [f"{round_key}.{i + 1}" for round_key in self.round_keys for i in range(5)]
        # Need a way to group all occurrences of each version of each car
        self.car_rid_groups = defaultdict(list)
        for car_key in self.car_keys:
            rid = self.data[car_key]["rid"]
            self.car_rid_groups[rid].append(car_key)
        # Every car/track combination is an element (1 if car used on track, 0 if not used)
        self.x = {}
        # Every car is an element, used for penalty calculation as multiple uses of a car is not
        # penalised multiple times
        self.y = {}

    # region Problem Setup

    @timer
    def _initialise_variables(self) -> None:
        """Initialises x and y."""
        car_track_tuples = []
        for track_id in self.track_ids:
            for car_key in self.car_keys:
                car_track_tuples.append((car_key, track_id))
        self.x = pulp.LpVariable.dicts("car_track_use", car_track_tuples, cat="Binary")
        self.y = pulp.LpVariable.dicts("car_used", self.car_keys, cat="Binary")

    @timer
    def _add_objective(self) -> None:
        """Adds the objective function to the problem: sum of penalties of all cars used."""
        objective = pulp.lpSum([self.data[i]["penalty"] * self.y[i] for i in self.car_keys])
        self.problem += objective, "Total_Penalty"

    def _constraint_x_y_link(self) -> None:
        """
        Adds constraint: If a car is used, update the corresponding y.

        For each car, the sum of its x values (tracks assigned) must be <= num_tracks * y[car].
        This forces y[car] = 1 whenever the car is used, ensuring its penalty is counted.
        """
        num_tracks = len(self.track_ids)
        for car_key in self.car_keys:
            car_x_vals = [self.x[(car_key, track_id)] for track_id in self.track_ids]
            car_y = self.y[car_key]
            self.problem.addConstraint(
                pulp.lpSum(car_x_vals) <= num_tracks * car_y, f"Link_x_y_{car_key}"
            )

    def _constraint_one_car_one_track(self) -> None:
        """
        Adds constraint: Every race must have exactly one car assigned.

        For each track, the sum of its x values (cars assigned) must be exactly 1.
        """
        for track_id in self.track_ids:
            track_x_vals = [self.x[(car_key, track_id)] for car_key in self.car_keys]
            self.problem.addConstraint(
                pulp.lpSum(track_x_vals) == 1, f"One_car_per_track_{track_id}"
            )

    def _constraint_one_car_use_per_round(self) -> None:
        """
        Adds constraint: Each car can be used at most once per round.

        For each car in each round, the sum of its x values (tracks assigned) must be 0 or 1 (<=1).
        """
        for round_key in self.round_keys:
            for car_key in self.car_keys:
                round_track_ids = [
                    track_id for track_id in self.track_ids if track_id.startswith(f"{round_key}.")
                ]
                car_round_x_vals = [self.x[(car_key, track_id)] for track_id in round_track_ids]
                self.problem.addConstraint(
                    pulp.lpSum(car_round_x_vals) <= 1,
                    f"One_car_use_per_round_{round_key}_{car_key}",
                )

    def _constraint_round_success(self) -> None:
        """
        Adds constraint: Each round must have a total score of at least 250pts.

        For each round, the sum of scores of cars assigned to tracks in the round must be >= 250.
        """
        for round_key in self.round_keys:
            round_track_ids = [
                track_id for track_id in self.track_ids if track_id.startswith(f"{round_key}.")
            ]
            assigned_car_pts = [
                self.data[car_key][track_id] * self.x[(car_key, track_id)]
                for car_key in self.car_keys
                for track_id in round_track_ids
            ]
            self.problem.addConstraint(pulp.lpSum(assigned_car_pts) >= 250, f"250_pts_{round_key}")

    def _constraint_within_rq_lim(self) -> None:
        """
        Adds constraint: The sum of RQ of cars used in a round must not exceed the round limit.

        For each round, the sum of rqs of cars assigned to a track in the round, must be <= 250.
        """
        for round_key, round_info in self.challenge_dict.items():
            rq_lim = round_info["RQ limit"]
            round_track_ids = [
                track_id for track_id in self.track_ids if track_id.startswith(f"{round_key}.")
            ]
            assigned_car_rqs = [
                self.data[car_key]["rq"] * self.x[(car_key, track_id)]
                for car_key in self.car_keys
                for track_id in round_track_ids
            ]
            self.problem.addConstraint(
                pulp.lpSum(assigned_car_rqs) <= rq_lim, f"RQ_limit_{round_key}"
            )

    def _constraint_correct_restrictions(self) -> None:
        """
        Adds constraint: All restrictions must be met

        For each round, for each restriction applying to the round, the number of cars fitting the
        restriction must be at least the required quantity.
        """
        for round_key, round_info in self.challenge_dict.items():
            round_track_ids = [
                track_id for track_id in self.track_ids if track_id.startswith(f"{round_key}.")
            ]
            for restriction, quantity in round_info["Restrictions"].items():
                assigned_car_restrictions = [
                    self.data[car_key][restriction] * self.x[(car_key, track_id)]
                    for car_key in self.car_keys
                    for track_id in round_track_ids
                ]
                self.problem.addConstraint(
                    pulp.lpSum(assigned_car_restrictions) >= quantity,
                    f"Restriction_{round_key}_{restriction}_{quantity}",
                )

    def _constraint_no_dupe_rids(self) -> None:
        """
        Adds constraint: No duplicate cars in a round
        (without this, the same car with different tunes could be selected for multiple tracks or
        different tunes used across the whole challenge with incorrect penalty).

        For each car rid, the sum of uses of that rid is 1 or 0 (<=1).
        """
        for car_rid, car_indexes in self.car_rid_groups.items():
            rid_uses = [self.y[car_index] for car_index in car_indexes]
            self.problem.addConstraint(pulp.lpSum(rid_uses) <= 1, f"One_car_per_rid_{car_rid}")

    @timer
    def _add_constraints(self) -> None:
        """Adds all constraints to problem."""
        self._constraint_x_y_link()
        self._constraint_one_car_one_track()
        self._constraint_one_car_use_per_round()
        self._constraint_round_success()
        self._constraint_within_rq_lim()
        self._constraint_correct_restrictions()
        self._constraint_no_dupe_rids()

    @timer
    def build_problem(self):
        """Constructs the PuLP problem."""
        self._initialise_variables()
        self._add_objective()
        self._add_constraints()

    # endregion

    # region Solving

    def _get_assigned_car(self, round_key: str, race_num: int):
        """Gets the index (key for self.data) of the assigned car."""
        for car_track_tup, car_track_assigned in self.x.items():
            if car_track_tup[1] == f"{round_key}.{race_num}":
                if pulp.value(car_track_assigned) == 1:
                    return car_track_tup[0]
        return None

    def _build_round_df(self, round_key: str, round_info: dict) -> pd.DataFrame:
        """Builds the results DataFrame for a single round."""
        round_restrictions = list(round_info["Restrictions"].keys())
        cols = PRINT_COLS + round_restrictions
        rows = []

        # Iterate through each race in the round
        for race_num, (track_name, challenge_time) in round_info["Tracks"].items():
            car_index = self._get_assigned_car(round_key, race_num)
            if car_index is None:
                continue

            car_data = self.data[car_index]
            row = {
                "Index": car_index,
                "Year": car_data["year"],
                "RQ": car_data["rq"],
                "Make": car_data["make"],
                "Model": car_data["model"],
                "Track": track_name,
                "Challenge Time": challenge_time,
                "Track Time": self.encoded_df.loc[car_index][track_name],
                "Points": car_data[f"{round_key}.{race_num}"],
                "Engine Up": car_data["engine_up"],
                "Weight Up": car_data["weight_up"],
                "Chassis Up": car_data["chassis_up"],
                "Penalty": car_data["penalty"],
                "Version": car_data["car_version"],
                **{restriction: car_data[restriction] for restriction in round_restrictions},
            }
            rows.append(row)

        return pd.DataFrame(rows, columns=cols)

    def print_round_summary(self, round_df: pd.DataFrame, round_key: str, rq_lim: int) -> None:
        """Prints information about a specific challenge round."""
        print(f"Round {round_key}:")
        print(round_df)
        print(
            f"{round_df['Points'].sum()} pts. "
            f"Penalty: {int(round_df['Penalty'].sum())}. "
            f"RQ Used: {round_df['RQ'].sum()} / {rq_lim}"
        )
        print()

    def _print_car(self, car_index: int, show_ups: bool) -> None:
        """Prints details about a specific car"""
        car_data = self.data[car_index]
        rq = car_data["rq"]
        year = car_data["year"]
        mm = car_data["make_model"]
        vers = car_data["car_version"]
        pen = car_data["penalty"]
        colour = get_rq_colour(rq)
        rq_coloured = f"\033[48;5;{colour}m[{rq}]\033[0m"
        line = f"{year} {rq_coloured} {mm} (Version {vers}): {pen}"
        if show_ups:
            eng = car_data["engine_up"]
            wei = car_data["weight_up"]
            cha = car_data["chassis_up"]
            ups = f"{eng}{wei}{cha}"
            line += f" - {ups}"
        print(line)

    def _get_and_print_results(self):
        """Prints round DataFrame for each round and returns list of results."""
        results = []
        cars_used_indices = []

        for round_key, round_info in self.challenge_dict.items():
            round_df = self._build_round_df(round_key, round_info)
            self.print_round_summary(round_df, round_key, round_info["RQ limit"])
            results.append(round_df)
            cars_used_indices.extend(round_df["Index"].tolist())

        return results, cars_used_indices

    def _print_cars_used(self, cars_used: list) -> list:
        """
        Prints all cars used, then all cars with penalty again.
        Returns list of details of cars used.
        """
        cars_with_penalty = [i for i in cars_used if self.data[i]["penalty"] > 0]

        print("Cars used:")
        cars_used_info = []
        for car_index in cars_used:
            self._print_car(car_index, False)
            cd = self.data[car_index]
            cars_used_info.append((cd["rq"], cd["make_model"], cd["car_version"], cd["penalty"]))

        print()
        if not cars_with_penalty:
            print("No cars with penalty.")
        else:
            print("Cars with penalty:")
            for car_index in cars_with_penalty:
                self._print_car(car_index, show_ups=True)

        return cars_used_info

    @timer
    def solve(self) -> tuple[bool, float | None, list | None, list | None]:
        """Solves the challenge, printing and returning results."""
        print(f"Solving challenge: {self.challenge_cat} ({self.challenge_num})")

        self.problem.solve(pulp.PULP_CBC_CMD(timeLimit=self.time_limit))
        status = pulp.LpStatus[self.problem.status]
        print("Status:", status)

        if status != "Optimal":
            return False, None, None, None

        obj_val = pulp.value(self.problem.objective)
        print("Objective value:", obj_val)

        results, cars_used_indices = self._get_and_print_results()

        cars_used = sorted(
            set(cars_used_indices),
            key=lambda i: (self.data[i]["rq"], self.data[i]["make"]),
            reverse=True,
        )
        cars_used_info = self._print_cars_used(cars_used)

        return True, obj_val, results, cars_used_info  # type: ignore

    # endregion
