from collections import Counter
from pymongo import MongoClient
db = MongoClient("mongodb://localhost:27017")["thunderbird"]
def cut(s, n=130):
    s = (s or "").replace("\n", " ")
    return s if len(s) <= n else s[:n] + "…"
by_prog = Counter()
for t in db.templates.find({"exp_level": "program"}, {"template": 1, "n": 1}):
    by_prog[t["template"].split(": ", 1)[0]] += t["n"]
print("=== program-level-only lines, by program ===")
for p, n in by_prog.most_common(12):
    print(f"{n:>12,}  {n/211212192:6.2%}  {p}")
print("\n=== 40 largest program-level-only templates ===")
for t in db.templates.find({"exp_level": "program"}).sort("n", -1).limit(40):
    print(f"[{t['n']:,}x] {cut(t['template'])}")
