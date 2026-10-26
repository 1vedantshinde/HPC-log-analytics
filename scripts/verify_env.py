import importlib
for m in ["pyspark", "pymongo", "streamlit", "plotly", "pandas", "numpy"]:
    try:
        mod = importlib.import_module(m); print(f"OK   {m} {getattr(mod, '__version__', '?')}")
    except Exception as e:
        print(f"FAIL {m}: {e}")

from pymongo import MongoClient
db = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=4000)["thunderbird"]
print("\nMongo server", db.client.server_info()["version"])
for c in sorted(db.list_collection_names()):
    print(f"  {c:20s} docs~{db[c].estimated_document_count():>12,}  indexes={list(db[c].index_information())}")
for c in ["templates", "alerts", "node_daily"]:
    d = db[c].find_one()
    print(f"\n{c} sample:", {k: (type(v).__name__, str(v)[:45]) for k, v in d.items()})
t = list(db.templates.aggregate([{"$group": {"_id": None, "s": {"$sum": "$n"}, "c": {"$sum": 1}}}]))[0]
print(f"\nsum(templates.n)={t['s']:,}  template docs={t['c']:,}  (dashboard hardcodes 211,212,192)")
print("alert labels:", [(r["_id"], r["n"]) for r in db.alerts.aggregate(
    [{"$group": {"_id": "$label", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}])])

from pyspark.sql import SparkSession, functions as F
spark = (SparkSession.builder.master("local[4]").appName("verify")
         .config("spark.sql.session.timeZone", "UTC").getOrCreate())
spark.sparkContext.setLogLevel("ERROR")
print("\nSpark", spark.version)
BASE = "hdfs://localhost:9000/processed/thunderbird"
ev = spark.read.parquet(BASE + "/events")
ev.printSchema()
print("events:", f"{ev.count():,}")
print(ev.agg(F.min("epoch"), F.max("epoch"), F.countDistinct("week")).first())
spark.read.parquet(BASE + "/templates").printSchema()
spark.stop()
