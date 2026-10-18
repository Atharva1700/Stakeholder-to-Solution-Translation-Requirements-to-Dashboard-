-- Metric layer. Each view is one requirement from docs/requirements.md.
-- Definitions are also written in plain language in docs/metric_definitions.md.
-- Timestamps are stored as 'YYYY-MM-DD HH:MM:SS' text. Comparisons use whole seconds
-- (strftime '%s') so a response exactly at the target is not lost to float rounding.

CREATE TABLE IF NOT EXISTS sla_targets (priority TEXT PRIMARY KEY, target_hours REAL);
DELETE FROM sla_targets;
INSERT INTO sla_targets VALUES ('P1', 1), ('P2', 4), ('P3', 24);

-- The reporting date. Nothing is measured past it. Set once per data refresh.
CREATE TABLE IF NOT EXISTS as_of (as_of_ts TEXT);
DELETE FROM as_of;

-- R1, R5: one row per ticket, with its SLA outcome.
-- is_due = the target time has passed as of the reporting date.
-- met_target = first response came within target. NULL until the ticket is due.
DROP VIEW IF EXISTS v_ticket_sla;
CREATE VIEW v_ticket_sla AS
SELECT t.ticket_id,
       t.team,
       t.priority,
       t.opened_at,
       t.first_response_at,
       s.target_hours,
       CASE WHEN t.first_response_at IS NULL THEN NULL
            ELSE ROUND((CAST(strftime('%s', t.first_response_at) AS INTEGER)
                      - CAST(strftime('%s', t.opened_at) AS INTEGER)) / 3600.0, 2)
       END AS response_hours,
       CASE WHEN CAST(strftime('%s', t.opened_at) AS INTEGER) + s.target_hours * 3600
                 <= CAST(strftime('%s', a.as_of_ts) AS INTEGER)
            THEN 1 ELSE 0 END AS is_due,
       CASE WHEN CAST(strftime('%s', t.opened_at) AS INTEGER) + s.target_hours * 3600
                 > CAST(strftime('%s', a.as_of_ts) AS INTEGER)
            THEN NULL
            WHEN t.first_response_at IS NOT NULL
             AND CAST(strftime('%s', t.first_response_at) AS INTEGER)
                 - CAST(strftime('%s', t.opened_at) AS INTEGER) <= s.target_hours * 3600
            THEN 1 ELSE 0 END AS met_target
FROM tickets t
JOIN sla_targets s ON s.priority = t.priority
CROSS JOIN as_of a;

-- R2: weekly first-response attainment by team. Weeks run Monday to Sunday, by open date.
-- attainment_pct = met / due. Tickets not yet due are left out, not counted as missed.
DROP VIEW IF EXISTS v_weekly_attainment;
CREATE VIEW v_weekly_attainment AS
SELECT team,
       date(opened_at, '-' || ((strftime('%w', opened_at) + 6) % 7) || ' days') AS week_start,
       SUM(is_due) AS due_tickets,
       SUM(CASE WHEN met_target = 1 THEN 1 ELSE 0 END) AS met_tickets,
       ROUND(100.0 * SUM(CASE WHEN met_target = 1 THEN 1 ELSE 0 END)
             / NULLIF(SUM(is_due), 0), 1) AS attainment_pct
FROM v_ticket_sla
WHERE is_due = 1
GROUP BY team, week_start;

-- R3: open backlog at the end of each complete week (Monday to Sunday).
-- A ticket is open at a week end if it was opened before that moment and not closed by it.
DROP VIEW IF EXISTS v_weekly_backlog;
CREATE VIEW v_weekly_backlog AS
WITH RECURSIVE weeks(week_start) AS (
    SELECT date(MIN(opened_at), '-' || ((strftime('%w', MIN(opened_at)) + 6) % 7) || ' days')
    FROM tickets
    UNION ALL
    SELECT date(week_start, '+7 days') FROM weeks
    WHERE date(week_start, '+14 days') <= date((SELECT as_of_ts FROM as_of))
)
SELECT w.week_start,
       datetime(w.week_start, '+7 days') AS week_end,
       (SELECT COUNT(*) FROM tickets t
         WHERE t.opened_at < datetime(w.week_start, '+7 days')
           AND (t.closed_at IS NULL OR t.closed_at >= datetime(w.week_start, '+7 days'))
       ) AS open_tickets
FROM weeks w;
