"""
E-commerce Monitoring Dashboard — Single Page
Run with: streamlit run app.py
"""

import sys, os, time, threading, subprocess
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))
from ingestion.db import get_connection

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ecom Monitor",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── inject sticky topbar + section anchor styles ──────────────────────────────
st.markdown("""
<style>
/* hide default streamlit chrome */
#MainMenu, footer, header {visibility: hidden;}

/* section headings */
.section-heading {
    font-size: 1.1rem;
    font-weight: 600;
    letter-spacing: .04em;
    color: #a5b4fc;
    padding: 6px 0 2px;
    border-bottom: 1px solid #252a3a;
    margin-bottom: 12px;
}

/* severity badges */
.badge-HIGH   { background:#f87171; color:#fff; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }
.badge-MEDIUM { background:#fbbf24; color:#000; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }
.badge-LOW    { background:#60a5fa; color:#fff; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }

/* pipeline log box */
.log-box {
    background: #0c0e14;
    border: 1px solid #252a3a;
    border-radius: 8px;
    padding: 12px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: #94a3b8;
    max-height: 200px;
    overflow-y: auto;
}

/* section divider */
.sec-divider {
    border: none;
    border-top: 1px solid #252a3a;
    margin: 28px 0 24px;
}

/* anchor jump links */
.jump-nav {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 18px;
}
.jump-nav a {
    background: #1a1e2e;
    border: 1px solid #252a3a;
    color: #a5b4fc !important;
    padding: 5px 14px;
    border-radius: 6px;
    font-size: 12px;
    text-decoration: none !important;
}
.jump-nav a:hover { border-color: #6366f1; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
def _init(key, val):
    if key not in st.session_state:
        st.session_state[key] = val

_init("auto_refresh",        True)
_init("refresh_interval",    15)
_init("last_refresh",        datetime.now())
_init("generator_running",   False)
_init("generator_scenario",  "normal")
_init("generator_interval",  60)
_init("generator_thread",    None)
_init("pipeline_log",        [])

# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADERS  (10-second cache)
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=10)
def load_funnel():
    conn = get_connection()
    try:    return pd.read_sql("SELECT * FROM agg_funnel_1m ORDER BY window_start DESC LIMIT 120", conn)
    finally: conn.close()

@st.cache_data(ttl=10)
def load_traffic():
    conn = get_connection()
    try:    return pd.read_sql("SELECT * FROM agg_traffic_1m ORDER BY window_start DESC LIMIT 120", conn)
    finally: conn.close()

@st.cache_data(ttl=10)
def load_payment():
    conn = get_connection()
    try:    return pd.read_sql("SELECT * FROM agg_payment_1m ORDER BY window_start DESC LIMIT 120", conn)
    finally: conn.close()

@st.cache_data(ttl=10)
def load_failures():
    conn = get_connection()
    try:    return pd.read_sql("SELECT * FROM agg_failures_1m ORDER BY window_start DESC LIMIT 120", conn)
    finally: conn.close()

@st.cache_data(ttl=10)
def load_alerts():
    conn = get_connection()
    try:    return pd.read_sql("SELECT * FROM alerts_1m ORDER BY alert_time DESC LIMIT 200", conn)
    finally: conn.close()

@st.cache_data(ttl=10)
def load_features():
    conn = get_connection()
    try:    return pd.read_sql("SELECT * FROM ml_features_1m ORDER BY region, window_start", conn)
    finally: conn.close()

@st.cache_data(ttl=10)
def load_raw_count():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM raw_events")
            return cur.fetchone()[0]
    finally: conn.close()

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
REGION_COLORS = {
    "IN-NORTH": "#60a5fa", "IN-SOUTH": "#a78bfa",
    "IN-WEST":  "#f87171", "IN-EAST":  "#22d3a0",
}
SEV_COLOR = {"HIGH": "#f87171", "MEDIUM": "#fbbf24", "LOW": "#60a5fa"}
PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#e2e8f0",
    font_size=12,
    margin=dict(l=0, r=0, t=32, b=0),
    legend=dict(bgcolor="rgba(0,0,0,0)", font_size=11),
    xaxis=dict(gridcolor="#252a3a", showgrid=True, zeroline=False),
    yaxis=dict(gridcolor="#252a3a", showgrid=True, zeroline=False),
)

SCENARIO_LABELS = {
    "normal":         "🟢 Normal traffic",
    "funnel_anomaly": "📉 Funnel anomaly",
    "region_outage":  "🔴 Region outage (IN-WEST)",
    "payment_outage": "💳 UPI payment failure",
    "traffic_spike":  "📈 Traffic spike",
}

# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _generator_loop(scenario, interval):
    from scripts.generate_events import run_scenario
    while st.session_state.generator_running:
        run_scenario(scenario, seconds=interval)
        time.sleep(1)

def start_generator(scenario, interval):
    if st.session_state.generator_running:
        return
    st.session_state.generator_running  = True
    st.session_state.generator_scenario = scenario
    st.session_state.generator_interval = interval
    t = threading.Thread(target=_generator_loop, args=(scenario, interval), daemon=True)
    t.start()
    st.session_state.generator_thread = t

def stop_generator():
    st.session_state.generator_running = False

def _log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.pipeline_log.append(f"[{ts}]  {msg}")
    st.session_state.pipeline_log = st.session_state.pipeline_log[-40:]

def run_pipeline_step(label, module):
    result = subprocess.run(
        [sys.executable, "-m", module],
        capture_output=True, text=True,
        cwd=os.path.dirname(__file__),
    )
    out = result.stdout.strip() or result.stderr.strip() or "done"
    _log(f"{label}: {out}")

def run_detectors():
    try:
        from ml.realtime_detector import (
            load_data as rt_load, detect_anomalies as rt_detect, save_alerts as rt_save
        )
        from ml.seasonal_detector import (
            load_data as s_load, detect_anomalies as s_detect, save_alerts as s_save
        )
        rt_df = rt_load(); rt_a = rt_detect(rt_df); rt_save(rt_a)
        _log(f"Realtime detector: {len(rt_a)} new alerts")
        s_df  = s_load();  s_a  = s_detect(s_df);   s_save(s_a)
        _log(f"Seasonal detector: {len(s_a)} new alerts")
    except Exception as e:
        _log(f"Detector error: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# TOP BAR  (refresh controls + status pills)
# ══════════════════════════════════════════════════════════════════════════════
try:
    raw_count = load_raw_count()
    db_ok     = True
except Exception:
    raw_count = 0
    db_ok     = False

top_l, top_m, top_r = st.columns([3, 4, 3])

with top_l:
    st.markdown(
        f"### 📡 Ecom Monitor &nbsp;"
        f"<span style='font-size:13px;color:#64748b'>{'🟢 DB connected' if db_ok else '🔴 DB error'} "
        f"· raw_events: {raw_count:,}</span>",
        unsafe_allow_html=True,
    )

with top_m:
    # jump nav
    st.markdown("""
    <div class='jump-nav'>
      <a href='#live-dashboard'>📊 Dashboard</a>
      <a href='#alerts-panel'>🚨 Alerts</a>
      <a href='#pipeline-control'>🔧 Pipeline</a>
      <a href='#region-payment-drilldown'>🌍 Drilldown</a>
    </div>
    """, unsafe_allow_html=True)

with top_r:
    rc1, rc2, rc3 = st.columns([2, 2, 1])
    with rc1:
        st.session_state.auto_refresh = st.toggle(
            "Auto-refresh", value=st.session_state.auto_refresh
        )
    with rc2:
        st.session_state.refresh_interval = st.select_slider(
            "Every", options=[5, 10, 15, 30, 60],
            value=st.session_state.refresh_interval,
            disabled=not st.session_state.auto_refresh,
            label_visibility="collapsed",
        )
        if st.session_state.auto_refresh:
            elapsed   = (datetime.now() - st.session_state.last_refresh).total_seconds()
            remaining = max(0, int(st.session_state.refresh_interval - elapsed))
            st.caption(f"Next refresh in {remaining}s")
        else:
            st.caption("Auto-refresh paused")
    with rc3:
        if st.button("🔄", help="Refresh now"):
            st.cache_data.clear()
            st.session_state.last_refresh = datetime.now()
            st.rerun()

    gen_col, _ = st.columns([3, 1])
    gen_status = (
        f"🟢 Generator running · **{st.session_state.generator_scenario}** "
        f"· {st.session_state.generator_interval}s cycle"
        if st.session_state.generator_running
        else "⚫ Generator stopped"
    )
    st.caption(gen_status)

st.markdown("<hr class='sec-divider'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — LIVE DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div id='live-dashboard'></div>", unsafe_allow_html=True)
st.markdown("<div class='section-heading'>📊 Live Dashboard</div>", unsafe_allow_html=True)

funnel_df  = load_funnel()
traffic_df = load_traffic()

if funnel_df.empty:
    st.warning("No data yet — scroll to Pipeline Control to start the generator.")
else:
    funnel_df["window_start"]  = pd.to_datetime(funnel_df["window_start"])
    traffic_df["window_start"] = pd.to_datetime(traffic_df["window_start"])

    latest = funnel_df.iloc[0]
    prev   = funnel_df.iloc[1] if len(funnel_df) > 1 else latest

    total_ev  = int(traffic_df["total_events"].sum())
    uniq_usr  = int(traffic_df.groupby("window_start")["unique_users"].sum().iloc[0]) if not traffic_df.empty else 0
    conv_now  = float(latest.get("conversion_rate", 0))
    conv_prev = float(prev.get("conversion_rate", 0))
    suc_now   = float(latest.get("success_rate", 0))
    suc_prev  = float(prev.get("success_rate", 0))
    fail_now  = int(latest.get("failures", 0))
    fail_prev = int(prev.get("failures", 0))

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Events",         f"{total_ev:,}")
    k2.metric("Unique Users",         f"{uniq_usr:,}")
    k3.metric("Conversion Rate",      f"{conv_now*100:.1f}%",
              delta=f"{(conv_now - conv_prev)*100:+.2f}%")
    k4.metric("Success Rate",         f"{suc_now*100:.1f}%",
              delta=f"{(suc_now - suc_prev)*100:+.2f}%")
    k5.metric("Failures (last window)", fail_now,
              delta=fail_now - fail_prev, delta_color="inverse")

    # row 1: event volume + conversion rate
    ch1, ch2 = st.columns(2)

    with ch1:
        st.caption("Event volume by region over time")
        fig = px.line(
            traffic_df.sort_values("window_start"),
            x="window_start", y="total_events", color="region",
            color_discrete_map=REGION_COLORS,
        )
        fig.update_layout(**PLOTLY_BASE, title="")
        st.plotly_chart(fig, use_container_width=True, key="chart_traffic_volume")

    with ch2:
        st.caption("Conversion rate by region over time")
        fig = px.line(
            funnel_df.sort_values("window_start"),
            x="window_start", y="conversion_rate", color="region",
            color_discrete_map=REGION_COLORS,
        )
        fig.update_layout(**PLOTLY_BASE, yaxis_tickformat=".1%")
        st.plotly_chart(fig, use_container_width=True, key="chart_conversion_time")

    # row 2: funnel bar + success rate
    ch3, ch4 = st.columns(2)

    with ch3:
        st.caption("Funnel stages — aggregated across all windows")
        funnel_agg = (
            funnel_df.groupby("region")[["views","carts","checkout_starts","successes","failures"]]
            .sum().reset_index()
            .melt(id_vars="region", var_name="stage", value_name="count")
        )
        fig = px.bar(
            funnel_agg, x="stage", y="count", color="region",
            barmode="group", color_discrete_map=REGION_COLORS,
        )
        fig.update_layout(**PLOTLY_BASE)
        st.plotly_chart(fig, use_container_width=True, key="chart_funnel_bar")

    with ch4:
        st.caption("Success rate by region over time")
        fig = px.line(
            funnel_df.sort_values("window_start"),
            x="window_start", y="success_rate", color="region",
            color_discrete_map=REGION_COLORS,
        )
        fig.update_layout(**PLOTLY_BASE, yaxis_tickformat=".1%")
        st.plotly_chart(fig, use_container_width=True, key="chart_success_rate")

st.markdown("<hr class='sec-divider'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — ALERTS PANEL
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div id='alerts-panel'></div>", unsafe_allow_html=True)
st.markdown("<div class='section-heading'>🚨 Alerts Panel</div>", unsafe_allow_html=True)

alerts_df = load_alerts()

if alerts_df.empty:
    st.info("No alerts yet — run the detectors from Pipeline Control below.")
else:
    alerts_df["alert_time"] = pd.to_datetime(alerts_df["alert_time"])

    # KPIs
    ak1, ak2, ak3, ak4, ak5 = st.columns(5)
    ak1.metric("Total Alerts",    len(alerts_df))
    ak2.metric("🔴 HIGH",         len(alerts_df[alerts_df.severity == "HIGH"]))
    ak3.metric("🟡 MEDIUM",       len(alerts_df[alerts_df.severity == "MEDIUM"]))
    ak4.metric("Realtime alerts", len(alerts_df[alerts_df.detector_type == "realtime"]))
    ak5.metric("Seasonal alerts", len(alerts_df[alerts_df.detector_type == "seasonal"]))

    # filters
    af1, af2, af3 = st.columns(3)
    sev_f = af1.multiselect("Severity",  ["HIGH","MEDIUM","LOW"],
                             default=["HIGH","MEDIUM","LOW"], key="af_sev")
    det_f = af2.multiselect("Detector",  ["realtime","seasonal"],
                             default=["realtime","seasonal"],  key="af_det")
    reg_f = af3.multiselect("Region",    alerts_df["region"].unique().tolist(),
                             default=alerts_df["region"].unique().tolist(), key="af_reg")

    filt = alerts_df[
        alerts_df.severity.isin(sev_f) &
        alerts_df.detector_type.isin(det_f) &
        alerts_df.region.isin(reg_f)
    ]

    # timeline + by-metric bar
    ac1, ac2 = st.columns([3, 2])

    with ac1:
        st.caption("Alerts timeline — each dot is one alert")
        # AFTER
        hover_cols = [c for c in ["region", "metric_value", "z_score"] if c in filt.columns]
        fig = px.scatter(
            filt, x="alert_time", y="metric",
            color="severity", symbol="detector_type",
            hover_data=hover_cols,
            color_discrete_map=SEV_COLOR,
        )
        fig.update_traces(marker_size=9)
        fig.update_layout(**PLOTLY_BASE)
        st.plotly_chart(fig, use_container_width=True, key="chart_alerts_timeline")

    with ac2:
        st.caption("Alert count by metric & severity")
        mc = filt.groupby(["metric","severity"]).size().reset_index(name="count")
        fig = px.bar(mc, x="count", y="metric", color="severity",
                     orientation="h", color_discrete_map=SEV_COLOR)
        fig.update_layout(**PLOTLY_BASE)
        st.plotly_chart(fig, use_container_width=True, key="chart_alerts_by_metric")

    # by-region bar
    ac3, ac4 = st.columns(2)
    with ac3:
        st.caption("Alert count by region")
        rc_ = filt.groupby(["region","severity"]).size().reset_index(name="count")
        fig = px.bar(rc_, x="region", y="count", color="severity",
                     color_discrete_map=SEV_COLOR)
        fig.update_layout(**PLOTLY_BASE)
        st.plotly_chart(fig, use_container_width=True, key="chart_alerts_by_region")

    with ac4:
        st.caption("Alerts by detector type")
        dc = filt.groupby(["detector_type","severity"]).size().reset_index(name="count")
        fig = px.bar(dc, x="detector_type", y="count", color="severity",
                     color_discrete_map=SEV_COLOR)
        fig.update_layout(**PLOTLY_BASE)
        st.plotly_chart(fig, use_container_width=True, key="chart_alerts_by_detector")

        # AFTER
        display_cols = [c for c in ["alert_time","severity","detector_type","region","metric","metric_value","z_score"] if c in filt.columns]
        rename_map   = {
            "alert_time":"Time","severity":"Severity","detector_type":"Detector",
            "region":"Region","metric":"Metric","metric_value":"Value","z_score":"Z-Score"
        }
        st.dataframe(
            filt[display_cols].rename(columns=rename_map),
            use_container_width=True, hide_index=True,
        )

st.markdown("<hr class='sec-divider'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — PIPELINE CONTROL
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div id='pipeline-control'></div>", unsafe_allow_html=True)
st.markdown("<div class='section-heading'>🔧 Pipeline Control</div>", unsafe_allow_html=True)

# ── generator controls ────────────────────────────────────────────────────────
st.caption("**Event Generator** — runs in background, repeating every N seconds")

gc1, gc2, gc3, gc4 = st.columns([3, 2, 2, 2])

with gc1:
    scenario = st.selectbox(
        "Scenario", options=list(SCENARIO_LABELS.keys()),
        format_func=lambda x: SCENARIO_LABELS[x],
        key="scenario_select",
    )
with gc2:
    cycle = st.number_input(
        "Cycle duration (s)", min_value=15, max_value=300, value=60, step=15,
        help="How long each scenario cycle runs before repeating",
    )
with gc3:
    st.markdown("<br>", unsafe_allow_html=True)
    if not st.session_state.generator_running:
        if st.button("▶ Start", use_container_width=True, type="primary"):
            start_generator(scenario, int(cycle))
            _log(f"Generator started — scenario:{scenario} cycle:{cycle}s")
            st.rerun()
    else:
        if st.button("⏹ Stop", use_container_width=True):
            stop_generator()
            _log("Generator stop requested")
            st.rerun()

with gc4:
    st.markdown("<br>", unsafe_allow_html=True)
    # show current status badge
    if st.session_state.generator_running:
        st.success(f"Running · {st.session_state.generator_scenario}")
    else:
        st.info("Stopped")

# ── pipeline step buttons ─────────────────────────────────────────────────────
st.caption("**Pipeline Steps** — trigger manually or run full cycle at once")

pb1, pb2, pb3, pb4 = st.columns(4)

with pb1:
    if st.button("🧹 Run Cleaning", use_container_width=True):
        with st.spinner("Cleaning…"):
            run_pipeline_step("Cleaning", "scripts.run_cleaning")
        st.cache_data.clear()

with pb2:
    if st.button("📦 Run Aggregations", use_container_width=True):
        with st.spinner("Aggregating…"):
            run_pipeline_step("Aggregations", "scripts.run_aggregations")
        st.cache_data.clear()

with pb3:
    if st.button("🔍 Run Detectors", use_container_width=True):
        with st.spinner("Detecting…"):
            run_detectors()
        st.cache_data.clear()

with pb4:
    if st.button("⚡ Full Pipeline", use_container_width=True, type="primary"):
        with st.spinner("Running full pipeline…"):
            run_pipeline_step("Cleaning",     "scripts.run_cleaning")
            run_pipeline_step("Aggregations", "scripts.run_aggregations")
            run_detectors()
        st.cache_data.clear()
        st.success("Pipeline cycle complete ✓")

# ── log ───────────────────────────────────────────────────────────────────────
st.caption("**Pipeline log**")
if st.session_state.pipeline_log:
    log_html = "<br>".join(reversed(st.session_state.pipeline_log))
    st.markdown(f"<div class='log-box'>{log_html}</div>", unsafe_allow_html=True)
    if st.button("Clear log", key="clear_log"):
        st.session_state.pipeline_log = []
        st.rerun()
else:
    st.markdown("<div class='log-box' style='color:#475569'>No log entries yet</div>",
                unsafe_allow_html=True)

st.markdown("<hr class='sec-divider'>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — REGION & PAYMENT DRILLDOWN
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div id='region-payment-drilldown'></div>", unsafe_allow_html=True)
st.markdown("<div class='section-heading'>🌍 Region & Payment Drilldown</div>", unsafe_allow_html=True)

payment_df  = load_payment()
failures_df = load_failures()
funnel_df2  = load_funnel()  # fresh reference

region_opts = ["All"] + ["IN-NORTH", "IN-SOUTH", "IN-WEST", "IN-EAST"]
sel_region  = st.selectbox("Filter by region", region_opts, key="drilldown_region")

def region_filter(df):
    if sel_region == "All" or df.empty: return df
    return df[df.region == sel_region]

payment_f  = region_filter(payment_df)
failures_f = region_filter(failures_df)
funnel_f   = region_filter(funnel_df2)

if payment_f.empty and failures_f.empty:
    st.warning("No payment/failure data yet.")
else:
    payment_f["window_start"]  = pd.to_datetime(payment_f["window_start"])
    failures_f["window_start"] = pd.to_datetime(failures_f["window_start"])
    funnel_f["window_start"]   = pd.to_datetime(funnel_f["window_start"])

    # row 1: latency + failures pie
    dr1, dr2 = st.columns(2)

    with dr1:
        st.caption("Avg latency by payment method over time")
        if not payment_f.empty:
            fig = px.line(
                payment_f.sort_values("window_start"),
                x="window_start", y="avg_latency_ms", color="payment_method",
                facet_col="region" if sel_region == "All" else None,
            )
            fig.update_layout(**PLOTLY_BASE)
            st.plotly_chart(fig, use_container_width=True, key="chart_latency_payment")

    with dr2:
        st.caption("Failures by reason")
        if not failures_f.empty:
            agg = failures_f.groupby("failure_reason")["failure_count"].sum().reset_index()
            fig = px.pie(
                agg, names="failure_reason", values="failure_count",
                color_discrete_sequence=["#f87171","#fbbf24","#60a5fa"],
                hole=0.45,
            )
            fig.update_layout(**PLOTLY_BASE)
            st.plotly_chart(fig, use_container_width=True, key="chart_failures_pie")

    # row 2: timeout count + conversion by region
    dr3, dr4 = st.columns(2)

    with dr3:
        st.caption("Timeout count by payment method over time")
        if not payment_f.empty:
            fig = px.bar(
                payment_f.sort_values("window_start"),
                x="window_start", y="timeout_count", color="payment_method",
            )
            fig.update_layout(**PLOTLY_BASE)
            st.plotly_chart(fig, use_container_width=True, key="chart_timeout_count")

    with dr4:
        st.caption("Failure count by payment method over time")
        if not payment_f.empty:
            fig = px.bar(
                payment_f.sort_values("window_start"),
                x="window_start", y="failure_count", color="payment_method",
            )
            fig.update_layout(**PLOTLY_BASE)
            st.plotly_chart(fig, use_container_width=True, key="chart_failure_count")

    # row 3: conversion rate (full width)
    st.caption("Conversion rate over time" + (f" — {sel_region}" if sel_region != "All" else " — all regions"))
    if not funnel_f.empty:
        fig = px.line(
            funnel_f.sort_values("window_start"),
            x="window_start", y="conversion_rate", color="region",
            color_discrete_map=REGION_COLORS,
        )
        fig.update_layout(**PLOTLY_BASE, yaxis_tickformat=".1%")
        st.plotly_chart(fig, use_container_width=True, key="chart_conv_drilldown")

    # payment raw table
    with st.expander("📄 Raw payment data table"):
        st.dataframe(
            payment_f.sort_values("window_start", ascending=False),
            use_container_width=True, hide_index=True,
        )

# ══════════════════════════════════════════════════════════════════════════════
# AUTO-REFRESH ENGINE
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.auto_refresh:
    elapsed = (datetime.now() - st.session_state.last_refresh).total_seconds()
    if elapsed >= st.session_state.refresh_interval:
        st.session_state.last_refresh = datetime.now()
        st.cache_data.clear()
        st.rerun()
    else:
        time.sleep(1)
        st.rerun()
