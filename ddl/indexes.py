from ingestion.db import get_connection


INDEX_QUERIES = [
"CREATE INDEX IF NOT EXISTS idx_funnel_window ON agg_funnel_1m(window_start);",
"CREATE INDEX IF NOT EXISTS idx_funnel_region ON agg_funnel_1m(region);",

"CREATE INDEX IF NOT EXISTS idx_payment_window ON agg_payment_1m(window_start);",
"CREATE INDEX IF NOT EXISTS idx_payment_region ON agg_payment_1m(region);",

"CREATE INDEX IF NOT EXISTS idx_traffic_window ON agg_traffic_1m(window_start);",
"CREATE INDEX IF NOT EXISTS idx_traffic_region ON agg_traffic_1m(region);",

"CREATE INDEX IF NOT EXISTS idx_failure_window ON agg_failures_1m(window_start);",
"CREATE INDEX IF NOT EXISTS idx_failure_region ON agg_failures_1m(region);",

"CREATE INDEX IF NOT EXISTS idx_clean_event_time ON clean_events(event_time);",
"CREATE INDEX IF NOT EXISTS idx_clean_region ON clean_events(region);",
"CREATE INDEX IF NOT EXISTS idx_clean_event_type ON clean_events(event_type);"
]


def create_indexes():

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            for sql in INDEX_QUERIES:
                cur.execute(sql)

        conn.commit()
        print("Gold layer indexes created")

    finally:
        conn.close()