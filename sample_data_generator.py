"""
sample_data_generator.py
Generates a realistic demo CSV so the app can be tried without real data.

Usage
-----
    python sample_data_generator.py               # writes sample_sales.csv
    python sample_data_generator.py --rows 5000   # larger dataset
"""

import argparse
import random
from datetime import date, timedelta

import numpy as np
import pandas as pd

# ── Seed for reproducibility ──────────────────────────────────────────────────
RNG = np.random.default_rng(42)
random.seed(42)

# ── Master lookup tables ──────────────────────────────────────────────────────
PRODUCTS = {
    "Laptop Pro 15":     {"base_price": 1_299, "base_cost": 820},
    "Wireless Mouse":    {"base_price":    49, "base_cost":  18},
    "USB-C Hub":         {"base_price":    79, "base_cost":  28},
    "Mechanical Keyboard": {"base_price": 149, "base_cost":  55},
    "27\" 4K Monitor":   {"base_price":   549, "base_cost": 310},
    "Webcam HD 1080p":   {"base_price":    89, "base_cost":  32},
    "Noise-Cancel Headset": {"base_price":199, "base_cost":  80},
    "Portable SSD 1TB":  {"base_price":   119, "base_cost":  58},
    "Laptop Stand":      {"base_price":    45, "base_cost":  14},
    "HDMI 2.1 Cable":    {"base_price":    19, "base_cost":   5},
}

CUSTOMERS = [
    "Acme Corp", "Bright Solutions", "CloudNine Ltd", "Delta Systems",
    "EagleTech", "Forte Industries", "Greenwave Inc", "Horizon Labs",
    "Infosync", "JetStream Co", "KineticData", "LumaLogic",
    "Meridian Group", "NovaBridge", "Omega Ventures",
]

# Seasonal multipliers — index 0 = January
SEASONAL_WEIGHTS = [0.7, 0.75, 0.9, 1.0, 1.05, 1.1,
                    0.95, 1.0, 1.1, 1.15, 1.3, 1.5]


def _random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def generate_dataset(n_rows: int = 2_000) -> pd.DataFrame:
    start = date(2024, 1, 1)
    end   = date(2024, 12, 31)

    rows = []
    for _ in range(n_rows):
        d          = _random_date(start, end)
        product    = random.choice(list(PRODUCTS.keys()))
        meta       = PRODUCTS[product]
        seasonal   = SEASONAL_WEIGHTS[d.month - 1]
        customer   = random.choice(CUSTOMERS)

        # Price with ±5 % variance and seasonal bump
        price = round(
            meta["base_price"] * seasonal * RNG.uniform(0.95, 1.05), 2
        )
        cost  = round(
            meta["base_cost"]  * RNG.uniform(0.97, 1.03), 2
        )
        qty   = int(RNG.integers(1, 15))

        rows.append(
            {
                "date":     d.isoformat(),
                "product":  product,
                "price":    price,
                "cost":     cost,
                "quantity": qty,
                "customer": customer,
            }
        )

    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a demo sales CSV.")
    parser.add_argument("--rows",   type=int, default=2_000, help="Number of rows (default 2000)")
    parser.add_argument("--output", type=str, default="sample_sales.csv")
    args = parser.parse_args()

    df = generate_dataset(args.rows)
    df.to_csv(args.output, index=False)
    print(f"Generated {len(df):,} rows → {args.output}")
