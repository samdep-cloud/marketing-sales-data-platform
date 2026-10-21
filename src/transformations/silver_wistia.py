
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

BUCKET = "sdep-marketing-sales-data-platform"
BRONZE = f"s3://{BUCKET}/bronze/wistia"
SILVER = f"s3://{BUCKET}/silver/wistia"

spark = SparkSession.builder.appName("silver-wistia").getOrCreate()


def read_bronze(dataset):
    return (
        spark.read
        .option("multiLine", "true")
        .json(f"{BRONZE}/{dataset}/")
    )


# 1. MEDIA: latest record per video
media = read_bronze("media")

media = media.select(
    F.col("hashed_id").alias("media_id"),
    F.col("name").alias("video_name"),
    F.col("duration").cast("double").alias("duration_seconds"),
    F.to_timestamp("created").alias("created_at"),
    F.to_timestamp("updated").alias("updated_at"),
    F.col("folder.name").alias("folder_name"),
)

media_window = Window.partitionBy("media_id").orderBy(
    F.col("updated_at").desc_nulls_last()
)

media = (
    media.filter(F.col("media_id").isNotNull())
    .withColumn("rn", F.row_number().over(media_window))
    .filter(F.col("rn") == 1)
    .drop("rn")
)

media.write.mode("overwrite").parquet(f"{SILVER}/media/")
print(f"Wistia media: {media.count()} records")


# 2. STATS: cumulative snapshot, not additive
stats = read_bronze("stats")

# input_file_name identifies the Bronze snapshot file.
# This assumes filenames sort chronologically.
stats = stats.withColumn("source_file", F.input_file_name())

stats = stats.select(
    "media_id",
    F.col("stats.load_count").cast("long").alias("load_count"),
    F.col("stats.play_count").cast("long").alias("play_count"),
    F.col("stats.play_rate").cast("double").alias("play_rate"),
    F.col("stats.hours_watched").cast("double").alias("hours_watched"),
    F.col("stats.engagement").cast("double").alias("engagement"),
    F.col("stats.visitors").cast("long").alias("visitors"),
    "source_file",
)

stats_window = Window.partitionBy("media_id").orderBy(
    F.col("source_file").desc()
)

stats = (
    stats.withColumn("rn", F.row_number().over(stats_window))
    .filter(F.col("rn") == 1)
    .drop("rn", "source_file")
)

stats.write.mode("overwrite").parquet(f"{SILVER}/stats/")
print(f"Wistia stats: {stats.count()} records")


# 3. VISITORS: deduplicate overlapping ingestion windows
visitors = read_bronze("visitors")

visitors = visitors.select(
    F.col("media_id"),
    F.col("event.event_key").alias("event_key"),
    F.col("event.visitor_key").alias("visitor_key"),
    F.to_timestamp("event.received_at").alias("received_at"),
    F.col("event.percent_viewed").cast("double").alias("percent_viewed"),
    F.col("event.user_agent_details.browser").alias("browser"),
    F.col("event.user_agent_details.mobile").alias("is_mobile"),
)

visitors = (
    visitors.filter(F.col("event_key").isNotNull())
    .dropDuplicates(["media_id", "event_key"])
)

visitors.write.mode("overwrite").parquet(f"{SILVER}/visitors/")
print(f"Wistia visitors: {visitors.count()} records")

print("Silver Wistia complete")
