import shutil, sys

PATCHES = {
 "add_indexes.py": [
  ('"node_daily": ["rs_node_day"], "templates": ["rs_n_desc"]}', '"node_daily": ["rs_node_day"]}'),
  ('db.templates.create_index([("n", D)], name="rs_n_desc")', 'pass'),
  ('("alerts count label=VAPI", lambda: db.alerts.count_documents({"label": "VAPI"})),',
   '("alerts label=VAPI sort ts desc limit 50", lambda: list(db.alerts.find({"label": "VAPI"}).sort("ts", -1).limit(50))),\n'
   '    ("alerts count label=VAPI", lambda: db.alerts.count_documents({"label": "VAPI"})),'),
 ],
 "research_analyses.py": [
  ('HOUR = 3600', 'HOUR = 3600\nDAY_TZ = os.environ.get("DAY_TZ", "UTC")'),
  ('dayc = F.date_format("ts", "yyyy-MM-dd")',
   'dayc = F.date_format(F.from_utc_timestamp("ts", DAY_TZ), "yyyy-MM-dd")'),
  ('"dominant_label": DOMINANT,', '"dominant_label": DOMINANT, "day_tz": DAY_TZ,'),
  ('nn = lab_nodes.groupBy("label").agg(F.count("*").alias("lnodes"))',
   'nn = (evh.select("node", "hr").distinct().join(F.broadcast(lab_nodes), "node")\n'
   '      .groupBy("label").agg(F.count("*").alias("active_node_hours")))'),
  ('.withColumn("p_base", F.col("base_hours") / (F.col("lnodes") * F.lit(total_hours)))',
   '.withColumn("p_base", F.col("base_hours") / F.col("active_node_hours"))'),
 ],
 "pages/1_Research_Findings.py": [
  ("(all times UTC)", "(replay in UTC; storm days bucketed in {meta.get('day_tz', 'UTC')})"),
 ],
}

new = {}
for path, edits in PATCHES.items():
    s = open(path).read()
    for old, rep in edits:
        c = s.count(old)
        if c != 1:
            sys.exit(f"{path}: expected exactly 1 match, found {c} for: {old!r}. Nothing was changed.")
        s = s.replace(old, rep)
    new[path] = s
for path, s in new.items():
    shutil.copy(path, path + ".bak")
    open(path, "w").write(s)
    print("patched", path, "(backup:", path + ".bak)")
