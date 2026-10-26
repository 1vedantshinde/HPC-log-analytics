import sys, time
from pyspark.sql import SparkSession, functions as F
from masking import mask

path = sys.argv[1] if len(sys.argv) > 1 else "hdfs://localhost:9000/raw/thunderbird/2006-W28/part-0.log"
spark = (SparkSession.builder.master("local[8]").appName("tbird-parse-test")
         .config("spark.driver.memory", "8g")
         .config("spark.sql.shuffle.partitions", "32").getOrCreate())
spark.sparkContext.setLogLevel("WARN")
t0 = time.time()

raw = spark.read.text(path)
p = F.split("value", r"\s+", 9)
PROG = r"^([^\s\[:]+)(?:\[(\d+)\])?:\s?(.*)$"
df = (raw.select("value", p.getItem(0).alias("label"), p.getItem(1).alias("epoch"),
                 p.getItem(3).alias("node"), p.getItem(8).alias("rest"))
      .withColumn("valid", F.coalesce(F.col("epoch").rlike(r"^\d+$") & F.col("rest").isNotNull(), F.lit(False)))
      .withColumn("prog", F.regexp_extract("rest", PROG, 1))
      .withColumn("msg", F.when(F.col("prog") == "", F.col("rest")).otherwise(F.regexp_extract("rest", PROG, 3)))
      .withColumn("alert", F.col("label") != "-"))
df = df.withColumn("template", F.concat_ws(": ", F.when(F.col("prog") == "", F.lit("(none)")).otherwise(F.col("prog")), mask(F.col("msg")))).cache()

total = df.count()
bad = df.filter(~F.col("valid")).count()
print(f"\ntotal={total:,}  bad_header={bad:,}")
tpl = df.filter("valid").groupBy("template").agg(F.count("*").alias("n"), F.sum(F.col("alert").cast("int")).alias("alerts")).cache()
nt = tpl.count(); once = tpl.filter("n = 1").count()
print(f"BASELINE (old masking): templates=18,465  singletons=15,798 (85.6%)  lines_in_singletons=1.73%")
print(f"NEW:                    templates={nt:,}  singletons={once:,} ({once/nt:.1%})  lines_in_singletons={once/total:.2%}")
print("\n--- alert templates ---")
tpl.filter("alerts > 0").orderBy(F.desc("alerts")).show(15, 120, False)
print("--- singleton samples ---")
frac = min(1.0, 40 / max(once, 1))
tpl.filter("n = 1").select("template").sample(False, frac, seed=1).limit(40).show(40, 180, False)
print(f"elapsed {time.time()-t0:.1f}s")
