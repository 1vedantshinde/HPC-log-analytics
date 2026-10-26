from pyspark.sql import SparkSession, functions as F, Window

spark = SparkSession.builder.master("local[8]").appName("mongo-exports").config("spark.driver.memory","8g").getOrCreate()

BASE = "hdfs://localhost:9000/processed/thunderbird"
ev = spark.read.parquet(BASE + "/events")

print("Building daily node summary...")
daily = (ev.groupBy("node", F.date_trunc("day", "ts").alias("day"))
           .agg(F.count("*").alias("lines"),
                F.sum(F.col("is_alert").cast("int")).alias("alerts"),
                F.countDistinct("template_id").alias("distinct_templates")))
daily.write.mode("overwrite").parquet(BASE + "/node_daily")
print("node_daily rows:", daily.count())

print("Building template sample messages...")
w = Window.partitionBy("template_id").orderBy(F.rand(seed=42))
sampled = (ev.withColumn("rn", F.row_number().over(w))
             .filter(F.col("rn") <= 5)
             .groupBy("template_id")
             .agg(F.collect_list("msg").alias("sample_msgs")))

tp = spark.read.parquet(BASE + "/templates")
tp_with_samples = tp.join(sampled, "template_id", "left")
tp_with_samples.write.mode("overwrite").parquet(BASE + "/templates_with_samples")
print("templates_with_samples rows:", tp_with_samples.count())

spark.stop()
