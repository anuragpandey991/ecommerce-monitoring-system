FUNNEL_SQL = """
INSERT INTO agg_funnel_1m (
    window_start,
    region,
    views,
    carts,
    checkout_starts,
    successes,
    failures,
    conversion_rate,
    cart_rate,
    checkout_start_rate,
    success_rate
)

SELECT
    date_trunc('minute', event_time) AS window_start,
    region,

    COUNT(*) FILTER (WHERE event_type = 'product_view') AS views,
    COUNT(*) FILTER (WHERE event_type = 'add_to_cart') AS carts,
    COUNT(*) FILTER (WHERE event_type = 'checkout_start') AS checkout_starts,
    COUNT(*) FILTER (WHERE event_type = 'checkout_success') AS successes,
    COUNT(*) FILTER (WHERE event_type = 'checkout_failed') AS failures,

    CASE
        WHEN COUNT(*) FILTER (WHERE event_type = 'product_view') = 0
        THEN 0
        ELSE
            COUNT(*) FILTER (WHERE event_type = 'checkout_success')::NUMERIC
            /
            COUNT(*) FILTER (WHERE event_type = 'product_view')
    END AS conversion_rate,

    CASE
        WHEN COUNT(*) FILTER (WHERE event_type = 'product_view') = 0
        THEN 0
        ELSE
            COUNT(*) FILTER (WHERE event_type = 'add_to_cart')::NUMERIC
            /
            COUNT(*) FILTER (WHERE event_type = 'product_view')
    END AS cart_rate,

    CASE
        WHEN COUNT(*) FILTER (WHERE event_type = 'add_to_cart') = 0
        THEN 0
        ELSE
            COUNT(*) FILTER (WHERE event_type = 'checkout_start')::NUMERIC
            /
            COUNT(*) FILTER (WHERE event_type = 'add_to_cart')
    END AS checkout_start_rate,

    CASE
        WHEN COUNT(*) FILTER (WHERE event_type = 'checkout_start') = 0
        THEN 0
        ELSE
            COUNT(*) FILTER (WHERE event_type = 'checkout_success')::NUMERIC
            /
            COUNT(*) FILTER (WHERE event_type = 'checkout_start')
    END AS success_rate

FROM clean_events
GROUP BY
    date_trunc('minute', event_time),
    region

ON CONFLICT (window_start, region)
DO UPDATE SET
    views = EXCLUDED.views,
    carts = EXCLUDED.carts,
    checkout_starts = EXCLUDED.checkout_starts,
    successes = EXCLUDED.successes,
    failures = EXCLUDED.failures,
    conversion_rate = EXCLUDED.conversion_rate,
    cart_rate = EXCLUDED.cart_rate,
    checkout_start_rate = EXCLUDED.checkout_start_rate,
    success_rate = EXCLUDED.success_rate
"""
