"""Checks the SQL metrics against plain-Python counts, and the SLA rules on hand-built tickets."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_dashboard as bd  # noqa: E402

TARGET_HOURS = {"P1": 1, "P2": 4, "P3": 24}  # a separate copy of the agreed targets
AS_OF = datetime.fromisoformat(bd.AS_OF)


def hand_count(df):
    """Plain-Python SLA counts: total due/met, and per team."""
    due = met = 0
    per_team = {}
    for r in df.itertuples():
        opened = datetime.fromisoformat(r.opened_at)
        target = TARGET_HOURS[r.priority]
        if opened + timedelta(hours=target) > AS_OF:
            continue
        ok = pd.notna(r.first_response_at) and (
            datetime.fromisoformat(r.first_response_at) - opened <= timedelta(hours=target))
        due += 1
        met += int(ok)
        d, m = per_team.get(r.team, (0, 0))
        per_team[r.team] = (d + 1, m + int(ok))
    return due, met, per_team


def hand_backlog(df, week_end):
    n = 0
    for r in df.itertuples():
        opened = datetime.fromisoformat(r.opened_at)
        closed = datetime.fromisoformat(r.closed_at) if pd.notna(r.closed_at) else None
        if opened < week_end and (closed is None or closed >= week_end):
            n += 1
    return n


@pytest.fixture(scope="module")
def df():
    return pd.read_csv(bd.DATA, dtype=str)


@pytest.fixture(scope="module")
def con():
    return bd.build_db()


def test_overall_matches_hand_count(df, con):
    due, met, _ = hand_count(df)
    got = con.execute(
        "SELECT SUM(is_due), SUM(CASE WHEN met_target = 1 THEN 1 ELSE 0 END) "
        "FROM v_ticket_sla WHERE is_due = 1").fetchone()
    assert got == (due, met)


def test_by_team_matches_hand_count(df, con):
    _, _, per_team = hand_count(df)
    rows = con.execute(
        "SELECT team, SUM(is_due), SUM(CASE WHEN met_target = 1 THEN 1 ELSE 0 END) "
        "FROM v_ticket_sla WHERE is_due = 1 GROUP BY team").fetchall()
    assert {team: (d, m) for team, d, m in rows} == per_team


def test_weekly_attainment_adds_up_to_overall(con):
    weekly_due = con.execute("SELECT SUM(due_tickets) FROM v_weekly_attainment").fetchone()[0]
    overall_due = con.execute("SELECT SUM(is_due) FROM v_ticket_sla").fetchone()[0]
    assert weekly_due == overall_due


def test_backlog_matches_hand_count_every_week(df, con):
    rows = con.execute("SELECT week_start, open_tickets FROM v_weekly_backlog").fetchall()
    assert len(rows) == 12
    for week_start, open_tickets in rows:
        week_end = datetime.fromisoformat(week_start) + timedelta(days=7)
        assert open_tickets == hand_backlog(df, week_end), week_start


def test_no_response_is_dated_after_reporting_date(df):
    times = df.first_response_at.dropna()
    assert (times < bd.AS_OF).all()


def test_sla_rules_on_hand_built_tickets():
    rows = pd.DataFrame([
        # ticket, team, priority, opened, first response, closed
        ("A", "Billing", "P1", "2026-10-05 10:00:00", "2026-10-05 10:30:00", None),  # met
        ("B", "Billing", "P1", "2026-10-05 10:00:00", "2026-10-05 11:00:00", None),  # met, on target
        ("C", "Billing", "P1", "2026-10-05 10:00:00", "2026-10-05 11:30:00", None),  # missed
        ("D", "Billing", "P1", "2026-10-05 10:00:00", None, None),                   # missed, no reply
        ("E", "Billing", "P1", "2026-10-05 11:30:00", None, None),                   # not due yet
    ], columns=["ticket_id", "team", "priority", "opened_at", "first_response_at", "closed_at"])
    con = bd.load_db(rows, as_of="2026-10-05 12:00:00")
    due, met = con.execute(
        "SELECT SUM(is_due), SUM(CASE WHEN met_target = 1 THEN 1 ELSE 0 END) "
        "FROM v_ticket_sla WHERE is_due = 1").fetchone()
    assert (due, met) == (4, 2)
    assert con.execute("SELECT met_target FROM v_ticket_sla WHERE ticket_id = 'E'").fetchone()[0] is None


def test_dashboard_html_has_definitions_link_and_date(tmp_path):
    out = bd.write_dashboard(bd.build_db(), out=tmp_path / "dashboard.html")
    text = out.read_text(encoding="utf-8")
    assert "docs/metric_definitions.md" in text
    assert "Reporting date: 2026-10-26" in text
    assert "Open backlog" in text
