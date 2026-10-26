# load_glossary.py
# Loads glossary_data.py into MongoDB and tags every template with a plain-English explanation.
# Safe to re-run: it rewrites the `glossary` collection and refreshes the exp_* fields on templates.
# Does NOT touch Spark, HDFS, the events, or the alerts collection.
import re
from pymongo import MongoClient, UpdateOne
from glossary_data import LABELS, PROGRAMS, TEMPLATE_RULES

TOTAL = 211_212_192
db = MongoClient("mongodb://localhost:27017")["thunderbird"]

# ---- 1. glossary collection (labels + programs) -------------------------------------
db.glossary.drop()
docs = []
for key, v in LABELS.items():
    docs.append({"_id": f"label:{key}", "kind": "label", "key": key, **v})
for key, v in PROGRAMS.items():
    docs.append({"_id": f"program:{key}", "kind": "program", "key": key, **v})
db.glossary.insert_many(docs)
print(f"glossary: {len(LABELS)} labels, {len(PROGRAMS)} programs loaded")

# ---- 2. tag each template ---------------------------------------------------------------
rules = [(re.compile(r["pattern"]), r) for r in TEMPLATE_RULES]
EXP_FIELDS = ["exp_level", "exp_title", "exp_plain", "exp_category", "exp_source"]

ops, batch_size = [], 5000
lines = {"template": 0, "program": 0, "none": 0}
count = {"template": 0, "program": 0, "none": 0}
unexplained, missing_progs = [], {}

def flush():
    global ops
    if ops:
        db.templates.bulk_write(ops, ordered=False)
        ops = []

for t in db.templates.find({}, {"template": 1, "n": 1}):
    tpl, n = t["template"], t["n"]
    level, upd = "none", None
    for rx, r in rules:
        if rx.search(tpl):
            level = "template"
            upd = {"exp_level": "template", "exp_title": r["title"], "exp_plain": r["plain"],
                   "exp_category": r["category"], "exp_source": r["source"]}
            break
    if upd is None:
        prog = tpl.split(": ", 1)[0]
        p = PROGRAMS.get(prog)
        if p:
            level = "program"
            upd = {"exp_level": "program", "exp_title": f"General note about '{prog}'",
                   "exp_plain": p["plain"], "exp_category": "Program-level note", "exp_source": p["source"]}
        else:
            missing_progs[prog] = missing_progs.get(prog, 0) + n
            unexplained.append((n, tpl))
    lines[level] += n
    count[level] += 1
    if upd:
        ops.append(UpdateOne({"_id": t["_id"]}, {"$set": upd}))
    else:
        ops.append(UpdateOne({"_id": t["_id"]}, {"$unset": {f: "" for f in EXP_FIELDS}}))
    if len(ops) >= batch_size:
        flush()
flush()

# ---- 3. coverage report (this is also a report-ready result) -----------------------
print("\n=== GLOSSARY COVERAGE ===")
for lvl, label in (("template", "specific template explanation"), ("program", "program-level note only"),
                   ("none", "no explanation yet")):
    print(f"{label:<32} templates={count[lvl]:>7,}   lines={lines[lvl]:>12,}  ({lines[lvl]/TOTAL:6.2%} of all lines)")
covered = lines["template"] + lines["program"]
print(f"{'TOTAL with some meaning':<32} lines={covered:>12,}  ({covered/TOTAL:6.2%})")

print("\nLargest templates still unexplained:")
for n, tpl in sorted(unexplained, reverse=True)[:15]:
    print(f"  {n:>10,}  {tpl[:130]}")
print("\nPrograms with unexplained templates (by line count):")
for p, n in sorted(missing_progs.items(), key=lambda x: -x[1])[:15]:
    print(f"  {n:>10,}  {p}")
