"""Sales Dashboard: a small Flask app that turns an Excel file into an interactive dashboard.

    python app.py            then open http://127.0.0.1:5000

The workbook is re-read automatically whenever it is saved, so the dashboard
always shows the latest data without restarting the server.

Author : Swaminathan Narayanan
Repo   : https://github.com/Swami529796/sales-dashboard-flask
"""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template, request

DATA_FILE = Path(os.environ.get("SALES_DATA", Path(__file__).parent / "data" / "sales_data.xlsx"))
REQUIRED_COLUMNS = ["Date", "Region", "Product", "Category", "Units", "Unit Price", "Revenue"]

app = Flask(__name__)
_cache: dict = {"modified": None, "data": None}


def load_data() -> pd.DataFrame:
    """Read the workbook, but only when the file has changed since the last read."""
    modified = DATA_FILE.stat().st_mtime
    if _cache["modified"] != modified:
        data = pd.read_excel(DATA_FILE)
        missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
        if missing:
            raise ValueError(f"{DATA_FILE.name} is missing column(s): {', '.join(missing)}")
        data["Date"] = pd.to_datetime(data["Date"])
        _cache.update(modified=modified, data=data)
    return _cache["data"]


def apply_filters(data: pd.DataFrame, region: str, category: str, start, end) -> pd.DataFrame:
    mask = (data["Date"] >= start) & (data["Date"] <= end)
    if region:
        mask &= data["Region"] == region
    if category:
        mask &= data["Category"] == category
    return data[mask]


def kpis(frame: pd.DataFrame) -> dict:
    revenue = float(frame["Revenue"].sum())
    orders = int(len(frame))
    return {
        "revenue": revenue,
        "units": int(frame["Units"].sum()),
        "orders": orders,
        "avg_order_value": revenue / orders if orders else 0.0,
    }


def change(current: float, previous: float) -> float | None:
    return (current - previous) / previous if previous else None


def grouped(frame: pd.DataFrame, column: str, top: int | None = None) -> dict:
    totals = frame.groupby(column)["Revenue"].sum().sort_values(ascending=False)
    if top:
        totals = totals.head(top)
    return {"labels": [str(label) for label in totals.index], "values": [float(value) for value in totals]}


@app.route("/")
def index():
    data = load_data()
    last = data["Date"].max()
    # open on the latest six months, so the cards can show a change vs the six months before
    default_start = max((last - pd.DateOffset(months=5)).replace(day=1), data["Date"].min())
    return render_template(
        "index.html",
        regions=sorted(data["Region"].unique()),
        categories=sorted(data["Category"].unique()),
        first_date=data["Date"].min().date().isoformat(),
        last_date=last.date().isoformat(),
        default_start=default_start.date().isoformat(),
        source=DATA_FILE.name,
        rows=len(data),
    )


@app.route("/api/summary")
def summary():
    """Everything the page needs for the chosen filters, in one JSON response."""
    data = load_data()
    try:
        start = pd.Timestamp(request.args.get("start") or data["Date"].min())
        end = pd.Timestamp(request.args.get("end") or data["Date"].max())
    except ValueError:
        return jsonify(error="Dates must be in YYYY-MM-DD format."), 400
    if start > end:
        return jsonify(error="The start date must be on or before the end date."), 400
    region = request.args.get("region", "")
    category = request.args.get("category", "")

    current = apply_filters(data, region, category, start, end)
    # compare with the period of the same length immediately before
    days = (end - start).days + 1
    previous = apply_filters(data, region, category, start - timedelta(days=days), start - timedelta(days=1))

    now, before = kpis(current), kpis(previous)
    monthly = current.groupby(current["Date"].dt.to_period("M"))["Revenue"].sum()
    return jsonify(
        kpis=now,
        changes={key: change(now[key], before[key]) for key in now},
        monthly={"labels": [period.strftime("%b %Y") for period in monthly.index],
                 "values": [float(value) for value in monthly]},
        by_region=grouped(current, "Region"),
        by_category=grouped(current, "Category"),
        top_products=grouped(current, "Product", top=8),
        rows=len(current),
    )


if __name__ == "__main__":
    app.run(debug=False)
