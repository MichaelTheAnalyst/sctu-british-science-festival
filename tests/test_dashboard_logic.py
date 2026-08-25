"""Regression tests for public filtering, demo isolation, and milestones."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

from history import leader_history  # noqa: E402
from synthetic_data import demonstration_responses  # noqa: E402
from widgets_festival import age_distribution, current_leader, public_responses  # noqa: E402


class DashboardLogicTests(unittest.TestCase):
    def test_demo_data_is_deterministic_and_never_public(self) -> None:
        first = demonstration_responses()
        second = demonstration_responses()
        self.assertEqual(len(first), 125)
        self.assertTrue(first.equals(second))
        self.assertTrue(public_responses(first).empty)

    def test_demo_exercises_all_survey_stories(self) -> None:
        frame = demonstration_responses()
        self.assertTrue(frame["FRAME_POSITIVE"].notna().any())
        self.assertTrue(frame["FRAME_NEGATIVE"].notna().any())
        self.assertGreaterEqual(frame["AGE_GROUP"].nunique(), 4)
        self.assertIsNotNone(current_leader(frame))

    def test_age_analysis_compares_only_groups_with_ten_answers(self) -> None:
        distribution, insight = age_distribution(demonstration_responses(), minimum_group_size=10)
        visible_groups = distribution[["age", "group_size"]].drop_duplicates()
        self.assertGreaterEqual(len(visible_groups), 2)
        self.assertTrue(visible_groups["group_size"].ge(10).all())
        self.assertEqual(distribution.groupby("age")["share"].sum().round(8).tolist(), [1.0] * len(visible_groups))
        self.assertIn("overall crowd", insight)

    def test_age_analysis_handles_one_early_response(self) -> None:
        frame = pd.DataFrame({"AGE_GROUP": ["25–49"], "PIZZA_METHOD": ["Knife"]})
        distribution, insight = age_distribution(frame)
        self.assertFalse(distribution.empty)
        self.assertEqual(set(distribution["age"]), {"25–49"})
        self.assertEqual(insight, "Too early to compare age groups.")

    def test_current_result_reports_a_tie_instead_of_choosing_first(self) -> None:
        frame = pd.DataFrame(
            {"PIZZA_METHOD": ["Fold or tear it", "Scissors", "Knife", "Fold or tear it", "Scissors", "Knife"]}
        )
        self.assertEqual(current_leader(frame), "Tie: Knife, Scissors and Fold or tear it")

    def test_history_records_tied_checkpoint(self) -> None:
        frame = pd.DataFrame({"PIZZA_METHOD": ["Knife", "Scissors", "Knife", "Scissors", "Fold or tear it", "Fold or tear it"]})
        history = leader_history(frame)
        self.assertEqual(history.iloc[-1]["leader"], "Tie: Fold or tear it / Knife / Scissors")

    def test_history_includes_milestones_and_current_total(self) -> None:
        history = leader_history(demonstration_responses())
        self.assertEqual(history["responses"].tolist(), [5, 10, 25, 50, 100, 125])
        self.assertFalse(history["leader"].isna().any())

    def test_first_milestone_is_a_single_checkpoint(self) -> None:
        history = leader_history(demonstration_responses().iloc[:5])
        self.assertEqual(history["responses"].tolist(), [5])


if __name__ == "__main__":
    unittest.main()
