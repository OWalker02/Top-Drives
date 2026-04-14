"""Solver for TD Challenges using PuLP."""

from collections import defaultdict

import pandas as pd
import pulp
from pulp import LpAffineExpression

from config.challenge import PRINT_COLS
from src.challenge.challenge import (
    get_challenge_info,
    get_rq_colour,
    load_filtered_challenge_dict,
)
from src.utils.timer import timer


class ChallengeSolver:
    """
    Solver for a Top Drives Challenge.
    Uses pulp.PULP_CBC_CMD to find the optimal car assignment minimising total penalty.
    """

    def __init__(
        self,
        encoded_df: pd.DataFrame,
        challenge_df: pd.DataFrame,
        challenge_cat: str,
        challenge_num: int,
        time_limit: int = 600,
    ):
        """
        Args:
            encoded_df: Preprocessed encoded DataFrame.
            challenge_df: Challenge DataFrame from make_challenge_df().
            challenge_cat: The challenge category identifier.
            challenge_num: The challenge number within the category.
            only_owned: If True, only include owned cars.
            time_limit: Max solver time in seconds before returning best found solution.
        """
        # Data
        self.encoded_df = encoded_df
        self.data: dict[int, dict] = challenge_df.to_dict(orient="index")  # type: ignore

        # Challenge config
        self.challenge_cat = challenge_cat
        self.challenge_num = challenge_num
        self.challenge_info = get_challenge_info(challenge_cat, challenge_num)
        self.challenge_dict = load_filtered_challenge_dict(self.challenge_info)

        # Keys
        print(type(self.data.keys()))
        print(self.data.keys())
        self.car_keys: list[int] = list(self.data.keys())
        self.round_keys: list[str] = list(self.challenge_dict.keys())
        self.track_ids: list[str] = [f"{r}.{i + 1}" for r in self.round_keys for i in range(5)]

        # Solver config
        self.time_limit = time_limit
        self.problem = pulp.LpProblem("Challenge", pulp.LpMinimize)

        # Set by build_problem()
        self.x: dict = {}
        self.y: dict = {}
        self.car_rid_groups: defaultdict[str, list[int]] = defaultdict(list)

        # Set by solve()
        self.status: str = "Not solved"
        self.objective_value: LpAffineExpression | float | None = None
        self.round_dfs: dict[str, pd.DataFrame] = {}
        self.cars_used: list[int] = []

    # region Build

    def _build_car_rid_groups(self) -> None:
        for car_key in self.car_keys:
            self.car_rid_groups[self.data[car_key]["rid"]].append(car_key)  # type: ignore

    @timer
    def _initialise_variables(self) -> None:
        """Initialises x (car/track assignments) and y (car used flags)."""
        car_track_tuples = [
            (car_key, track_id) for track_id in self.track_ids for car_key in self.car_keys
        ]
        self.x = pulp.LpVariable.dicts("car_track_use", car_track_tuples, cat="Binary")
        self.y = pulp.LpVariable.dicts("car_used", self.car_keys, cat="Binary")

    @timer
    def _add_objective(self) -> None:
        """Minimise total penalty of all cars used."""
        self.problem += (
            pulp.lpSum([self.data[i]["penalty"] * self.y[i] for i in self.car_keys]),
            "Total_Penalty",
        )

    def _round_track_ids(self, round_key: str) -> list[str]:
        """Returns all track ids belonging to a round."""
        return [t for t in self.track_ids if t.startswith(f"{round_key}.")]

    def _constraint_x_y_link(self) -> None:
        """If a car is used on any track, force y=1 so its penalty is counted."""
        num_tracks = len(self.track_ids)
        for car_key in self.car_keys:
            self.problem.addConstraint(
                pulp.lpSum([self.x[(car_key, t)] for t in self.track_ids])
                <= num_tracks * self.y[car_key],
                f"Link_x_y_{car_key}",
            )

    def _constraint_one_car_per_track(self) -> None:
        """Every track must have exactly one car assigned."""
        for track_id in self.track_ids:
            self.problem.addConstraint(
                pulp.lpSum([self.x[(car_key, track_id)] for car_key in self.car_keys]) == 1,
                f"One_car_per_track_{track_id}",
            )

    def _constraint_one_car_per_round(self) -> None:
        """Each car can be used at most once per round."""
        for round_key in self.round_keys:
            round_tracks = self._round_track_ids(round_key)
            for car_key in self.car_keys:
                self.problem.addConstraint(
                    pulp.lpSum([self.x[(car_key, t)] for t in round_tracks]) <= 1,
                    f"One_car_use_per_round_{round_key}_{car_key}",
                )

    def _constraint_round_success(self) -> None:
        """Each round must score at least 250 pts."""
        for round_key in self.round_keys:
            round_tracks = self._round_track_ids(round_key)
            self.problem.addConstraint(
                pulp.lpSum(
                    [
                        self.data[car_key][track_id] * self.x[(car_key, track_id)]
                        for car_key in self.car_keys
                        for track_id in round_tracks
                    ]
                )
                >= 250,
                f"250_pts_{round_key}",
            )

    def _constraint_rq_limit(self) -> None:
        """Total RQ of cars used in a round must not exceed the round's RQ limit."""
        for round_key, round_info in self.challenge_dict.items():
            round_tracks = self._round_track_ids(round_key)
            self.problem.addConstraint(
                pulp.lpSum(
                    [
                        self.data[car_key]["rq"] * self.x[(car_key, t)]
                        for car_key in self.car_keys
                        for t in round_tracks
                    ]
                )
                <= round_info["RQ limit"],
                f"RQ_limit_{round_key}",
            )

    def _constraint_restrictions(self) -> None:
        """All per-round restrictions must be met."""
        for round_key, round_info in self.challenge_dict.items():
            round_tracks = self._round_track_ids(round_key)
            for restriction, quantity in round_info["Restrictions"].items():
                self.problem.addConstraint(
                    pulp.lpSum(
                        [
                            self.data[car_key][restriction] * self.x[(car_key, t)]
                            for car_key in self.car_keys
                            for t in round_tracks
                        ]
                    )
                    >= quantity,
                    f"Restriction_{round_key}_{restriction}_{quantity}",
                )

    def _constraint_no_duplicate_rids(self) -> None:
        """The same car (by rid) cannot be used more than once across the challenge."""
        for car_rid, car_indexes in self.car_rid_groups.items():
            self.problem.addConstraint(
                pulp.lpSum([self.y[i] for i in car_indexes]) <= 1,
                f"One_car_per_rid_{car_rid}",
            )

    @timer
    def _add_constraints(self) -> None:
        """Adds all constraints to the problem."""
        self._constraint_x_y_link()
        self._constraint_one_car_per_track()
        self._constraint_one_car_per_round()
        self._constraint_round_success()
        self._constraint_rq_limit()
        self._constraint_restrictions()
        self._constraint_no_duplicate_rids()

    @timer
    def build_problem(self) -> None:
        """Constructs the full PuLP problem."""
        self._build_car_rid_groups()
        self._initialise_variables()
        self._add_objective()
        self._add_constraints()

    # endregion

    # region Solve

    def _get_assigned_car(self, round_key: str, race_num: int) -> int | None:
        """Returns the car_key of the car assigned to a specific race, or None."""
        for (car_key, track_id), var in self.x.items():
            if track_id == f"{round_key}.{race_num}" and pulp.value(var) == 1:
                return car_key
        return None

    def _build_round_df(self, round_key: str, round_info: dict) -> pd.DataFrame:
        """Builds the results DataFrame for a single round."""
        round_restrictions = list(round_info["Restrictions"].keys())
        rows = []
        for race_num, (track_name, challenge_time) in round_info["Tracks"].items():
            car_index = self._get_assigned_car(round_key, race_num)
            if car_index is None:
                continue
            car_data = self.data[car_index]
            rows.append(
                {
                    "Index": car_index,
                    "RQ": car_data["rq"],
                    "Rid": car_data["rid"],
                    "Track": track_name,
                    "Challenge Time": challenge_time,
                    "Track Time": self.encoded_df.loc[car_index][track_name],
                    "Points": car_data[f"{round_key}.{race_num}"],
                    "Engine Up": car_data["engine_up"],
                    "Weight Up": car_data["weight_up"],
                    "Chassis Up": car_data["chassis_up"],
                    "Penalty": car_data["penalty"],
                    "Version": car_data["car_version"],
                    **{r: car_data[r] for r in round_restrictions},
                }
            )
        return pd.DataFrame(rows, columns=PRINT_COLS + round_restrictions)

    def _extract_results(self) -> None:
        """Populates self.round_dfs and self.cars_used from solved x/y variables."""
        cars_used_set: set[int] = set()
        for round_key, round_info in self.challenge_dict.items():
            round_df = self._build_round_df(round_key, round_info)
            self.round_dfs[round_key] = round_df
            cars_used_set.update(round_df["Index"].tolist())
        self.cars_used = sorted(
            cars_used_set,
            key=lambda i: (self.data[i]["rq"], self.data[i]["rid"]),
            reverse=True,
        )

    @timer
    def solve(self) -> bool:
        """
        Solves the challenge and populates self.status, self.objective_value,
        self.round_dfs, and self.cars_used.
        Returns True if an optimal solution was found.
        """
        print(f"Solving: {self.challenge_cat} {self.challenge_num}")
        self.problem.solve(
            pulp.PULP_CBC_CMD(timeLimit=self.time_limit, msg=True, logPath="cbc.log")
        )
        self.status = pulp.LpStatus[self.problem.status]

        if self.status != "Optimal":
            print(f"Status: {self.status}")
            return False

        self.objective_value = pulp.value(self.problem.objective)
        print(self.objective_value)
        self._extract_results()
        return True

    # endregion

    # region Print

    def _print_car(self, car_index: int, show_ups: bool = False) -> None:
        """Prints a single car with coloured RQ."""
        cd = self.data[car_index]
        colour = get_rq_colour(cd["rq"])
        rq_str = f"\033[48;5;{colour}m[{cd['rq']}]\033[0m"
        line = f"{rq_str} {cd['rid']} (V{cd['car_version']}): {cd['penalty']}"
        if show_ups:
            line += f" - {cd['engine_up']}{cd['weight_up']}{cd['chassis_up']}"
        print(line)

    def print_round(self, round_key: str) -> None:
        """Prints the results DataFrame and summary for a single round."""
        round_df = self.round_dfs[round_key]
        round_info = self.challenge_dict[round_key]
        print(f"Round {round_key}:")
        print(round_df.to_string(index=False))
        print(
            f"{round_df['Points'].sum()} pts. "
            f"Penalty: {int(round_df['Penalty'].sum())}. "
            f"RQ Used: {round_df['RQ'].sum()} / {round_info['RQ limit']}"
        )
        print()

    def print_cars_used(self) -> None:
        """Prints all cars used, then just ones with a penalty."""
        print("Cars used:")
        for car_index in self.cars_used:
            self._print_car(car_index)

        penalised = [i for i in self.cars_used if self.data[i]["penalty"] > 0]
        if not penalised:
            print("\nNo cars with penalty.")
        else:
            print("\nCars with penalty:")
            for car_index in penalised:
                self._print_car(car_index, show_ups=True)

    def print_result(self) -> None:
        """Prints the full solve result: status, rounds, and cars used."""
        if self.status != "Optimal":
            print(f"No solution found. Status: {self.status}")
            return
        print(f"Objective value: {self.objective_value}")
        for round_key in self.round_keys:
            self.print_round(round_key)
        self.print_cars_used()

    # endregion
