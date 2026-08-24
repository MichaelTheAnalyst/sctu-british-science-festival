"""Regression tests for public filtering, demo isolation, and milestones."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

from history import leader_history  # noqa: E402
from synthetic_data import demonstration_responses  # noqa: E402
from widgets_festival import current_leader, public_responses  # noqa: E402


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

    def test_history_includes_milestones_and_current_total(self) -> None:
        history = leader_history(demonstration_responses())
        self.assertEqual(history["responses"].tolist(), [5, 10, 25, 50, 100, 125])
        self.assertFalse(history["leader"].isna().any())


if __name__ == "__main__":
    unittest.main()
