"""Deterministic demonstration data for festival-display development."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import random

import pandas as pd


def demonstration_responses(size: int = 125, seed: int = 2026) -> pd.DataFrame:
    """Return clearly synthetic responses shaped like the Qualtrics export."""
    rng = random.Random(seed)
    pizza = ["Pizza cutter", "Knife", "Scissors", "Fold or tear it", "Someone else can do it"]
    ages = ["Under 16", "16–24", "25–49", "50+", "Prefer not to say"]
    effectiveness = [
        "Not at all effective",
        "Slightly effective",
        "Moderately effective",
        "Very effective",
        "Extremely effective",
    ]
    overclaims = [
        "Scissors are currently leading among the festival visitors who answered",
        "Most people across the UK use scissors",
        "Scissors are scientifically the best method",
        "We cannot learn anything from the answers",
        "Not sure",
    ]
    started = datetime(2026, 9, 12, 9, 30, tzinfo=timezone.utc)
    rows: list[dict[str, object]] = []

    for index in range(size):
        age = rng.choices(ages, weights=[18, 20, 34, 22, 6])[0]
        if index < 10:
            pizza_choice = rng.choices(pizza, weights=[16, 10, 45, 24, 5])[0]
        elif index < 25:
            pizza_choice = rng.choices(pizza, weights=[23, 10, 25, 37, 5])[0]
        else:
            weights = {
                "Under 16": [18, 9, 38, 31, 4],
                "16–24": [27, 10, 26, 33, 4],
                "25–49": [38, 16, 19, 23, 4],
                "50+": [44, 21, 15, 17, 3],
                "Prefer not to say": [32, 16, 23, 25, 4],
            }[age]
            pizza_choice = rng.choices(pizza, weights=weights)[0]

        predicted = rng.choices(pizza, weights=[43, 11, 25, 17, 4])[0]
        positive_group = index % 2 == 0
        frame_weights = [3, 8, 20, 40, 29] if positive_group else [7, 15, 27, 33, 18]
        frame_answer = rng.choices(effectiveness, weights=frame_weights)[0]
        privacy = rng.choices(["Myth", "Fact", "Not sure"], weights=[82, 7, 11])[0]
        overclaim = rng.choices(overclaims, weights=[77, 8, 4, 5, 6])[0]

        rows.append(
            {
                "RecordedDate": started + timedelta(minutes=index * 3),
                "Finished": True,
                "DistributionChannel": "synthetic-demonstration",
                "AGE_GROUP": age if rng.random() > 0.05 else pd.NA,
                "PIZZA_METHOD": pizza_choice,
                "PREDICT_LEADER": predicted,
                "FRAME_POSITIVE": frame_answer if positive_group else pd.NA,
                "FRAME_NEGATIVE": frame_answer if not positive_group else pd.NA,
                "PRIVACY_MYTH": privacy if rng.random() > 0.03 else pd.NA,
                "SPOT_OVERCLAIM": overclaim if rng.random() > 0.04 else pd.NA,
            }
        )

    return pd.DataFrame(rows)
