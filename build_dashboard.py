"""Builds the stakeholder dashboard as one self-contained HTML file.

Loads data/tickets.csv into SQLite, runs the metric views in sql/views.sql, and writes
dashboard.html. Run it again whenever the data changes. Made-up data.
"""

import html
import sqlite3
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
DATA = HERE / "data" / "tickets.csv"
VIEWS = HERE / "sql" / "views.sql"
OUT = HERE / "dashboard.html"
AS_OF = "2026-10-26 00:00:00"  # end of the 12 simulated weeks; change it with the data

CSS = """
body{font-family:system-ui,sans-serif;margin:0;padding:16px;color:#1f2937;background:#f9fafb;line-height:1.4}
h1{font-size:1.5rem;margin:0 0 4px} h2{font-size:1.1rem;margin:24px 0 8px}
.note{color:#4b5563;font-size:.9rem}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.tile{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:12px}
.tile .v{font-size:1.6rem;font-weight:600}
.tile .l{font-size:.85rem;color:#4b5563}
.row{display:grid;grid-template-columns:110px 1fr 120px;align-items:center;gap:8px;margin:6px 0}
.track{background:#e5e7eb;border-radius:4px;height:14px;overflow:hidden}
.fill{background:#2563eb;height:100%}
table{border-collapse:collapse;width:100%;background:#fff;font-size:.9rem;display:block;overflow-x:auto}
th,td{border-bottom:1px solid #e5e7eb;padding:6px 8px;text-align:left;white-space:nowrap}
.up{color:#15803d}.down{color:#b91c1c}
details{margin-top:12px}
a{color:#1d4ed8}
"""


def load_db(df, as_of=AS_OF):
    """Loads ticket rows (missing values as None or NaN) and sets the reporting date."""
    con = sqlite3.connect(":memory:")
    df.to_sql("tickets", con, index=False)
    con.executescript(VIEWS.read_text())
    con.execute("INSERT INTO as_of (as_of_ts) VALUES (?)", (as_of,))
    return con


def build_db(csv_path=DATA, as_of=AS_OF):
    return load_db(pd.read_csv(csv_path, dtype=str), as_of)


def fetch(con):
    overall_due, overall_met = con.execute(
        "SELECT SUM(is_due), SUM(CASE WHEN met_target = 1 THEN 1 ELSE 0 END) "
        "FROM v_ticket_sla WHERE is_due = 1").fetchone()
    return {
        "overall": (int(overall_due or 0), int(overall_met or 0)),
        "by_team": pd.read_sql(
            "SELECT team, SUM(is_due) AS due, "
            "SUM(CASE WHEN met_target = 1 THEN 1 ELSE 0 END) AS met "
            "FROM v_ticket_sla WHERE is_due = 1 GROUP BY team ORDER BY team", con),
        "weekly": pd.read_sql(
            "SELECT team, week_start, due_tickets, attainment_pct FROM v_weekly_attainment", con),
        "backlog": pd.read_sql(
            "SELECT week_start, week_end, open_tickets FROM v_weekly_backlog ORDER BY week_start", con),
        "tickets": pd.read_sql(
            "SELECT ticket_id, team, priority, opened_at, first_response_at, response_hours, "
            "target_hours, is_due, met_target FROM v_ticket_sla ORDER BY opened_at, ticket_id", con),
    }


def pct(met, due):
    return None if not due else 100.0 * met / due


def fmt_pct(x):
    return "–" if x is None or pd.isna(x) else f"{x:.1f}%"


def esc(x):
    return html.escape(str(x))


def bar_row(label, width, text):
    w = 0.0 if width is None or pd.isna(width) else max(0.0, min(100.0, width))
    return (f'<div class="row"><div>{esc(label)}</div>'
            f'<div class="track"><div class="fill" style="width:{w:.1f}%"></div></div>'
            f'<div>{esc(text)}</div></div>')


def last_weeks(weekly, n=4):
    weeks = sorted(weekly.week_start.unique())[-n:]
    table = (weekly[weekly.week_start.isin(weeks)]
             .pivot(index="team", columns="week_start", values="attainment_pct")
             .reindex(columns=weeks))
    return weeks, table


def render(data, as_of=AS_OF):
    due, met = data["overall"]
    by_team = data["by_team"]
    weeks, table = last_weeks(data["weekly"])
    backlog_all = data["backlog"]
    backlog = backlog_all.tail(8)
    tickets = data["tickets"]

    latest_open = int(backlog_all.open_tickets.iloc[-1])
    if len(backlog_all) >= 5:
        delta = latest_open - int(backlog_all.open_tickets.iloc[-5])
        backlog_note = f"{delta:+d} vs 4 weeks earlier"
    else:
        backlog_note = ""
    no_response = int(((tickets.is_due == 1) & tickets.first_response_at.isna()).sum())

    team_html = "".join(
        bar_row(r.team, pct(r.met, r.due), f"{fmt_pct(pct(r.met, r.due))} ({int(r.met)}/{int(r.due)})")
        for r in by_team.itertuples())

    peak = max(int(v) for v in backlog.open_tickets) or 1
    backlog_html = "".join(
        bar_row(r.week_start, 100.0 * r.open_tickets / peak, str(int(r.open_tickets)))
        for r in backlog.itertuples())

    week_head = "".join(f"<th>Week of {esc(w)}</th>" for w in weeks)
    week_body = ""
    for team in table.index:
        cells = "".join(f"<td>{fmt_pct(table.loc[team, w])}</td>" for w in weeks)
        vals = table.loc[team].dropna()
        if len(vals) >= 2:
            change = vals.iloc[-1] - vals.iloc[0]
            cls = "up" if change >= 0 else "down"
            change_html = f'<span class="{cls}">{change:+.1f} pts</span>'
        else:
            change_html = "–"
        week_body += f"<tr><td>{esc(team)}</td>{cells}<td>{change_html}</td></tr>"

    rows = []
    for r in tickets.itertuples():
        if r.is_due != 1:
            outcome = "Not due yet"
        elif r.met_target == 1:
            outcome = "Met"
        else:
            outcome = "Missed"
        first = r.first_response_at if pd.notna(r.first_response_at) else "no response yet"
        hours = "" if pd.isna(r.response_hours) else f"{r.response_hours:.2f}"
        rows.append(f"<tr><td>{esc(r.ticket_id)}</td><td>{esc(r.team)}</td><td>{esc(r.priority)}</td>"
                    f"<td>{esc(r.opened_at)}</td><td>{esc(first)}</td><td>{hours}</td>"
                    f"<td>{int(r.target_hours)}</td><td>{outcome}</td></tr>")
    ticket_rows = "".join(rows)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Support first-response dashboard</title>
<style>{CSS}</style></head><body>
<h1>Support queue: first-response targets</h1>
<p class="note">Made-up data for a portfolio project. Reporting date: {esc(as_of[:10])}.
Every number is defined in <a href="docs/metric_definitions.md">docs/metric_definitions.md</a>.</p>
<div class="tiles">
 <div class="tile"><div class="l">First-response attainment, all teams</div>
  <div class="v">{fmt_pct(pct(met, due))}</div>
  <div class="l">{met} of {due} due tickets met target</div></div>
 <div class="tile"><div class="l">Open backlog, latest week end</div>
  <div class="v">{latest_open}</div><div class="l">{esc(backlog_note)}</div></div>
 <div class="tile"><div class="l">Due tickets with no response yet</div>
  <div class="v">{no_response}</div><div class="l">counted as missed</div></div>
</div>
<h2>Attainment by team, all weeks</h2>
{team_html}
<h2>Last 4 weeks by team</h2>
<table><tr><th>Team</th>{week_head}<th>Change over 4 weeks</th></tr>{week_body}</table>
<p class="note">The latest week is partial: tickets not yet due are left out, so its figure can still move.</p>
<h2>Open backlog, last 8 weeks</h2>
{backlog_html}
<details><summary>Ticket detail ({len(tickets)} tickets)</summary>
<table><tr><th>Ticket</th><th>Team</th><th>Priority</th><th>Opened</th><th>First response</th>
<th>Hours to respond</th><th>Target (h)</th><th>Outcome</th></tr>{ticket_rows}</table></details>
</body></html>
"""


def write_dashboard(con, out=OUT, as_of=AS_OF):
    out = Path(out)
    out.write_text(render(fetch(con), as_of), encoding="utf-8")
    return out


if __name__ == "__main__":
    print(f"wrote {write_dashboard(build_db(), as_of=AS_OF)}")
