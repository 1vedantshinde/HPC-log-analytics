import os, sys, time
import pandas as pd
from pymongo import MongoClient
from pyspark.sql import SparkSession, functions as F, Window

BASE = sys.argv[1] if len(sys.argv) > 1 else "hdfs://localhost:9000/processed/thunderbird"
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
DOMINANT = os.environ.get("DOMINANT_LABEL", "VAPI")
TOP_DAYS = int(os.environ.get("TOP_DAYS", "10"))
MIN_SUPPORT = int(os.environ.get("MIN_SUPPORT", "3"))
KEEP_PER_LABEL = int(os.environ.get("KEEP_PER_LABEL", "300"))
WEEKS = [w for w in os.environ.get("WEEKS", "").split(",") if w]   # dry-run on a subset
HOUR = 3600
DAY_TZ = os.environ.get("DAY_TZ", "UTC")
TMP = os.environ.get("SPARK_TMP", "/home/vs/spark-tmp"); os.makedirs(TMP, exist_ok=True)

spark = (SparkSession.builder.master(f"local[{os.environ.get('CORES', '8')}]").appName("research-analyses")
         .config("spark.driver.memory", os.environ.get("DRIVER_MEM", "8g"))
         .config("spark.sql.shuffle.partitions", "64")
         .config("spark.sql.session.timeZone", "UTC")
         .config("spark.local.dir", TMP).getOrCreate())
spark.sparkContext.setLogLevel("ERROR")
T0 = time.time()
def lap(msg): print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)

ev = spark.read.parquet(BASE + "/events")
need = {"week", "epoch", "ts", "node", "label", "is_alert", "program", "template_id", "template", "msg"}
if need - set(ev.columns):
    sys.exit(f"events is missing columns {sorted(need - set(ev.columns))}; actual: {ev.columns}")
if WEEKS:
    ev = ev.filter(F.col("week").isin(WEEKS)); print("*** DRY RUN on weeks:", WEEKS)

mc = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000); mc.server_info()
db = mc["thunderbird"]
def replace(name, docs):
    db[name].drop()
    if docs: db[name].insert_many(docs)
    print(f"  wrote {name}: {len(docs):,} docs", flush=True)

# ---------- A. summary / meta ----------
n_events = ev.count()
alert_ev = ev.filter("is_alert")
n_alerts = alert_ev.count()
labels = {r["label"]: r["count"] for r in alert_ev.groupBy("label").count().collect()}
span = ev.agg(F.min("epoch").alias("lo"), F.max("epoch").alias("hi")).first()
tsum = list(db.templates.aggregate([{"$group": {"_id": None, "s": {"$sum": "$n"}}}]))
mongo_sum = tsum[0]["s"] if tsum else None
lap(f"events={n_events:,} alerts={n_alerts:,}  (sum of Mongo templates.n = {mongo_sum:,})")
if not WEEKS and mongo_sum != n_events:
    print("WARNING: Parquet event count != sum(templates.n) in Mongo. Investigate before trusting numbers.")
if DOMINANT not in labels:
    sys.exit(f"Label {DOMINANT!r} not found among alert labels {list(labels)}; set DOMINANT_LABEL.")
meta = {"_id": "dryrun_summary" if WEEKS else "summary", "dry_run": bool(WEEKS), "events": n_events,
        "alerts": n_alerts, "templates": db.templates.estimated_document_count(),
        "dominant_label": DOMINANT, "day_tz": DAY_TZ, "dominant_alerts": labels[DOMINANT],
        "dominant_share": labels[DOMINANT] / n_alerts if n_alerts else None, "labels": labels,
        "first_epoch": int(span["lo"]), "last_epoch": int(span["hi"]),
        "mongo_template_event_sum": mongo_sum, "generated_at": time.time()}
db.rs_meta.replace_one({"_id": meta["_id"]}, meta, upsert=True)

evh = ev.select("node", "label", "is_alert", "template_id", "epoch",
                (F.col("epoch") - (F.col("epoch") % HOUR)).alias("hr"))
rare_cond = F.col("is_alert") & (F.col("label") != DOMINANT)

# ---------- B. replay data ----------
hourly = (evh.groupBy("hr").agg(F.count("*").alias("lines"),
          F.sum(F.col("is_alert").cast("int")).alias("alerts"),
          F.sum(rare_cond.cast("int")).alias("rare")).orderBy("hr").collect())
replace("rs_hourly", [{"hour_epoch": int(r["hr"]), "lines": int(r["lines"]),
                       "alerts": int(r["alerts"]), "rare": int(r["rare"])} for r in hourly])
rare_df = ev.filter(rare_cond).select("epoch", "node", "label", "program", "msg").cache()
n_rare = rare_df.count()
if n_rare > 500_000:
    sys.exit(f"{n_rare:,} non-{DOMINANT} alerts: far more than expected; check DOMINANT_LABEL.")
if not WEEKS:
    mongo_rare = db.alerts.count_documents({"label": {"$ne": DOMINANT}})
    print(f"  non-{DOMINANT} alerts: parquet={n_rare:,} vs mongo alerts collection={mongo_rare:,}")
replace("rs_rare_alerts", [{"epoch": int(r["epoch"]), "node": r["node"], "label": r["label"],
                           "program": r["program"], "msg": (r["msg"] or "")[:300]}
                          for r in rare_df.orderBy("epoch").collect()])
lap("replay data done")

# ---------- C. log-storm explainer ----------
dayc = F.date_format(F.from_utc_timestamp("ts", DAY_TZ), "yyyy-MM-dd")
dn = ev.groupBy(dayc.alias("day"), "node").count().cache()
ranked = dn.withColumn("rn", F.row_number().over(Window.partitionBy("day").orderBy(F.desc("count"), "node")))
tot = dn.groupBy("day").agg(F.sum("count").alias("lines"), F.count("*").alias("active_nodes"))
top5 = ranked.filter("rn <= 5").groupBy("day").agg(F.sum("count").alias("top5_lines"))
top1 = ranked.filter("rn = 1").select("day", F.col("node").alias("top_node"), F.col("count").alias("top_node_lines"))
daily = pd.DataFrame([r.asDict() for r in tot.join(top5, "day").join(top1, "day").collect()])
daily["top5_share"] = daily["top5_lines"] / daily["lines"]
daily = daily.sort_values("lines", ascending=False).reset_index(drop=True)
storm, rest = daily.head(TOP_DAYS), daily.iloc[TOP_DAYS:]
baseline = {"_id": "baseline", "n_days": int(len(daily)), "storm_days": int(len(storm)),
            "median_top5_share_storm": float(storm["top5_share"].median()),
            "median_top5_share_other": float(rest["top5_share"].median()) if len(rest) else None,
            "median_active_nodes_storm": float(storm["active_nodes"].median()),
            "median_active_nodes_other": float(rest["active_nodes"].median()) if len(rest) else None,
            "median_lines_other": float(rest["lines"].median()) if len(rest) else None}
tpl = spark.read.parquet(BASE + "/templates").select("template_id", "template")
dt = (ev.filter(dayc.isin(list(storm["day"]))).groupBy(dayc.alias("day"), "template_id")
        .agg(F.count("*").alias("lines"), F.countDistinct("node").alias("nodes_emitting")))
top_t = (dt.withColumn("rk", F.row_number().over(Window.partitionBy("day").orderBy(F.desc("lines"))))
           .filter("rk <= 3").join(tpl, "template_id", "left").collect())
tt = {}
for r in top_t:
    tt.setdefault(r["day"], []).append({"rank": int(r["rk"]), "template_id": int(r["template_id"]),
        "template": (r["template"] or "")[:300], "lines": int(r["lines"]), "nodes_emitting": int(r["nodes_emitting"])})
storm_docs = [{"day": r["day"], "lines": int(r["lines"]), "active_nodes": int(r["active_nodes"]),
               "top5_share": float(r["top5_share"]), "top_node": r["top_node"],
               "top_node_lines": int(r["top_node_lines"]),
               "templates": sorted(tt.get(r["day"], []), key=lambda d: d["rank"])} for _, r in storm.iterrows()]
replace("rs_storms", storm_docs)
replace("rs_storm_baseline", [baseline])
print(storm[["day", "lines", "active_nodes", "top5_share", "top_node"]].to_string(index=False))
lap("storms done")

# ---------- D. precursors of non-dominant alerts ----------
# Incident = distinct (label, node, clock-hour): bursts of alerts count once.
# Precursor window = the clock-hour BEFORE the incident hour. Alert lines are excluded
# from both the precursor and baseline sides so an alert cannot "predict" itself.
rare = evh.filter(rare_cond)
inc = rare.select("label", "node", "hr").distinct().cache()
st = (inc.groupBy("label").agg(F.count("*").alias("n_inc"), F.countDistinct("node").alias("n_nodes"))
      .join(rare.groupBy("label").count().withColumnRenamed("count", "alerts"), "label"))
replace("rs_label_stats", [{"label": r["label"], "alerts": int(r["alerts"]), "incidents": int(r["n_inc"]),
                            "nodes": int(r["n_nodes"])} for r in st.collect()])
nonalert = evh.filter(~F.col("is_alert"))
keys = inc.select("node", (F.col("hr") - HOUR).alias("hr")).distinct()
pre = (nonalert.join(F.broadcast(keys), ["node", "hr"], "left_semi")
       .select("node", "hr", "template_id").distinct())
pre_counts = (inc.select("label", "node", (F.col("hr") - HOUR).alias("pre_hr"))
              .join(pre.withColumnRenamed("hr", "pre_hr"), ["node", "pre_hr"])
              .groupBy("label", "template_id").agg(F.count("*").alias("k"))
              .filter(F.col("k") >= MIN_SUPPORT).cache())
lap(f"candidate (label, template) pairs with k>={MIN_SUPPORT}: {pre_counts.count():,}")

lab_nodes = inc.select("label", "node").distinct()
pres = (nonalert.join(F.broadcast(lab_nodes.select("node").distinct()), "node", "left_semi")
        .join(F.broadcast(pre_counts.select("template_id").distinct()), "template_id", "left_semi")
        .select("node", "hr", "template_id").distinct()
        .groupBy("node", "template_id").agg(F.count("*").alias("hours_present")))
base = pres.join(lab_nodes, "node").groupBy("label", "template_id").agg(F.sum("hours_present").alias("base_hours"))
mm = evh.agg(F.min("hr").alias("lo"), F.max("hr").alias("hi")).first()
total_hours = int((mm["hi"] - mm["lo"]) // HOUR + 1)
nn = (evh.select("node", "hr").distinct().join(F.broadcast(lab_nodes), "node")
      .groupBy("label").agg(F.count("*").alias("active_node_hours")))
res = (pre_counts.join(base, ["label", "template_id"], "left").join(nn, "label")
       .join(st.select("label", "n_inc"), "label"))
n_null = res.filter(F.col("base_hours").isNull()).count()
if n_null: print(f"WARNING: {n_null} candidate rows had no baseline and are dropped")
res = (res.filter(F.col("base_hours").isNotNull())
       .withColumn("p_pre", F.col("k") / F.col("n_inc"))
       .withColumn("p_base", F.col("base_hours") / F.col("active_node_hours"))
       .withColumn("lift", F.col("p_pre") / F.col("p_base"))
       .withColumn("expected", F.col("n_inc") * F.col("p_base")))
res = (res.withColumn("rk", F.row_number().over(Window.partitionBy("label").orderBy(F.desc("lift"))))
       .filter(F.col("rk") <= KEEP_PER_LABEL).join(tpl, "template_id", "left"))
docs = [{"label": r["label"], "template_id": int(r["template_id"]), "template": (r["template"] or "")[:300],
         "k": int(r["k"]), "n_inc": int(r["n_inc"]), "p_pre": float(r["p_pre"]), "p_base": float(r["p_base"]),
         "lift": float(r["lift"]), "expected": float(r["expected"])} for r in res.collect()]
replace("rs_precursors", docs)
db.rs_precursors.create_index("label"); db.rs_rare_alerts.create_index("epoch")
db.rs_hourly.create_index("hour_epoch"); db.rs_storms.create_index("day")
print("total_hours used for baseline:", total_hours)
lap("ALL DONE")
spark.stop()
