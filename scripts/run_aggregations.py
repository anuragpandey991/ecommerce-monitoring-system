from ingestion.db import get_connection

from sql.funnel import FUNNEL_SQL
from sql.payment import PAYMENT_SQL
from sql.traffic import TRAFFIC_SQL
from sql.failures import FAILURE_SQL
from sql.features import FEATURE_SQL

from ddl.indexes import create_indexes


def run():

    conn = get_connection()

    try:
        with conn.cursor() as cur:

            cur.execute(FUNNEL_SQL)
            print("agg_funnel_1m updated")

            cur.execute(PAYMENT_SQL)
            print("agg_payment_1m updated")

            cur.execute(TRAFFIC_SQL)
            print("agg_traffic_1m updated")

            cur.execute(FAILURE_SQL)
            print("agg_failures_1m updated")

            cur.execute(FEATURE_SQL)
            print("ml_features_1m updated")

        conn.commit()

    finally:
        conn.close()

    create_indexes()


if __name__ == "__main__":
    run()

# DROP_FUNNEL_TABLE = """
# DROP TABLE IF EXISTS agg_funnel_1m;
# """
# DROP_PAYMENT_TABLE = """
# DROP TABLE IF EXISTS agg_payment_1m;
# """
# DROP_TRAFFIC_TABLE = """
# DROP TABLE IF EXISTS agg_traffic_1m;
# """
# DROP_FAILURE_TABLE = """
# DROP TABLE IF EXISTS agg_failures_1m;
# """

# CREATE_FUNNEL_TABLE = """
# CREATE TABLE IF NOT EXISTS agg_funnel_1m (
#     window_start TIMESTAMP,
#     region TEXT,
#     views INT,
#     carts INT,
#     checkout_starts INT,
#     successes INT,
#     failures INT,
#     conversion_rate NUMERIC,
#     PRIMARY KEY (window_start, region)
# );
# """

# CREATE_PAYMENT_TABLE = """
# CREATE TABLE IF NOT EXISTS agg_payment_1m (
#     window_start TIMESTAMP,
#     region TEXT,
#     payment_method TEXT,
#     avg_latency_ms NUMERIC,
#     timeout_count INT,
#     failure_count INT,
#     PRIMARY KEY (window_start, region, payment_method)
# );
# """

# CREATE_TRAFFIC_TABLE = """
# CREATE TABLE IF NOT EXISTS agg_traffic_1m (
#     window_start TIMESTAMP,
#     region TEXT,
#     unique_users INT,
#     total_events INT,
#     PRIMARY KEY (window_start, region)
# );
# """

# CREATE_FAILURE_TABLE = """
# CREATE TABLE IF NOT EXISTS agg_failures_1m (
#     window_start TIMESTAMP,
#     region TEXT,
#     failure_reason TEXT,
#     failure_count INT,
#     PRIMARY KEY (window_start, region, failure_reason)
# );
# """

# CREATE_FEATURE_TABLE = """
# CREATE TABLE IF NOT EXISTS agg_failures_1m (
#     window_start TIMESTAMP,
#     region TEXT,
#     failure_reason TEXT,
#     failure_count INT,
#     PRIMARY KEY (window_start, region, failure_reason)
# );
# """
