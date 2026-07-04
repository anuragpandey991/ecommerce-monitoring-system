import pandas as pd
from ingestion.db import get_connection

LOOKBACK_WEEKS = 4     # how many past same-hour windows to use as baseline
Z_THRESHOLD    = 2.5   # slightly more sensitive than realtime (2.5σ vs 3.0σ)
MIN_BASELINE   = 3     # need at least this many historical points to compare

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

    df["window_start"] = pd.to_datetime(df["window_start"])
    df["hour_of_day"]  = df["window_start"].dt.hour
    df["day_of_week"]  = df["window_start"].dt.dayofweek  # 0=Mon … 6=Sun
    return df


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    alerts = []

    for region, reg_df in df.groupby("region"):
        reg_df = reg_df.sort_values("window_start").reset_index(drop=True)

        for metric in METRICS:
            if metric not in reg_df.columns:
                continue

            for idx, row in reg_df.iterrows():
                current_val  = row[metric]
                current_hour = row["hour_of_day"]
                current_dow  = row["day_of_week"]
                current_ts   = row["window_start"]

                if pd.isna(current_val):
                    continue

                # Seasonal baseline: same hour-of-day + same day-of-week,
                # from past LOOKBACK_WEEKS weeks only (exclude current window)
                baseline_mask = (
                    (reg_df["hour_of_day"] == current_hour)  &
                    (reg_df["day_of_week"] == current_dow)   &
                    (reg_df["window_start"] < current_ts)    &
                    (reg_df["window_start"] >= current_ts - pd.Timedelta(weeks=LOOKBACK_WEEKS))
                )
                baseline = reg_df.loc[baseline_mask, metric].dropna()

                if len(baseline) < MIN_BASELINE:
                    # not enough seasonal history — skip
                    continue

                baseline_mean = baseline.mean()
                baseline_std  = baseline.std()

                if baseline_std == 0:
                    continue

                z = (current_val - baseline_mean) / baseline_std

                if abs(z) > Z_THRESHOLD:
                    alerts.append({
                        "alert_time":    current_ts,
                        "region":        region,
                        "metric":        metric,
                        "metric_value":  current_val,
                        "baseline_mean": baseline_mean,
                        "baseline_std":  baseline_std,
                        "z_score":       z,
                        "detector_type": "seasonal",
                        "severity":      _severity(z),
                    })

    return pd.DataFrame(alerts)


def _severity(z: float) -> str:
    az = abs(z)
    if az > 5:
        return "HIGH"
    if az > 3.5:
        return "MEDIUM"
    return "LOW"


def save_alerts(alerts: pd.DataFrame) -> None:
    if alerts.empty:
        return

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for _, row in alerts.iterrows():
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
        conn.commit()
    finally:
        conn.close()


def main():
    df = load_data()

    if df.empty:
        print("No feature data found — skipping seasonal detection")
        return

    alerts = detect_anomalies(df)

    if not alerts.empty:
        print(f"Detected {len(alerts)} seasonal anomalies:")
        print(alerts[["region", "metric", "metric_value", "z_score", "severity"]])
        save_alerts(alerts)
    else:
        print("No seasonal anomalies detected")


if __name__ == "__main__":
    main()