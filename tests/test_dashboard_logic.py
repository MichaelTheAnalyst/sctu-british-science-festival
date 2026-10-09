"""Regression tests for public filtering and the Q1–Q7 dashboard logic."""

from __future__ import annotations

from datetime import date
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

from synthetic_data import demonstration_responses  # noqa: E402
from data import default_config_path, default_output_root  # noqa: E402
from post_analysis import (  # noqa: E402
    PERIOD_ORDER,
    answer_leaders,
    completion_distribution,
    hourly_participation,
    preference_by_period,
    responses_on_date,
)
from widgets_festival import (  # noqa: E402
    AGE_ORDER,
    COMMUNICATION_ORDER,
    HAND_ORDER,
    PIZZA_ORDER,
    current_leader,
    public_responses,
    relationship_distribution,
)


class DashboardLogicTests(unittest.TestCase):
    def test_private_runtime_paths_can_be_selected_with_environment_variables(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "QUALTRICS_CONFIG_PATH": r"C:\private\qualtrics-config.json",
                "QUALTRICS_OUTPUT_PATH": r"C:\private\response-exports",
            },
        ):
            self.assertEqual(default_config_path(), Path(r"C:\private\qualtrics-config.json"))
            self.assertEqual(default_output_root(), Path(r"C:\private\response-exports"))

    def test_demo_data_is_deterministic_and_never_public(self) -> None:
        first = demonstration_responses()
        second = demonstration_responses()
        self.assertEqual(len(first), 100)
        self.assertTrue(first.equals(second))
        self.assertTrue(public_responses(first).empty)

    def test_demo_contains_only_the_seven_public_questions(self) -> None:
        frame = demonstration_responses()
        expected = {
            "AGE_GROUP",
            "HANDEDNESS",
            "HOME_AREA",
            "PIZZA_METHOD",
            "CREATURE",
            "DAY_OUT",
            "COMMUNICATION",
        }
        self.assertTrue(expected.issubset(frame.columns))
        optional = {
            "CONTINUE_QUIZ",
            "TRIAL_STOP",
            "NEW_TREATMENT",
            "RANDOMISED_TRIAL",
            "BASELINE_CHARACTERISTICS",
            "SYSTEM_VALIDATION",
            "PLACEBO",
        }
        self.assertTrue(optional.isdisjoint(frame.columns))

    def test_demo_includes_every_current_survey_choice(self) -> None:
        frame = demonstration_responses()
        expected_choices = {
            "PIZZA_METHOD": {"Pizza cutter", "Scissors", "Knife", "I eat it whole"},
            "CREATURE": {"Cat", "Kangaroo", "Walrus", "Butterfly"},
            "DAY_OUT": {
                "Shopping in Southampton",
                "Relaxing on Bournemouth beach",
                "Walking in the New Forest",
                "In bed",
            },
            "COMMUNICATION": {"Call me!", "Text message", "Written letter", "Answer in a survey"},
        }
        for column, choices in expected_choices.items():
            self.assertEqual(set(frame[column]), choices)

    def test_relationship_percentages_are_calculated_within_each_group(self) -> None:
        distribution, percentages = relationship_distribution(
            demonstration_responses(),
            row_column="AGE_GROUP",
            answer_column="COMMUNICATION",
            row_order=AGE_ORDER,
            answer_order=COMMUNICATION_ORDER,
        )
        self.assertTrue(percentages)
        self.assertTrue(distribution["group_size"].ge(10).all())
        sums = distribution.groupby("group")["share"].sum().round(8).tolist()
        self.assertEqual(sums, [1.0] * distribution["group"].nunique())

    def test_small_groups_show_counts_instead_of_percentages(self) -> None:
        frame = pd.DataFrame(
            {
                "HANDEDNESS": ["Right: I write with my right hand", "Left: Left is best for me"],
                "PIZZA_METHOD": ["Pizza cutter", "Scissors"],
            }
        )
        distribution, percentages = relationship_distribution(
            frame,
            row_column="HANDEDNESS",
            answer_column="PIZZA_METHOD",
            row_order=HAND_ORDER,
            answer_order=PIZZA_ORDER,
        )
        self.assertFalse(percentages)
        self.assertEqual(int(distribution["count"].sum()), 2)

    def test_export_answer_labels_are_normalised(self) -> None:
        frame = pd.DataFrame(
            {
                "AGE_GROUP": ["0–15 years old: Seedling scientist"],
                "COMMUNICATION": ["Can I answer in a survey, please?"],
            }
        )
        distribution, _ = relationship_distribution(
            frame,
            row_column="AGE_GROUP",
            answer_column="COMMUNICATION",
            row_order=AGE_ORDER,
            answer_order=COMMUNICATION_ORDER,
        )
        selected = distribution.loc[distribution["count"].eq(1)].iloc[0]
        self.assertEqual(selected["group"], "0–15")
        self.assertEqual(selected["answer"], "Answer in a survey")

    def test_current_result_reports_a_tie_instead_of_choosing_first(self) -> None:
        frame = pd.DataFrame({"PIZZA_METHOD": ["Pizza cutter", "Scissors", "Knife"]})
        self.assertEqual(current_leader(frame), "Tie: Pizza cutter, Scissors and Knife")

    def test_post_analysis_hourly_counts_preserve_empty_hours(self) -> None:
        frame = pd.DataFrame(
            {
                "RecordedDate": pd.to_datetime(
                    ["2026-09-20 08:05:00", "2026-09-20 08:55:00", "2026-09-20 10:10:00"]
                )
            }
        )
        hourly = hourly_participation(frame)
        self.assertEqual(hourly["responses"].tolist(), [2, 0, 1])
        self.assertEqual(hourly["cumulative"].tolist(), [2, 2, 3])

    def test_post_analysis_shares_sum_within_each_period(self) -> None:
        distribution = preference_by_period(
            demonstration_responses(),
            "PIZZA_METHOD",
            PIZZA_ORDER,
        )
        self.assertTrue(set(distribution["period"]).issubset(set(PERIOD_ORDER)))
        sums = distribution.groupby("period")["share"].sum().round(8).tolist()
        self.assertEqual(sums, [1.0] * distribution["period"].nunique())

    def test_post_analysis_completion_buckets_and_leaders_cover_demo(self) -> None:
        frame = demonstration_responses()
        completion = completion_distribution(frame)
        self.assertEqual(int(completion["responses"].sum()), len(frame))
        leaders = answer_leaders(frame)
        self.assertEqual(len(leaders), 4)
        self.assertTrue(all(leader.count > 0 and 0 < leader.share <= 1 for leader in leaders))

    def test_post_analysis_is_restricted_to_20_september(self) -> None:
        frame = demonstration_responses()
        frame.loc[0, "RecordedDate"] = pd.Timestamp("2026-09-19 12:00:00", tz="UTC")
        selected = responses_on_date(frame, date(2026, 9, 20))
        self.assertEqual(len(selected), len(frame) - 1)
        self.assertEqual(
            set(pd.to_datetime(selected["RecordedDate"]).dt.date),
            {date(2026, 9, 20)},
        )


if __name__ == "__main__":
    unittest.main()
