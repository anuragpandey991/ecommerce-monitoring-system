from ingestion.db import get_connection
from ddl.indexes import create_indexes
from sql.clean_events import CLEAN_SQL
from ddl.tables import CREATE_TABLES

def run():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for query in CREATE_TABLES:
                cur.execute(query)
            cur.execute(CLEAN_SQL)
        conn.commit()
        print("clean_events updated")
    finally:
        conn.close()
    create_indexes()
if __name__ == "__main__":
    run()