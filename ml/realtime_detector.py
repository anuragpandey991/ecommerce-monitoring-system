import pandas as pd
from ingestion.db import get_connection

WINDOW = 30        # rolling window in minutes (rows)
Z_THRESHOLD = 3.0  # sigma threshold for anomaly

QUERY = """
SELECT *
FROM ml_features_1m
ORDER BY region, window_start
"""

METRICS = [
    "views",
    "cart_rate",
    "checkout_start_rate",
    "success_rate",
    "conversion_rate",
    "avg_latency_ms",
    "total_events",
    "unique_users",
    "failure_count",
]


def load_data() -> pd.DataFrame:
    conn = get_connection()
    try:
        df = pd.read_sql(QUERY, conn)
    finally:
        conn.close()
    return df


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    alerts = []

    # Bug fix #2: group by region so rolling stats are per-region
    for region, group in df.groupby("region"):
        group = group.sort_values("window_start").reset_index(drop=True)

        for metric in METRICS:
            if metric not in group.columns:
                continue

            series = group[metric]

            # Bug fix #3: fully vectorized — no row loop
            rolling_mean = series.rolling(WINDOW, min_periods=5).mean()
            rolling_std  = series.rolling(WINDOW, min_periods=5).std()

            z_scores = (series - rolling_mean) / rolling_std.replace(0, pd.NA)
            anomaly_mask = z_scores.abs() > Z_THRESHOLD

            for idx in group[anomaly_mask].index:
                alerts.append({
                    "alert_time":     group.loc[idx, "window_start"],
                    "region":         region,
                    "metric":         metric,
                    "metric_value":   group.loc[idx, metric],
                    "baseline_mean":  rolling_mean.loc[idx],
                    "baseline_std":   rolling_std.loc[idx],
                    "z_score":        z_scores.loc[idx],
                    "detector_type":  "realtime",   # Bug fix #4: track detector
                    "severity":       _severity(z_scores.loc[idx]),
                })

    return pd.DataFrame(alerts)


def _severity(z: float) -> str:
    az = abs(z)
    if az > 5:
        return "HIGH"
    if az > 4:
        return "MEDIUM"
    return "LOW"


def save_alerts(alerts: pd.DataFrame) -> None:
    if alerts.empty:
        return

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for _, row in alerts.iterrows():
                # Bug fix #5: ON CONFLICT deduplicates by (time, region, metric, detector)
                cur.execute(
                    """
                    INSERT INTO alerts_1m (
                        alert_time, region, metric,
                        metric_value, baseline_mean, baseline_std,
                        severity, detector_type
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (alert_time, region, metric, detector_type)
                    DO NOTHING;
                    """,
                    (
                        row.alert_time,
                        row.region,
                        row.metric,
                        row.metric_value,
                        row.baseline_mean,
                        row.baseline_std,
                        row.severity,
                        row.detector_type,
                    ),
                )
        conn.commit()  # Bug fix #6: commit is inside try, close is in finally
    finally:
        conn.close()


def main():
    df = load_data()

    if df.empty:
        print("No feature data found — skipping detection")
        return

    alerts = detect_anomalies(df)

    if not alerts.empty:
        print(f"Detected {len(alerts)} anomalies:")
        print(alerts[["region", "metric", "metric_value", "z_score", "severity"]])
        save_alerts(alerts)
    else:
        print("No anomalies detected")


if __name__ == "__main__":
    main()