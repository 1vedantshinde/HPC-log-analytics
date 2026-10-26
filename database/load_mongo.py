import json, glob
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["thunderbird"]

def load(collection_name, path_glob, batch_size=5000):
    coll = db[collection_name]
    coll.drop()
    batch = []
    total = 0
    for fname in sorted(glob.glob(path_glob)):
        with open(fname) as f:
            for line in f:
                batch.append(json.loads(line))
                if len(batch) >= batch_size:
                    coll.insert_many(batch, ordered=False)
                    total += len(batch)
                    batch = []
    if batch:
        coll.insert_many(batch, ordered=False)
        total += len(batch)
    print(f"{collection_name}: loaded {total} documents")

load("templates", "mongo_export/templates/part-*.json")
load("alerts", "mongo_export/alerts/part-*.json")
load("node_daily", "mongo_export/node_daily/part-*.json")
