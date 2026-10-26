import sys, time
from pymongo import MongoClient, ASCENDING as A, DESCENDING as D

db = MongoClient("mongodb://localhost:27017")["thunderbird"]
NAMES = {"alerts": ["rs_label_ts", "rs_node_ts", "rs_ts"], "node_daily": ["rs_node_day"]}

if "--drop" in sys.argv:
    for coll, names in NAMES.items():
        for n in names:
            if n in db[coll].index_information():
                db[coll].drop_index(n); print("dropped", coll, n)
    sys.exit()

ex = db.alerts.find_one({"label": "ECC"})
if not ex:
    sys.exit("No alert with label ECC found; tell me what labels exist (verify_env.py prints them).")
node = ex["node"]
tests = [
    ("alerts label=ECC sort ts desc limit 50", lambda: list(db.alerts.find({"label": "ECC"}).sort("ts", -1).limit(50))),
    (f"alerts node={node} sort ts desc limit 50", lambda: list(db.alerts.find({"node": node}).sort("ts", -1).limit(50))),
    ("alerts (all) sort ts desc limit 50", lambda: list(db.alerts.find({}).sort("ts", -1).limit(50))),
    ("alerts label=VAPI sort ts desc limit 50", lambda: list(db.alerts.find({"label": "VAPI"}).sort("ts", -1).limit(50))),
    ("alerts count label=VAPI", lambda: db.alerts.count_documents({"label": "VAPI"})),
    (f"node_daily node={node} sort day", lambda: list(db.node_daily.find({"node": node}).sort("day", 1))),
    ("templates sort n desc limit 30", lambda: list(db.templates.find({}).sort("n", -1).limit(30))),
]
def run(tag):
    print(f"\n--- {tag} ---")
    for name, fn in tests:
        t = time.time(); fn(); print(f"{name:50s} {time.time() - t:8.3f}s")

for coll in NAMES:
    print(coll, "existing indexes:", list(db[coll].index_information()))
run("BEFORE")
db.alerts.create_index([("label", A), ("ts", D)], name="rs_label_ts")
db.alerts.create_index([("node", A), ("ts", D)], name="rs_node_ts")
db.alerts.create_index([("ts", D)], name="rs_ts")
db.node_daily.create_index([("node", A), ("day", A)], name="rs_node_day")
pass
run("AFTER")
