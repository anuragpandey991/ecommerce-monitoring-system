from ingestion.db import get_connection


CREATE_TABLES = [

"""
CREATE TABLE IF NOT EXISTS clean_events (
    event_id UUID PRIMARY KEY,
    event_type TEXT,
    event_time TIMESTAMP,
    user_id INT,
    product_id INT,
    order_id TEXT,
    price NUMERIC,
    currency TEXT,
    payment_method TEXT,
    latency_ms INT,
    failure_reason TEXT,
    region TEXT
);
""",

"""
CREATE TABLE IF NOT EXISTS agg_funnel_1m (
    window_start TIMESTAMP,
    region TEXT,
    views INT,
    carts INT,
    checkout_starts INT,
    successes INT,
    failures INT,
    conversion_rate NUMERIC,
    PRIMARY KEY (window_start, region)
);
""",

"""
CREATE TABLE IF NOT EXISTS agg_payment_1m (
    window_start TIMESTAMP,
    region TEXT,
    payment_method TEXT,
    avg_latency_ms NUMERIC,
    timeout_count INT,
    failure_count INT,
    PRIMARY KEY (window_start, region, payment_method)
);
""",

"""
CREATE TABLE IF NOT EXISTS agg_traffic_1m (
    window_start TIMESTAMP,
    region TEXT,
    unique_users INT,
    total_events INT,
    PRIMARY KEY (window_start, region)
);
""",

"""
CREATE TABLE IF NOT EXISTS agg_failures_1m (
    window_start TIMESTAMP,
    region TEXT,
    failure_reason TEXT,
    failure_count INT,
    PRIMARY KEY (window_start, region, failure_reason)
);
""",

"""
CREATE TABLE IF NOT EXISTS ml_features_1m (
    window_start TIMESTAMP,
    region TEXT,
    views INT,
    carts INT,
    checkout_starts INT,
    successes INT,
    failures INT,
    conversion_rate NUMERIC,
    avg_latency_ms NUMERIC,
    timeout_count INT,
    total_events INT,
    unique_users INT,
    failure_count INT,
    PRIMARY KEY (window_start, region)
);
"""

]


def create_tables():

    conn = get_connection()

    try:
        with conn.cursor() as cur:

            for sql in CREATE_TABLES:
                cur.execute(sql)

        conn.commit()
        print("All tables created successfully")

    finally:
        conn.close()