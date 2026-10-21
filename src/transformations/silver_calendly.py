
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

BRONZE_PATH = "s3://sdep-marketing-sales-data-platform/bronze/calendly/"
SILVER_PATH = "s3://sdep-marketing-sales-data-platform/silver/calendly/bookings/"

spark = SparkSession.builder.appName("silver-calendly").getOrCreate()

df = spark.read.option("multiLine", "true").json(BRONZE_PATH)

# Keep invitee creation events and flatten the payload
df = df.filter(F.col("event") == "invitee.created")

df = df.select(
    F.regexp_extract("payload.uri", r"/invitees/([^/]+)$", 1).alias("invitee_id"),
    F.regexp_extract("payload.scheduled_event.uri", r"/scheduled_events/([^/]+)$", 1).alias("event_id"),
    F.lower(F.trim(F.col("payload.email"))).alias("email"),
    F.to_timestamp("payload.created_at").alias("created_at"),
    F.to_timestamp("payload.updated_at").alias("updated_at"),
    F.to_timestamp("payload.scheduled_event.start_time").alias("meeting_start"),
    F.to_timestamp("payload.scheduled_event.end_time").alias("meeting_end"),
    F.col("payload.name").alias("invitee_name"),
    F.col("payload.event_type").alias("event_type_id"),
    F.col("payload.tracking.utm_source").alias("utm_source"),
    F.col("payload.rescheduled").alias("rescheduled"),
    F.col("payload.status").alias("status"),
    F.col("payload.scheduled_event.event_memberships").getItem(0).getField("user_name").alias("employee_name"),
)

df = df.filter(
    F.col("invitee_id").isNotNull()
    & (F.col("invitee_id") != "")
)

# Retain the most recently updated record for each invitee
window = Window.partitionBy("invitee_id").orderBy(
    F.col("updated_at").desc_nulls_last()
)

df = (
    df.withColumn("row_num", F.row_number().over(window))
      .filter(F.col("row_num") == 1)
      .drop("row_num")
)

df.write.mode("overwrite").parquet(SILVER_PATH)

print(f"Silver Calendly complete: {df.count()} bookings written")
