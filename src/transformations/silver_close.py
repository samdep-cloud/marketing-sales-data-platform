from pyspark.sql import SparkSession
from pyspark.sql import functions as F

BRONZE_PATH = "s3://sdep-marketing-sales-enriched/close/"
SILVER_PATH = "s3://sdep-marketing-sales-data-platform/silver/close/leads/"

spark = SparkSession.builder.appName("silver-close").getOrCreate()

# Read enriched Close CRM JSON records
df = spark.read.option("multiLine", "true").json(BRONZE_PATH)

# Select and standardize lead attributes
df = df.select(
    F.col("lead_id"),
    F.trim(F.col("display_name")).alias("display_name"),
    F.lower(F.trim(F.col("lead_email"))).alias("lead_email"),
    F.to_timestamp("date_created").alias("date_created"),
    F.trim(F.col("status_label")).alias("status_label"),
    F.trim(F.col("lead_owner")).alias("lead_owner"),
    F.trim(F.col("funnel")).alias("funnel"),
)

# Remove records without a valid lead ID
df = df.filter(
    F.col("lead_id").isNotNull()
    & (F.trim(F.col("lead_id")) != "")
)

# Remove exact duplicate records
df = df.dropDuplicates()

# Do not arbitrarily select a lead version if attributes conflict
conflicts = (
    df.groupBy("lead_id")
      .count()
      .filter(F.col("count") > 1)
)

if conflicts.limit(1).count() > 0:
    raise ValueError(
        "Conflicting records found for the same lead_id. "
        "A reliable update timestamp is needed to select the latest version."
    )

# Write one record per lead
df.write.mode("overwrite").parquet(SILVER_PATH)

print(f"Silver Close complete: {df.count()} leads written")
