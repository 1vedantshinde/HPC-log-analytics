import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pymongo import MongoClient

st.set_page_config(page_title="Findings", layout="wide")

@st.cache_resource
def get_db():
    return MongoClient("mongodb://localhost:27017")["thunderbird"]
db = get_db()

st.title("Research findings")
meta = db.rs_meta.find_one({"_id": "summary"}) or db.rs_meta.find_one({"_id": "dryrun_summary"})
if not meta:
    st.error("rs_meta not found. Run research_analyses.py first."); st.stop()
if meta.get("dry_run"):
    st.warning("Showing a DRY RUN on a subset of weeks. Re-run research_analyses.py without WEEKS.")
st.caption(f"{meta['events']:,} events · {meta['alerts']:,} alerts · computed offline in Spark, stored in rs_* collections (replay in UTC; storm days bucketed in {meta.get('day_tz', 'UTC')})")

tab_z, tab_s, tab_p, tab_r = st.tabs(["Heavy-tail (Zipf)", "Log storms", "Alert precursors", "Replay"])

# ---------- Zipf ----------
@st.cache_data
def template_counts():
    arr = np.array([d["n"] for d in db.templates.find({}, {"n": 1, "_id": 0})], dtype="int64")
    return np.sort(arr)[::-1]

with tab_z:
    n_sorted = template_counts(); ranks = np.arange(1, len(n_sorted) + 1); total = n_sorted.sum()
    lo, hi = st.slider("Rank range used for the fit", 1, len(n_sorted), (1, len(n_sorted)))
    if hi - lo < 3:
        st.warning("Choose a wider rank range.")
    else:
        x, y = np.log10(ranks[lo - 1:hi]), np.log10(n_sorted[lo - 1:hi])
        slope, icpt = np.polyfit(x, y, 1)
        r2 = 1 - ((y - (slope * x + icpt)) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Fitted exponent s (freq ∝ rank^-s)", f"{-slope:.3f}")
        c2.metric("R² of the fit", f"{r2:.3f}")
        c3.metric("Singleton templates", f"{(n_sorted == 1).mean():.1%}")
        fig = go.Figure()
        fig.add_trace(go.Scattergl(x=ranks, y=n_sorted, mode="markers", name="templates", marker=dict(size=3)))
        fig.add_trace(go.Scatter(x=ranks[lo - 1:hi], y=10 ** (slope * x + icpt), name="fit", line=dict(color="red")))
        fig.update_layout(xaxis_type="log", yaxis_type="log", xaxis_title="Template rank",
                          yaxis_title="Lines per template", height=450)
        st.plotly_chart(fig, use_container_width=True)
        cum = np.cumsum(n_sorted) / total
        st.write("Coverage: " + " · ".join(f"top {k:,} templates = {cum[k - 1]:.2%} of lines"
                                         for k in (10, 100, 1000) if k <= len(cum)))
        st.caption("Simple least-squares fit on log-log axes: a rough estimate, not a rigorous power-law test. "
                   "The plateau of count-1 templates in the tail bends the fit, so compare different rank ranges.")

# ---------- Storms ----------
with tab_s:
    storms = list(db.rs_storms.find({}, {"_id": 0}).sort("lines", -1))
    base = db.rs_storm_baseline.find_one({"_id": "baseline"})
    if not storms:
        st.info("No storm data. Run research_analyses.py.")
    else:
        if base:
            a, b, c = st.columns(3)
            a.metric("Median share of lines from top-5 nodes: storm days", f"{base['median_top5_share_storm']:.1%}")
            b.metric("Same, all other days", f"{base['median_top5_share_other']:.1%}" if base["median_top5_share_other"] is not None else "n/a")
            c.metric("Median active nodes (storm vs other)",
                     f"{base['median_active_nodes_storm']:.0f} vs {base['median_active_nodes_other']:.0f}"
                     if base["median_active_nodes_other"] is not None else "n/a")
        df = pd.DataFrame(storms)
        df["top5_share"] = (df["top5_share"] * 100).round(1)
        st.dataframe(df[["day", "lines", "active_nodes", "top5_share", "top_node", "top_node_lines"]]
                     .rename(columns={"top5_share": "top5_share_%"}), use_container_width=True)
        for s in storms:
            with st.expander(f"{s['day']} — {s['lines']:,} lines, {s['active_nodes']:,} active nodes"):
                t = pd.DataFrame(s["templates"])
                if not t.empty:
                    t["share_of_day_%"] = (t["lines"] / s["lines"] * 100).round(1)
                    st.dataframe(t[["rank", "template", "lines", "share_of_day_%", "nodes_emitting"]],
                                 use_container_width=True)

# ---------- Precursors ----------
with tab_p:
    stats = pd.DataFrame(list(db.rs_label_stats.find({}, {"_id": 0})))
    if stats.empty:
        st.info("No precursor data.")
    else:
        stats = stats.sort_values("alerts", ascending=False)
        st.write(f"Non-{meta['dominant_label']} labels. An *incident* = distinct (label, node, clock-hour); "
                 "the precursor window is the clock-hour before it. Alert lines are excluded from both sides.")
        st.dataframe(stats, use_container_width=True)
        label = st.selectbox("Label", list(stats["label"]))
        rows = pd.DataFrame(list(db.rs_precursors.find({"label": label}, {"_id": 0})))
        if rows.empty:
            st.info("No template met the minimum support for this label.")
        else:
            mk = st.slider("Minimum incidents with template (k)", int(rows["k"].min()), int(rows["k"].max()), int(rows["k"].min()))
            mp = st.slider("Minimum p_pre", 0.0, 1.0, 0.0, 0.05)
            r = rows[(rows["k"] >= mk) & (rows["p_pre"] >= mp)].sort_values("lift", ascending=False)
            st.dataframe(r[["template", "k", "n_inc", "p_pre", "p_base", "lift", "expected"]], use_container_width=True, height=450)
            st.caption("p_pre = share of incidents with the template in the preceding hour. p_base = share of all node-hours "
                       "(same nodes) containing it. lift = p_pre / p_base. Small incident counts make lift unstable; use the k slider.")

# ---------- Replay ----------
@st.cache_data
def load_hourly():
    df = pd.DataFrame(list(db.rs_hourly.find({}, {"_id": 0})))
    df["hour"] = pd.to_datetime(df["hour_epoch"], unit="s", utc=True)
    df = df.set_index("hour").sort_index()
    return df[["lines", "alerts", "rare"]].reindex(pd.date_range(df.index.min(), df.index.max(), freq="h"), fill_value=0)

@st.cache_data
def load_rare():
    df = pd.DataFrame(list(db.rs_rare_alerts.find({}, {"_id": 0})))
    if df.empty: return df
    df = df.sort_values("epoch").reset_index(drop=True)
    df["time"] = pd.to_datetime(df["epoch"], unit="s", utc=True)
    return df

with tab_r:
    h, rare = load_hourly(), load_rare()
    h_epoch = ((h.index - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(seconds=1)).to_numpy()
    rare_epochs = rare["epoch"].to_numpy() if not rare.empty else np.array([], dtype="int64")
    cum_l, cum_a = h["lines"].cumsum().to_numpy(), h["alerts"].cumsum().to_numpy()
    dates = np.array([d.date() for d in h.index])
    c1, c2, c3 = st.columns(3)
    step = c1.selectbox("Simulated hours per tick", [1, 3, 6, 12, 24], index=3)
    delay = c2.slider("Seconds per tick", 0.02, 1.0, 0.1)
    wdays = c3.slider("Chart window (days)", 3, 30, 14)
    days = sorted(set(dates))
    start_day = st.select_slider("Start replay at (UTC date)", options=days, value=days[0])
    start_i = int(np.argmax(dates >= start_day))
    play = st.button("▶ Play")
    st.caption("Replays stored history as if it were arriving live. Touching any widget stops playback.")
    clock, met = st.empty(), st.empty()
    st.write("Lines per hour"); p_lines = st.empty()
    st.write("Alerts per hour (all labels)"); p_alerts = st.empty()
    st.write(f"Latest non-{meta['dominant_label']} alerts"); p_feed = st.empty()

    def render(i):
        e = min(i, len(h) - 1)
        clock.subheader(f"Simulated time: {h.index[e]:%Y-%m-%d %H:00} UTC")
        j = int(np.searchsorted(rare_epochs, h_epoch[e] + 3600, side="right"))
        with met.container():
            a, b, c = st.columns(3)
            a.metric("Lines so far", f"{int(cum_l[e]):,}")
            b.metric("Alerts so far", f"{int(cum_a[e]):,}")
            c.metric(f"Non-{meta['dominant_label']} alerts so far", f"{j:,}")
        win = h.iloc[max(0, e - wdays * 24):e + 1]
        p_lines.line_chart(win["lines"]); p_alerts.bar_chart(win["alerts"])
        if not rare.empty:
            p_feed.dataframe(rare.iloc[max(0, j - 8):j].iloc[::-1][["time", "node", "label", "program", "msg"]],
                             use_container_width=True)

    render(start_i)
    if play:
        for i in range(start_i, len(h), step):
            render(i); time.sleep(delay)
