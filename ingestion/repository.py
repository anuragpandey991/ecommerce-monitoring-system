from psycopg2.extras import Json
from ingestion.db import get_connection
from ingestion.schemas import EcommerceEvent

INSERT_RAW_EVENT_SQL = """
INSERT INTO raw_events (
    event_id,
    event_type,
    event_time,
    region,
    payload
)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (event_id) DO NOTHING;
"""


def insert_raw_event(event: EcommerceEvent) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                INSERT_RAW_EVENT_SQL,
                (
                    str(event.event_id),                # UUID → string
                    event.event_type.value,
                    event.event_time,
                    event.region,
                    Json(event.model_dump(mode="json")) # JSON-safe
                )
            )
        conn.commit()
    finally:
        conn.close()
