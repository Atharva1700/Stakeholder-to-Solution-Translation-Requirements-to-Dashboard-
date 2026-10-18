"""Simulates a support ticket queue for three teams. Made-up data, fixed seed.

Billing has a built-in slowdown after week 6 so the trend requirement (R2) has something
to show. The slowdown is a modeled effect, not an observed one.
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 11
N = 2400
OUT = Path(__file__).parent / "data" / "tickets.csv"
START = pd.Timestamp("2026-08-03")  # a Monday
WEEKS = 12


def simulate(seed=SEED, n=N):
    rng = np.random.default_rng(seed)
    team = rng.choice(["Billing", "Technical", "Accounts"], n, p=[0.45, 0.35, 0.20])
    priority = rng.choice(["P1", "P2", "P3"], n, p=[0.15, 0.35, 0.50])
    opened = START + pd.to_timedelta(rng.uniform(0, WEEKS * 7, n), unit="D")

    base_hours = {"P1": 0.6, "P2": 2.5, "P3": 14.0}
    mean_hours = np.array([base_hours[p] for p in priority])
    week = (opened - START).days // 7
    slowdown = np.where((team == "Billing") & (week >= 6), 2.2, 1.0)
    response_hours = rng.exponential(mean_hours * slowdown)
    responded = rng.random(n) < 0.93  # some tickets never get a first response yet

    first_response = opened + pd.to_timedelta(response_hours, unit="h")
    closed = first_response + pd.to_timedelta(rng.uniform(4, 96, n), unit="h")
    is_closed = responded & (rng.random(n) < 0.8)

    df = pd.DataFrame({
        "ticket_id": [f"T{i:05d}" for i in range(n)],
        "team": team,
        "priority": priority,
        "opened_at": opened,
        "first_response_at": pd.Series(first_response).where(responded),
        "closed_at": pd.Series(closed).where(is_closed),
    })
    # The data is as of the cutoff: nothing after it exists yet.
    cutoff = START + pd.Timedelta(days=WEEKS * 7)
    df.loc[df.opened_at >= cutoff, ["first_response_at", "closed_at"]] = pd.NaT
    df.loc[df.first_response_at >= cutoff, "first_response_at"] = pd.NaT
    df.loc[df.closed_at >= cutoff, "closed_at"] = pd.NaT
    return df


if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    df = simulate()
    df["opened_at"] = df.opened_at.dt.strftime("%Y-%m-%d %H:%M:%S")
    for col in ["first_response_at", "closed_at"]:
        df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S")
    df.to_csv(OUT, index=False)
    print(f"wrote {OUT}")
