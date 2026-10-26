import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st
from pymongo import MongoClient

import glossary.template_glossary as tg

st.set_page_config(page_title="Template decoder", layout="wide")


@st.cache_resource
def get_db():
    return MongoClient("mongodb://localhost:27017")["thunderbird"]


db = get_db()

LEVEL_NAMES = {"specific": "Specific explanation", "program": "Program-level only",
               "keyword": "Category guessed from keywords", "none": "Not explained yet"}


@st.cache_data(show_spinner="Decoding all templates...")
def load_templates():
    rows = []
    for d in db.templates.find({}, {"template": 1, "n": 1, "alerts": 1, "nodes": 1, "first_ts": 1, "last_ts": 1}):
        e = tg.explain(d["template"])
        rows.append({"id": d["_id"], "template": d["template"], "lines": int(d["n"]),
                     "alerts": int(d.get("alerts", 0) or 0), "nodes": int(d.get("nodes", 0) or 0),
                     "first_seen": str(d.get("first_ts") or "")[:10], "last_seen": str(d.get("last_ts") or "")[:10],
                     "category": e["category"], "meaning": e["headline"], "program": e["program_name"],
                     "level": e["level"]})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner="Summarising alert labels (can take a few seconds)...")
def label_stats():
    out = {}
    for r in db.alerts.aggregate([{"$group": {"_id": "$label", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}], allowDiskUse=True):
        lab = r["_id"]
        progs = list(db.alerts.aggregate([{"$match": {"label": lab}}, {"$group": {"_id": "$program", "n": {"$sum": 1}}},
                                          {"$sort": {"n": -1}}, {"$limit": 3}], allowDiskUse=True))
        tmpls = list(db.alerts.aggregate([{"$match": {"label": lab}},
                                          {"$group": {"_id": "$template_id", "n": {"$sum": 1},
                                                      "template": {"$first": "$template"}, "ex": {"$first": "$msg"}}},
                                          {"$sort": {"n": -1}}, {"$limit": 4}], allowDiskUse=True))
        out[lab] = {"n": r["n"], "programs": [(p["_id"], p["n"]) for p in progs],
                    "templates": [(t["template"], t["n"], t["ex"]) for t in tmpls]}
    return out


df = load_templates()
TOTAL = int(df["lines"].sum())

st.title("Template decoder")
st.caption("A template is a log line with its changing parts (numbers, IPs, ...) replaced by placeholders, so millions of "
           "near-identical lines collapse into one pattern. This page translates templates into plain English and shows "
           "where each explanation comes from.")


def render_label_card(label):
    info = tg.ALERT_LABELS.get(label)
    st.markdown("#### Alert tag: " + str(label))
    if not info:
        st.info("No verified description for this tag in the glossary.")
        return
    t = info["type"]
    st.write("**" + info["title"] + "**  ·  Type: " + (t + " – " + tg.TYPE_NAMES[t] if t else "not verified"))
    st.write(info["summary"])
    st.caption("From the source paper: " + info["paper"])


def render_detail(row):
    tpl = row["template"]
    e = tg.explain(tpl)
    st.markdown("### " + e["headline"])
    tags = ["**Activity:** " + e["category"], "**Explanation level:** " + LEVEL_NAMES[e["level"]]]
    if e["problem_wording"]:
        tags.append("**Wording suggests a problem**")
    st.markdown("  ·  ".join(tags))
    if row.get("lines") is not None:
        a, b, c, d = st.columns(4)
        a.metric("Lines in the log", f"{row['lines']:,}")
        b.metric("Share of all lines", f"{row['lines'] / TOTAL:.3%}")
        c.metric("Tagged as alerts", f"{row['alerts']:,}")
        d.metric("Nodes emitting it", f"{row['nodes']:,}")
        st.caption("First seen " + str(row["first_seen"]) + " · last seen " + str(row["last_seen"]) + " (dates as stored in MongoDB)")
    st.write(e["detail"])
    st.caption("Basis for this explanation: " + e["basis"] + ". 'Wording suggests a problem' is a plain keyword check, not a verdict.")
    st.markdown("**Where it comes from:** " + e["program_name"] + " – " + e["program_desc"])
    c1, c2 = st.columns(2)
    c1.write("Plain-English template")
    c1.code(e["readable"], language=None)
    c2.write("Raw template (as stored)")
    c2.code(tpl, language=None)
    if e["variables"]:
        st.write("What the placeholders mean")
        st.dataframe(pd.DataFrame([(f, d) for _, f, d in e["variables"]], columns=["Shown as", "Meaning"]), hide_index=True)
    if row.get("id"):
        doc = db.templates.find_one({"_id": row["id"]}, {"sample_msgs": 1}) or {}
        samples = doc.get("sample_msgs") or []
        st.write("Real examples from the log (" + str(len(samples)) + " stored)")
        for m in samples:
            st.code(m, language=None)
            vals = tg.extract_values(tpl, m)
            if vals:
                st.text("   ↳ " + "   ".join(k + " = " + v for k, v in vals))


MODES = ["Full raw log line", "Message only (program: text)"]
st.session_state.setdefault("dec_mode", MODES[0])
st.session_state.setdefault("dec_text", "")


def _random_alert():
    d = next(iter(db.alerts.aggregate([{"$sample": {"size": 1}}])), None)
    if d:
        prog = d.get("program")
        st.session_state["dec_text"] = (prog + ": " + d.get("msg", "")) if prog else d.get("msg", "")
        st.session_state["dec_mode"] = MODES[1]


tab_b, tab_d, tab_a, tab_h = st.tabs(["Browse by activity", "Decode a log line", "Alert types", "How templates are made"])

# ---------------- Browse ----------------
with tab_b:
    cov = df.groupby("level")["lines"].sum()
    cols = st.columns(4)
    for col, key in zip(cols, ["specific", "program", "keyword", "none"]):
        col.metric(LEVEL_NAMES[key], f"{cov.get(key, 0) / TOTAL:.1%}", help="Share of all log lines in this explanation level")
    st.caption("Share of all log lines by how well their template is explained. 'Specific' means a written, message-level "
               "explanation; the other levels fall back to program or keyword hints.")
    cat = df.groupby("category").agg(lines=("lines", "sum")).reset_index()
    cat["share of all lines (%)"] = (cat["lines"] / TOTAL * 100).round(2)
    fig = px.bar(cat, x="share of all lines (%)", y="category", orientation="h", title="What the log is mostly about")
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=380)
    st.plotly_chart(fig)

    f1, f2, f3 = st.columns([2, 3, 2])
    sel_cat = f1.selectbox("Activity type", ["(all)"] + [c for c in tg.CATEGORY_ORDER if c in set(df["category"])]
                           + sorted(set(df["category"]) - set(tg.CATEGORY_ORDER)))
    q = f2.text_input("Search (meaning, program, or raw template)", "")
    only_alerts = f3.checkbox("Only templates containing alerts")
    view = df
    if sel_cat != "(all)":
        view = view[view["category"] == sel_cat]
    if q:
        ql = q.lower()
        view = view[view["meaning"].str.lower().str.contains(ql, regex=False)
                    | view["program"].str.lower().str.contains(ql, regex=False)
                    | view["template"].str.lower().str.contains(ql, regex=False)]
    if only_alerts:
        view = view[view["alerts"] > 0]
    view = view.sort_values("lines", ascending=False).head(200).reset_index(drop=True)
    if view.empty:
        st.info("No templates match.")
    else:
        show = view[["meaning", "program", "lines", "alerts", "nodes", "first_seen", "last_seen"]].copy()
        show.insert(0, "rank", range(1, len(show) + 1))
        show["% of all lines"] = (view["lines"] / TOTAL * 100).round(3)
        st.dataframe(show, hide_index=True)
        st.caption("Top 200 by number of lines.")
        idx = st.selectbox("Pick a template to decode in detail", list(range(len(view))),
                           format_func=lambda i: str(i + 1) + ". [" + f"{view.loc[i, 'lines']:,}" + "x] " + view.loc[i, "meaning"][:100])
        st.divider()
        render_detail(view.loc[idx].to_dict())

# ---------------- Decode ----------------
with tab_d:
    st.write("Paste one raw log line (or just the 'program: message' part) to see how it becomes a template and what it means.")
    st.button("Try a random real alert", on_click=_random_alert)
    st.radio("What did you paste?", MODES, key="dec_mode", horizontal=True)
    text = st.text_area("Log line", key="dec_text", height=90)
    line = text.strip().splitlines()[0] if text.strip() else ""
    if line:
        label = node = None
        rest = None
        if st.session_state["dec_mode"] == MODES[0]:
            p = tg.split_raw_line(line)
            if p is None:
                st.error("This doesn't look like a full raw line (needs a label, a numeric epoch timestamp and a node name). "
                         "Try the 'Message only' option.")
            else:
                rest, label, node = p["rest"], p["label"], p["node"]
        else:
            rest = line
        if rest is not None:
            tpl, program, msg = tg.template_from_rest(rest)
            st.markdown("**Step 1 – split the line into parts**")
            st.dataframe(pd.DataFrame([{"label": label if label is not None else "(not in input)",
                                        "node": node or "(not in input)", "program": program or "(none)",
                                        "message": msg}]), hide_index=True)
            st.markdown("**Step 2 – mask the changing parts to get the template**")
            st.code(tpl, language=None)
            st.markdown("**Step 3 – what it means**")
            hit = df[df["template"] == tpl]
            if len(hit):
                render_detail(hit.iloc[0].to_dict())
            else:
                st.info("This exact template is not among the " + f"{len(df):,}" + " stored templates, so there are no log statistics for it. "
                        "The explanation below still applies.")
                render_detail({"template": tpl})
            if label and label != "-":
                st.divider()
                render_label_card(label)

# ---------------- Alert types ----------------
with tab_a:
    st.write("The first column of the raw log tags each alert line with a category. Descriptions come from the dataset's source papers "
             "where I could verify them; otherwise the page says so and shows real examples from your data.")
    st.caption("Sources: " + tg.LABEL_SOURCE + " Dataset page: https://github.com/logpai/loghub/tree/master/Thunderbird")
    stats = label_stats()
    pick = st.selectbox("Alert label", list(stats.keys()), format_func=lambda k: str(k) + "  (" + f"{stats[k]['n']:,}" + " alerts)")
    render_label_card(pick)
    s = stats[pick]
    st.write("**In your data:** " + f"{s['n']:,}" + " alerts · top programs: " + ", ".join(str(p) + " (" + f"{n:,}" + ")" for p, n in s["programs"]))
    st.write("Most common templates with this tag")
    for tpl, n, ex in s["templates"]:
        e = tg.explain(tpl)
        st.markdown("**[" + f"{n:,}" + "x] " + e["headline"] + "**")
        st.code(ex, language=None)

# ---------------- How made ----------------
with tab_h:
    st.markdown("""
1. **Split** each raw line into: label (`-` = normal, anything else = alert tag), timestamp, node, program and message.
2. **Mask** the parts of the message that change from line to line, using the ordered rules below (same rules as `masking.py`).
3. **Group** identical masked messages; each distinct one is a *template*.
""")
    st.dataframe(pd.DataFrame([(i + 1, tg.MASK_RULES[i][1], tg.MASK_RULE_NOTES[i]) for i in range(len(tg.MASK_RULES))],
                              columns=["Order", "Becomes", "What it replaces"]), hide_index=True)
    st.write("Placeholder legend")
    st.dataframe(pd.DataFrame([(k, v[0], v[1]) for k, v in tg.PLACEHOLDERS.items()],
                              columns=["In template", "Shown as", "Meaning"]), hide_index=True)
    st.write("Try the masking on your own text (an example is prefilled; it is not taken from the dataset)")
    demo = st.text_input("Text", "sshd: Accepted publickey for root from ::ffff:10.1.2.3 port 5022 ssh2")
    if demo:
        t2, _, _ = tg.template_from_rest(demo)
        st.code(t2, language=None)
        st.code(tg.readable(t2), language=None)

