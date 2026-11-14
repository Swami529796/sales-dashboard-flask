"""Tests for the dashboard API. Run with: python -m pytest"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as dashboard  # noqa: E402


@pytest.fixture()
def client():
    dashboard.app.config["TESTING"] = True
    return dashboard.app.test_client()


def test_home_page_lists_the_filters(client):
    page = client.get("/")
    assert page.status_code == 200
    assert b"All regions" in page.data and b"North" in page.data


def test_summary_totals_match_the_workbook(client):
    data = dashboard.load_data()
    summary = client.get("/api/summary").get_json()
    assert summary["rows"] == len(data)
    assert summary["kpis"]["revenue"] == pytest.approx(data["Revenue"].sum())
    assert sum(summary["by_region"]["values"]) == pytest.approx(data["Revenue"].sum())
    assert len(summary["monthly"]["labels"]) == 12


def test_region_filter_only_returns_that_region(client):
    summary = client.get("/api/summary?region=East").get_json()
    assert summary["by_region"]["labels"] == ["East"]


def test_change_compares_with_the_previous_period(client):
    data = dashboard.load_data()
    june = data[(data["Date"] >= "2026-06-01") & (data["Date"] <= "2026-06-30")]["Revenue"].sum()
    may = data[(data["Date"] >= "2026-05-02") & (data["Date"] <= "2026-05-31")]["Revenue"].sum()
    summary = client.get("/api/summary?start=2026-06-01&end=2026-06-30").get_json()
    assert summary["changes"]["revenue"] == pytest.approx((june - may) / may)


def test_no_earlier_period_gives_no_change(client):
    summary = client.get("/api/summary").get_json()
    assert summary["changes"]["revenue"] is None


def test_bad_dates_are_rejected_with_a_message(client):
    assert client.get("/api/summary?start=not-a-date").status_code == 400
    reply = client.get("/api/summary?start=2026-06-30&end=2026-06-01")
    assert reply.status_code == 400 and "start date" in reply.get_json()["error"]
