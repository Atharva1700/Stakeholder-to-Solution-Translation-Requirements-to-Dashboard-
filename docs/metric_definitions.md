# Metric definitions

Plain-language definitions for every number on the dashboard. The data is made up.

**Ticket.** One support request, with the time it was opened, the time of the first reply
from an agent (if any), and the time it was closed (if it has been).

**Priority and target.** Each ticket has a priority: P1, P2 or P3. The first-response
target is the time allowed from opening to the first reply:

| Priority | Target |
|---|---|
| P1 | 1 hour |
| P2 | 4 hours |
| P3 | 24 hours |

**Reporting date.** The date the numbers are measured up to. Nothing after it is counted.
The dashboard shows it at the top.

**Due.** A ticket is due once its target time has passed by the reporting date. A ticket
still inside its target window is *not due yet* and is left out of every attainment
number. It is not counted as a miss.

**Met target.** A due ticket is met if its first reply came within the target, measured
from opening. A reply exactly at the target counts as met.

**No response yet.** A due ticket with no reply. It counts as missed.

**First-response attainment %.** Met tickets divided by due tickets, as a percentage.
Shown overall and for each team.

**Week.** Monday to Sunday. Weekly attainment groups tickets by the week they were opened.
The latest week is usually partial: tickets opened in it that are not yet due are left out,
so its percentage can still change.

**Change over 4 weeks (points).** The latest week's attainment minus the attainment of the
earliest of the last four weeks, in percentage points. A positive change means the team is
meeting targets more often.

**Open backlog at week end.** The number of tickets opened before the end of that week and
not closed by the end of it. A ticket closed after the week ended is still counted as open
for that week.

**Team.** The support team the ticket is assigned to: Billing, Technical or Accounts.

**Out of scope.** Resolution time and customer satisfaction are not on this dashboard.
