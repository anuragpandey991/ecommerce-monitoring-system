FAILURE_SQL = """
INSERT INTO agg_failures_1m (
    window_start,
    region,
    failure_reason,
    failure_count
)
SELECT
    date_trunc('minute', event_time),
    region,
    failure_reason,
    COUNT(*)
FROM clean_events
WHERE failure_reason IS NOT NULL
GROUP BY date_trunc('minute', event_time), region, failure_reason
ON CONFLICT (window_start, region, failure_reason) DO NOTHING;
"""