# Requirements, metrics, and sources

Each stakeholder need becomes a requirement with a success measure: a test of whether the
dashboard meets it. Each requirement maps to one metric and one data source.

| Req | Stakeholder need | Success measure | Metric | Source (view) |
|---|---|---|---|---|
| R1 | Are we meeting first-response targets, overall and by team? | Dashboard shows attainment % overall and per team, matching a hand count on the test data | First-response attainment % | `v_ticket_sla` |
| R2 | Which team is falling behind, and is it getting worse? | Per-team attainment for each of the last 4 weeks is shown, with the direction of change | Weekly attainment by team | `v_weekly_attainment` |
| R3 | How big is the open backlog, and is it growing? | Open ticket count at each week end is shown for the last 8 weeks | Open backlog at week end | `v_weekly_backlog` |
| R4 | Can a non-technical reader understand each number? | Every figure on the dashboard has a definition in `metric_definitions.md`, and the definition is linked from the page | Definitions coverage | `docs/metric_definitions.md` |
| R5 | If a number is disputed, can I see how it was counted? | Each ticket behind a metric can be listed, with its response time and whether it met target | Ticket-level detail | `v_ticket_sla` |

## Targets (agreed definitions)

First-response target by priority, in hours from opening to first response:

| Priority | Target (hours) |
|---|---|
| P1 | 1 |
| P2 | 4 |
| P3 | 24 |

These targets are stored in a table (`sla_targets`) so changing a target means changing
one row.

## Out of scope

- Resolution time and customer satisfaction. The request does not ask for them, and the
  data has no satisfaction field.
- Real-time updates. The dashboard is refreshed by running `build_dashboard.py`.
