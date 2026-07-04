CLEAN_SQL = """
INSERT INTO clean_events (
    event_id,
    event_type,
    event_time,
    user_id,
    product_id,
    order_id,
    price,
    currency,
    payment_method,
    latency_ms,
    failure_reason,
    region
)
SELECT
    event_id,
    event_type,
    event_time,
    (payload->>'user_id')::INT,
    (payload->>'product_id')::INT,
    payload->>'order_id',
    (payload->>'price')::NUMERIC,
    payload->>'currency',
    payload->>'payment_method',
    (payload->>'latency_ms')::INT,
    payload->>'failure_reason',
    region
FROM raw_events
ON CONFLICT (event_id) DO NOTHING;
"""