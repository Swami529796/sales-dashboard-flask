"""Create the sample Excel workbook the dashboard reads (repeatable: fixed seed).

    python make_sample_data.py
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

OUTPUT = Path(__file__).parent / "data" / "sales_data.xlsx"
START, END = date(2025, 7, 1), date(2026, 6, 30)

# product: (category, unit price, typical units per order)
PRODUCTS = {
    "Laptop": ("Computers", 55000, 3),
    "Desktop": ("Computers", 42000, 2),
    "Monitor": ("Displays", 14000, 5),
    "Projector": ("Displays", 36000, 1),
    "Printer": ("Peripherals", 9500, 3),
    "Scanner": ("Peripherals", 8200, 2),
    "Headset": ("Accessories", 2500, 10),
    "Keyboard": ("Accessories", 1500, 12),
}
REGION_SIZE = {"North": 1.00, "South": 1.20, "East": 0.75, "West": 1.10}
SEASON = {10: 1.20, 11: 1.30, 12: 1.10, 3: 1.10}  # festive season and financial year end


def main() -> None:
    rng = random.Random(11)
    rows = []
    day = START
    while day <= END:
        months_in = (day.year - START.year) * 12 + day.month - START.month
        level = (1 + 0.02 * months_in) * SEASON.get(day.month, 1.0)
        for region, size in REGION_SIZE.items():
            for _ in range(rng.choices([0, 1, 2, 3], weights=[15, 40, 30, 15])[0]):
                product = rng.choice(list(PRODUCTS))
                category, price, typical = PRODUCTS[product]
                units = max(1, round(typical * size * level * rng.uniform(0.5, 1.5)))
                rows.append([day, region, product, category, units, price, units * price])
        day += timedelta(days=1)

    frame = pd.DataFrame(rows, columns=["Date", "Region", "Product", "Category", "Units", "Unit Price", "Revenue"])
    OUTPUT.parent.mkdir(exist_ok=True)
    frame.to_excel(OUTPUT, sheet_name="Sales", index=False)
    print(f"Wrote {len(frame):,} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
