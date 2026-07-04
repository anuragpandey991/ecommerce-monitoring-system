FEATURE_SQL = """
INSERT INTO ml_features_1m (
    window_start,
    region,
    views,
    carts,
    checkout_starts,
    successes,
    failures,
    conversion_rate,
    avg_latency_ms,
    timeout_count,
    total_events,
    unique_users,
    failure_count,
    cart_rate,
    checkout_start_rate,
    success_rate
)
SELECT
    f.window_start,
    f.region,
    f.views,
    f.carts,
    f.checkout_starts,
    f.successes,
    f.failures,
    f.conversion_rate,
    f.cart_rate,
    f.checkout_start_rate,
    f.success_rate,
    p.avg_latency_ms,
    p.timeout_count,
    t.total_events,
    t.unique_users,
    fl.failure_count
FROM agg_funnel_1m f
LEFT JOIN (
    SELECT window_start, region,
           AVG(avg_latency_ms) AS avg_latency_ms,
           SUM(timeout_count) AS timeout_count
    FROM agg_payment_1m
    GROUP BY window_start, region
) p
ON f.window_start = p.window_start
AND f.region = p.region
LEFT JOIN agg_traffic_1m t
ON f.window_start = t.window_start
AND f.region = t.region
LEFT JOIN (
    SELECT window_start, region,
           SUM(failure_count) AS failure_count
    FROM agg_failures_1m
    GROUP BY window_start, region
) fl
ON f.window_start = fl.window_start
AND f.region = fl.region
ON CONFLICT (window_start, region) DO NOTHING;
"""