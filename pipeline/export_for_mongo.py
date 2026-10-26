from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder.master("local[8]").appName("export-mongo").config("spark.driver.memory","8g").getOrCreate()
BASE = "hdfs://localhost:9000/processed/thunderbird"
OUT = "file:///home/vs/SEMESTER 7/bigdata/project/mongo_export"

tp = spark.read.parquet(BASE + "/templates_with_samples") \
    .withColumnRenamed("template_id", "_id") \
    .withColumn("_id", F.col("_id").cast("string"))
tp.write.mode("overwrite").json(OUT + "/templates")

al = spark.read.parquet(BASE + "/alerts").drop("is_alert")
al.write.mode("overwrite").json(OUT + "/alerts")

nd = spark.read.parquet(BASE + "/node_daily") \
    .withColumn("_id", F.concat_ws("_", "node", F.date_format("day", "yyyy-MM-dd")))
nd.write.mode("overwrite").json(OUT + "/node_daily")

print("done")
spark.stop()
