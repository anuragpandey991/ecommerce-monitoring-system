import pandas as pd
from sklearn.ensemble import IsolationForest
from ingestion.db import get_connection


QUERY = """
SELECT *
FROM ml_features_1m
ORDER BY window_start
"""


def load_data():
    conn = get_connection()
    df = pd.read_sql(QUERY, conn)
    conn.close()
    return df


def train_model(df):

    features = df[[
        "conversion_rate",
        "revenue",
        "avg_latency_ms",
        "total_events",
        "failure_count"
    ]].fillna(0)

    model = IsolationForest(
        contamination=0.05,
        random_state=42
    )

    df["anomaly_score"] = model.fit_predict(features)

    return df


def main():

    df = load_data()

    df = train_model(df)

    anomalies = df[df["anomaly_score"] == -1]

    print("Detected anomalies:\n")
    print(anomalies[[
        "window_start",
        "region",
        "conversion_rate",
        "revenue",
        "avg_latency_ms",
        "total_events"
    ]])


if __name__ == "__main__":
    main()
