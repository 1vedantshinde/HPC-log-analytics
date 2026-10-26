import re
import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo import MongoClient

TOTAL_LINES = 211_212_192

st.set_page_config(page_title="Thunderbird Log Analytics", layout="wide")


@st.cache_resource
def get_db():
    return MongoClient("mongodb://localhost:27017")["thunderbird"]


db = get_db()


@st.cache_data(ttl=300)
def glossary(kind):
    return {d["key"]: d for d in db.glossary.find({"kind": kind}, {"_id": 0})}


@st.cache_data(ttl=300)
def label_counts():
    return list(db.alerts.aggregate([{"$group": {"_id": "$label", "count": {"$sum": 1}}},
                                     {"$sort": {"count": -1}}]))


@st.cache_data(ttl=300)
def coverage():
    out = {"template": 0, "program": 0}
    for r in db.templates.aggregate([{"$match": {"exp_level": {"$exists": True}}},
                                     {"$group": {"_id": "$exp_level", "n": {"$sum": "$n"}}}]):
        out[r["_id"]] = r["n"]
    return out


LABELS = glossary("label")
PROGS = glossary("program")

st.title("Thunderbird Supercomputer Log Analytics")
st.caption("211.2M parsed log lines · 47,320 templates · 3.25M alerts · Sandia National Labs, 2005-2006")
if not LABELS:
    st.warning("Glossary not loaded yet. Run `python load_glossary.py` in the project folder, then refresh.")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Templates", "Node Drill-down", "Alert Explorer", "Glossary"])

# ------------------------------------------------------------------ OVERVIEW
with tab1:
    cov = coverage()
    explained = cov["template"] + cov["program"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total events", f"{TOTAL_LINES:,}")
    c2.metric("Total alerts", f"{db.alerts.estimated_document_count():,}")
    c3.metric("Distinct templates", f"{db.templates.estimated_document_count():,}")
    c4.metric("Lines with a specific explanation", f"{cov['template'] / TOTAL_LINES:.1%}",
              help=f"A further {cov['program'] / TOTAL_LINES:.1%} have only a generic program-level note. "
                   "Computed from the templates collection.")

    st.subheader("Alert volume by label")
    ldf = pd.DataFrame(label_counts()).rename(columns={"_id": "label"})
    ldf["meaning"] = ldf["label"].map(lambda l: LABELS.get(l, {}).get("short", "(no entry yet)"))
    fig = px.bar(ldf, x="label", y="count", log_y=True, hover_data=["meaning"],
                 labels={"label": "Alert label", "count": "Count (log scale)"})
    st.plotly_chart(fig, use_container_width=True)
    total_alerts = int(ldf["count"].sum())
    top = ldf.iloc[0]
    st.caption(f"{top['label']} makes up {top['count'] / total_alerts:.1%} of all alerts. "
               "Hover a bar for a short name; the explanations are below.")

    st.subheader("What do these alert labels mean?")
    for _, r in ldf.iterrows():
        g = LABELS.get(r["label"])
        head = f"{r['label']} - {g['short'] if g else 'no entry yet'}   |   {int(r['count']):,} alerts ({r['count'] / total_alerts:.2%})"
        with st.expander(head):
            if g:
                st.write(g["plain"])
                if g.get("type"):
                    st.write(f"**Category type in the original study:** {g['type']}")
                if g.get("note"):
                    st.write(g["note"])
                st.caption(f"Basis for this explanation: {g['source']}")
            else:
                st.write("No glossary entry yet.")

    st.subheader("Daily event + alert trend (all nodes combined)")
    trend = pd.DataFrame(list(db.node_daily.aggregate([
        {"$group": {"_id": {"$substr": ["$day", 0, 10]}, "lines": {"$sum": "$lines"}, "alerts": {"$sum": "$alerts"}}},
        {"$sort": {"_id": 1}}])))
    if not trend.empty:
        trend.columns = ["day", "lines", "alerts"]
        st.plotly_chart(px.line(trend, x="day", y=["lines", "alerts"],
                                labels={"value": "Count", "day": "Date"}), use_container_width=True)

# ------------------------------------------------------------------ TEMPLATES
with tab2:
    st.subheader("Log message templates")
    with st.expander("How to read a template"):
        st.markdown(
            "A template is a log message with its changing parts replaced by placeholders, so thousands of "
            "similar lines group into one pattern.\n\n"
            "- `<N>` a number  - `<IP>` an IP address  - `<HEX>` a hexadecimal value  - `<MAC>` a hardware address\n"
            "- `<QID>` a mail queue ID  - `<ANON>` a value that was already anonymised in the original dataset (like `#569#`)\n"
            "- The word before the first colon is the program that wrote the line. `(none)` means no program "
            "prefix was found; `(empty)` means the line had no message text.\n\n"
            "The **real, unmasked example messages** are shown when you select a template below.")
    c1, c2, c3 = st.columns([3, 2, 2])
    search = c1.text_input("Search templates (text)", "")
    only_expl = c2.checkbox("Only templates with a specific explanation", value=False)
    cats = ["(all)"] + sorted([c for c in db.templates.distinct("exp_category") if c])
    cat = c3.selectbox("Category", cats)

    query = {}
    if search:
        query["template"] = {"$regex": re.escape(search), "$options": "i"}
    if only_expl:
        query["exp_level"] = "template"
    if cat != "(all)":
        query["exp_category"] = cat
    top_t = list(db.templates.find(query).sort("n", -1).limit(40))

    def meaning(t):
        if t.get("exp_level") == "template":
            return t["exp_title"]
        if t.get("exp_level") == "program":
            return "(program-level note only)"
        return "- not explained yet -"

    if top_t:
        df = pd.DataFrame([{"lines": t["n"], "alerts": t.get("alerts", 0), "what it means": meaning(t),
                            "category": t.get("exp_category", ""), "template": t["template"]} for t in top_t])
        st.dataframe(df, use_container_width=True, height=420, hide_index=True)

        st.subheader("Inspect one template")
        options = {f"{i + 1}. [{t['n']:,} lines] {meaning(t)[:60]} | {t['template'][:50]}": t["_id"]
                   for i, t in enumerate(top_t)}
        choice = st.selectbox("Select a template", list(options.keys()))
        doc = db.templates.find_one({"_id": options[choice]})
        if doc.get("exp_level") == "template":
            st.success(f"**{doc['exp_title']}**\n\n{doc['exp_plain']}")
            st.caption(f"Category: {doc['exp_category']} | basis: {doc['exp_source']}")
        elif doc.get("exp_level") == "program":
            st.info(f"No specific explanation for this message yet. {doc['exp_title']}: {doc['exp_plain']}")
        else:
            st.warning("Not explained yet.")
        st.write("**Template pattern**")
        st.code(doc["template"], language=None)
        st.write("**Real example messages (unmasked)**")
        for m in doc.get("sample_msgs", []):
            st.code(m, language=None)
    else:
        st.info("No templates matched.")

# ------------------------------------------------------------------ NODE DRILL-DOWN
with tab3:
    st.subheader("Per-node daily activity")
    node_name = st.text_input("Node name (e.g. cn414, an193, tbird-admin1)", "")
    if node_name:
        rows = list(db.node_daily.find({"node": node_name}).sort("day", 1))
        if rows:
            ndf = pd.DataFrame(rows)
            ndf["day"] = ndf["day"].str[:10]
            st.plotly_chart(px.bar(ndf, x="day", y=["lines", "alerts"], barmode="group",
                                   labels={"value": "Count", "day": "Date"}), use_container_width=True)
            st.dataframe(ndf[["day", "lines", "alerts", "distinct_templates"]],
                         use_container_width=True, hide_index=True)
        else:
            st.warning(f"No data found for node '{node_name}'. Check spelling/case.")
    else:
        st.info("Enter a node name to see its activity timeline.")

# ------------------------------------------------------------------ ALERT EXPLORER
with tab4:
    st.subheader("Browse real alert records")
    a1, a2 = st.columns(2)
    label_filter = a1.selectbox("Filter by label", ["(all)"] + sorted(db.alerts.distinct("label")))
    node_filter = a2.text_input("Filter by node (exact match, optional)", "")
    q = {}
    if label_filter != "(all)":
        q["label"] = label_filter
        g = LABELS.get(label_filter)
        if g:
            st.info(f"**{label_filter} - {g['short']}.** {g['plain']}")
    if node_filter:
        q["node"] = node_filter
    st.write(f"**{db.alerts.count_documents(q):,} matching alerts** (showing the 50 most recent)")
    res = list(db.alerts.find(q).sort("ts", -1).limit(50))
    if res:
        st.dataframe(pd.DataFrame(res)[["ts", "node", "label", "program", "msg"]],
                     use_container_width=True, height=480, hide_index=True)
    else:
        st.info("No alerts match this filter.")

# ------------------------------------------------------------------ GLOSSARY
with tab5:
    g1, g2, g3 = st.tabs(["Alert labels", "Programs", "Not explained yet"])
    with g1:
        st.dataframe(pd.DataFrame([{"label": k, "short name": v["short"], "meaning": v["plain"],
                                    "basis": v["source"]} for k, v in LABELS.items()]),
                     use_container_width=True, hide_index=True)
    with g2:
        ps = st.text_input("Filter programs", "")
        prow = [{"program": k, "meaning": v["plain"], "basis": v["source"]}
                for k, v in PROGS.items() if ps.lower() in k.lower() or ps.lower() in v["plain"].lower()]
        st.dataframe(pd.DataFrame(prow), use_container_width=True, hide_index=True)
    with g3:
        st.caption("Largest templates with no explanation yet. These are the next entries to write in glossary_data.py.")
        rest = list(db.templates.find({"exp_level": {"$exists": False}}).sort("n", -1).limit(20))
        if rest:
            st.dataframe(pd.DataFrame([{"lines": t["n"], "template": t["template"]} for t in rest]),
                         use_container_width=True, hide_index=True)
        else:
            st.success("Every template has at least a program-level note.")
