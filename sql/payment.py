PAYMENT_SQL = """
INSERT INTO agg_payment_1m (
    window_start,
    region,
    payment_method,
    avg_latency_ms,
    timeout_count,
    failure_count
)
SELECT
    date_trunc('minute', event_time),
    region,
    payment_method,
    AVG(latency_ms) FILTER (WHERE latency_ms IS NOT NULL),
    COUNT(*) FILTER (WHERE failure_reason = 'TIMEOUT'),
    COUNT(*) FILTER (WHERE event_type = 'checkout_failed')
FROM clean_events
WHERE payment_method IS NOT NULL
GROUP BY date_trunc('minute', event_time), region, payment_method
ON CONFLICT (window_start, region, payment_method) DO NOTHING;
"""