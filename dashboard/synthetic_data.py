"""Deterministic demonstration data for the seven public survey questions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import random

import pandas as pd


def demonstration_responses(size: int = 100, seed: int = 2026) -> pd.DataFrame:
    """Return synthetic Q1–Q7 responses shaped like a Qualtrics export."""
    rng = random.Random(seed)
    ages = ["0–15", "16–24", "25–49", "50+", "Prefer not to say"]
    hands = ["Right", "Left", "Both", "Prefer not to say"]
    homes = ["City", "Town", "Village or rural area", "Prefer not to say"]
    pizzas = ["Pizza cutter", "Scissors", "Knife", "I eat it whole"]
    creatures = ["Cat", "Kangaroo", "Walrus", "Butterfly"]
    days_out = [
        "Shopping in Southampton",
        "Relaxing on Bournemouth beach",
        "Walking in the New Forest",
        "In bed",
    ]
    communication = ["Call me!", "Text message", "Written letter", "Answer in a survey"]
    started = datetime(2026, 9, 20, 9, 30, tzinfo=timezone.utc)
    rows: list[dict[str, object]] = []

    for index in range(size):
        age = rng.choices(ages, weights=[18, 20, 34, 22, 6])[0]
        hand = rng.choices(hands, weights=[68, 13, 14, 5])[0]
        home = rng.choices(homes, weights=[38, 33, 24, 5])[0]
        duration_band = rng.choices(
            [(45, 119), (120, 299), (300, 599), (600, 1199), (1200, 2100)],
            weights=[24, 32, 18, 16, 10],
        )[0]
        duration_seconds = rng.randint(*duration_band)
        recorded_at = started + timedelta(minutes=index * 3)

        pizza_weights = {
            "Right": [46, 14, 25, 15],
            "Left": [32, 26, 25, 17],
            "Both": [35, 28, 20, 17],
            "Prefer not to say": [38, 21, 23, 18],
        }[hand]
        creature_weights = {
            "Right": [38, 25, 20, 17],
            "Left": [24, 34, 22, 20],
            "Both": [29, 21, 31, 19],
            "Prefer not to say": [25, 25, 25, 25],
        }[hand]
        day_weights = {
            "City": [38, 28, 19, 15],
            "Town": [27, 28, 30, 15],
            "Village or rural area": [17, 22, 44, 17],
            "Prefer not to say": [25, 25, 25, 25],
        }[home]
        communication_weights = {
            "0–15": [12, 47, 9, 32],
            "16–24": [10, 53, 8, 29],
            "25–49": [22, 41, 12, 25],
            "50+": [39, 24, 22, 15],
            "Prefer not to say": [25, 25, 25, 25],
        }[age]

        rows.append(
            {
                "StartDate": recorded_at - timedelta(seconds=duration_seconds),
                "EndDate": recorded_at,
                "RecordedDate": recorded_at,
                "Duration (in seconds)": duration_seconds,
                "Finished": True,
                "DistributionChannel": "synthetic-demonstration",
                "AGE_GROUP": age if rng.random() > 0.03 else pd.NA,
                "HANDEDNESS": hand if rng.random() > 0.03 else pd.NA,
                "HOME_AREA": home if rng.random() > 0.03 else pd.NA,
                "PIZZA_METHOD": rng.choices(pizzas, weights=pizza_weights)[0],
                "CREATURE": rng.choices(creatures, weights=creature_weights)[0],
                "DAY_OUT": rng.choices(days_out, weights=day_weights)[0],
                "COMMUNICATION": rng.choices(communication, weights=communication_weights)[0],
            }
        )

    return pd.DataFrame(rows)
