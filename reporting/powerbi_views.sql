-- Power BI-ready reporting views. Written against the PostgreSQL/orm_models.py
-- target schema (see docs/assumptions_and_decision_log.md for verification
-- status). Designed only in this session - not executed against a live
-- Postgres instance. Review row-level security / masking needs (per the
-- 9-role security matrix in HS_Nomination_Automation_Data_Architecture.docx)
-- before exposing these views to a BI dataset with mixed-role access.

-- Executive Dashboard --------------------------------------------------
CREATE OR REPLACE VIEW vw_executive_dashboard AS
SELECT
    p.id                                        AS program_id,
    p.name                                      AS program_name,
    p.status                                    AS program_status,
    COUNT(DISTINCT b.id)                        AS active_batches,
    COUNT(DISTINCT n.id)                        AS total_nominations,
    COUNT(DISTINCT n.id) FILTER (WHERE n.status = 'Confirmed') AS registrations,
    ROUND(
        100.0 * COUNT(DISTINCT ed.nomination_id) FILTER (WHERE ed.status = 'Eligible')
        / NULLIF(COUNT(DISTINCT n.id), 0), 2
    )                                            AS eligibility_pct,
    ROUND(
        100.0 * COUNT(DISTINCT n.id) FILTER (WHERE n.status IN ('Submitted','PendingValidation','Eligible','Confirmed'))
        / NULLIF(SUM(DISTINCT b.capacity), 0), 2
    )                                            AS seat_utilization_pct
FROM programs p
LEFT JOIN batches b ON b.program_id = p.id AND b.is_archived = false
LEFT JOIN nominations n ON n.batch_id = b.id AND n.is_archived = false
LEFT JOIN eligibility_decisions ed ON ed.nomination_id = n.id
GROUP BY p.id, p.name, p.status;
-- NOTE: SUM(DISTINCT b.capacity) avoids double counting capacity across
-- multiple nominations per batch; verify against actual physical model
-- before trusting seat_utilization_pct - a batch-level pre-aggregation
-- (CTE grouping by batch first) is safer once real data volumes are known.

-- Operations Dashboard --------------------------------------------------
CREATE OR REPLACE VIEW vw_operations_dashboard AS
SELECT
    n.program_id,
    COUNT(*)                                                     AS invited,
    COUNT(*) FILTER (WHERE n.status = 'Confirmed')               AS registered,
    COUNT(*) FILTER (WHERE n.status = 'PendingValidation')       AS pending_validation,
    COUNT(*) FILTER (WHERE n.status = 'Eligible')                AS eligible,
    COUNT(*) FILTER (WHERE n.status = 'Rejected')                AS rejected,
    COUNT(*) FILTER (WHERE n.status = 'Waitlisted')               AS waitlisted,
    COUNT(*) FILTER (WHERE n.status = 'Confirmed')                AS confirmed
FROM nominations n
WHERE n.is_archived = false
GROUP BY n.program_id;

-- Validation Dashboard --------------------------------------------------
CREATE OR REPLACE VIEW vw_validation_dashboard AS
SELECT
    er.rule_source,
    COUNT(*) FILTER (WHERE er.result = 'Pending')          AS pending_count,
    COUNT(*) FILTER (WHERE er.result = 'DataUnavailable')   AS data_unavailable_count,
    COUNT(*) FILTER (WHERE er.result = 'Fail')              AS fail_count,
    ROUND(AVG(EXTRACT(EPOCH FROM (now() - er.evaluated_at)) / 86400.0), 1) AS avg_age_days
FROM eligibility_results er
WHERE er.result IN ('Pending', 'DataUnavailable', 'Fail')
GROUP BY er.rule_source;

-- Top missing prerequisites (separate query - not a fixed view since "top N" is a UI parameter)
-- SELECT rule_name, COUNT(*) missing_count FROM eligibility_results
-- WHERE result IN ('Fail','DataUnavailable') GROUP BY rule_name ORDER BY missing_count DESC LIMIT 10;

-- Communication Dashboard --------------------------------------------------
CREATE OR REPLACE VIEW vw_communication_dashboard AS
SELECT
    cl.comm_type,
    COUNT(*) FILTER (WHERE cl.status = 'Sent')       AS sent_count,
    COUNT(*) FILTER (WHERE cl.status = 'DryRun')      AS dry_run_count,
    COUNT(*) FILTER (WHERE cl.status = 'Failed')      AS failed_count,
    COUNT(*) FILTER (WHERE cl.status = 'Suppressed')  AS suppressed_count,
    SUM(cl.retry_count)                               AS total_retries,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE cl.status = 'Sent')
        / NULLIF(COUNT(*) FILTER (WHERE cl.status IN ('Sent','Failed')), 0), 2
    )                                                  AS send_success_rate_pct
FROM communication_log cl
GROUP BY cl.comm_type;
