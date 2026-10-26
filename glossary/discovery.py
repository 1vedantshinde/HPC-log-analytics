from collections import Counter
from pymongo import MongoClient

db = MongoClient("mongodb://localhost:27017")["thunderbird"]
TOTAL = 211_212_192

def cut(s, n=160):
    s = (s or "").replace("\n", " ")
    return s if len(s) <= n else s[:n] + "…"

print("=== A. ALERT LABELS: count, top programs, top templates, real example ===")
labels = db.alerts.aggregate([{"$group": {"_id": "$label", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}])
for row in labels:
    lab = row["_id"]
    print(f"\n##### {lab}  ({row['n']:,} alerts)")
    progs = db.alerts.aggregate([{"$match": {"label": lab}},
                                 {"$group": {"_id": "$program", "n": {"$sum": 1}}},
                                 {"$sort": {"n": -1}}, {"$limit": 5}])
    print("  top programs:", ", ".join(f"{p['_id']} ({p['n']:,})" for p in progs))
    tmpls = db.alerts.aggregate([{"$match": {"label": lab}},
                                 {"$group": {"_id": "$template", "n": {"$sum": 1}, "ex": {"$first": "$msg"}}},
                                 {"$sort": {"n": -1}}, {"$limit": 4}])
    for t in tmpls:
        print(f"  [{t['n']:,}x] TEMPLATE: {cut(t['_id'])}")
        print(f"           EXAMPLE : {cut(t['ex'])}")

print("\n=== B. TOP 60 PROGRAMS (all lines) ===")
prog, prog_alerts = Counter(), Counter()
tmpl_rows = list(db.templates.find({}, {"template": 1, "n": 1, "alerts": 1, "sample_msgs": 1}))
for t in tmpl_rows:
    p = t["template"].split(": ", 1)[0]
    prog[p] += t["n"]
    prog_alerts[p] += t.get("alerts", 0)
for p, n in prog.most_common(60):
    print(f"{n:>12,}  {n/TOTAL:6.2%}  alerts={prog_alerts[p]:>9,}  {p}")

print("\n=== C. COVERAGE: how many top templates cover what share of all lines ===")
tmpl_rows.sort(key=lambda t: -t["n"])
cum, marks = 0, {10, 25, 50, 100, 200, 500, 1000}
for i, t in enumerate(tmpl_rows, 1):
    cum += t["n"]
    if i in marks:
        print(f"top {i:>5} templates -> {cum/TOTAL:6.2%} of all lines")

print("\n=== D. TOP 50 TEMPLATES with one real example ===")
for i, t in enumerate(tmpl_rows[:50], 1):
    ex = (t.get("sample_msgs") or [""])[0]
    print(f"{i:>2}. [{t['n']:,}x, alerts={t.get('alerts',0):,}] {cut(t['template'])}")
    print(f"      example: {cut(ex)}")
