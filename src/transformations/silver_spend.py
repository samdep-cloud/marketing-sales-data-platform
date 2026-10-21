from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

BRONZE_PATH = "s3://sdep-marketing-sales-data-platform/bronze/spend/"
SILVER_PATH = "s3://sdep-marketing-sales-data-platform/silver/spend/"

spark = SparkSession.builder.appName("silver-spend").getOrCreate()

# Read JSON arrays from Bronze
df = spark.read.option("multiLine", "true").json(BRONZE_PATH)

# Standardize columns and types
df = df.select(
    F.to_date("date").alias("date"),
    F.lower(F.trim(F.col("channel"))).alias("channel"),
    F.col("spend").cast("decimal(12,2)").alias("spend"),
)

# Remove invalid records
df = df.filter(
    F.col("date").isNotNull()
    & F.col("channel").isNotNull()
    & F.col("spend").isNotNull()
)

# Deduplicate identical records
df = df.dropDuplicates(["date", "channel", "spend"])

# Detect conflicting values for the same date/channel
conflicts = (
    df.groupBy("date", "channel")
    .count()
    .filter(F.col("count") > 1)
)

if conflicts.limit(1).count() > 0:
    raise ValueError(
        "Conflicting spend amounts found for the same date/channel."
    )

# One record per date and channel
df = df.dropDuplicates(["date", "channel"])

# Write Silver as Parquet
df.write.mode("overwrite").parquet(SILVER_PATH)

print(f"Silver Spend complete: {df.count()} records written")