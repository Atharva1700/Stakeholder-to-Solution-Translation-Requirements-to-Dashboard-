# Stakeholder-to-Solution: Support First-Response Dashboard

A made-up support request ("are we meeting response targets, which team is falling
behind, how big is the backlog") turned into requirements, metrics, SQL views, a dashboard,
and plain-language definitions.

**The data is simulated.** The Billing slowdown after week 6 is built into the generator
on purpose, so the trend can be shown. It is not a real finding.

## Path from request to dashboard

| Step | File |
|---|---|
| Stakeholder request | `docs/stakeholder_request.md` |
| Requirements, success measures, data sources | `docs/requirements.md` (R1 to R5) |
| Metric definitions for a non-technical reader (R4) | `docs/metric_definitions.md` |
| Metric views (R1, R2, R3, R5) | `sql/views.sql` |
| Dashboard build | `build_dashboard.py` → `dashboard.html` |
| Checks against plain-Python counts | `tests/test_dashboard.py` |

## Results on the simulated data (reporting date 2026-10-26)

| Measure | Result |
|---|---|
| First-response attainment, all teams | 69.3% (1,654 of 2,385 due tickets) |
| Billing | 64.1% (710 of 1,107) |
| Technical | 72.6% (606 of 835) |
| Accounts | 76.3% (338 of 443) |
| Billing, last three weeks (Oct 5 / Oct 12 / Oct 19) | 60.9% / 47.9% / 54.1% |
| Open backlog, week ending Oct 26 | 680 (333 in the week ending Sep 7) |

The latest attainment week (Oct 19) is partial, so its figures can still move.

## Run

```bash
python3 simulate_tickets.py    # regenerate data/tickets.csv (fixed seed)
python3 build_dashboard.py     # writes dashboard.html
python3 -m pytest -q           # 7 tests
```

## Checks

- Overall and per-team attainment match a plain-Python count on the same data.
- The weekly attainment rows add up to the overall due count.
- Backlog matches a plain-Python count for each of the 12 weeks.
- Responses dated after the reporting date are masked, so none can leak in.
- The SLA rules are tested on five hand-built tickets, including a reply exactly on target
  (counted as met) and a ticket still inside its window (not counted).

## Limits and what was not built

- **No Power BI file.** Power BI Desktop is not available here, so there is no `.pbix`.
  `sql/views.sql` is the metric layer a Power BI model would connect to. The HTML dashboard
  shows the same numbers.
- The dashboard is rebuilt by running `build_dashboard.py`. It is not live.
- Resolution time and satisfaction are out of scope (see `docs/requirements.md`).
- The reporting date is fixed in `build_dashboard.py` and must be changed with the data.
- Targets are in the `sla_targets` table, so changing a target means changing one row.
