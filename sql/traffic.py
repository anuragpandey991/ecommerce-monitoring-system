TRAFFIC_SQL = """
INSERT INTO agg_traffic_1m (
    window_start,
    region,
    unique_users,
    total_events
)
SELECT
    date_trunc('minute', event_time),
    region,
    COUNT(DISTINCT user_id),
    COUNT(*)
FROM clean_events
GROUP BY date_trunc('minute', event_time), region
ON CONFLICT (window_start, region) DO NOTHING;
"""