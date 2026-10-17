
import os
import json
import requests
import boto3

from pathlib import Path
from dotenv import load_dotenv


# -------------------------------------------------------------------
# CONFIGURATION
#
# Load local environment variables.
# AWS Glue will use job configuration instead of a local .env file.

project_root = Path(__file__).resolve().parents[2]
load_dotenv(project_root / ".env")

INDEX_URL = os.environ["INDEX_URL"]
BRONZE_BUCKET = os.environ["BRONZE_BUCKET"]

print(f"INDEX_URL: {INDEX_URL}")

s3 = boto3.client("s3")


# -------------------------------------------------------------------
# FUNCTION 1: FETCH AVAILABLE SPEND FILES
#
# The public S3 file index lists daily JSON filenames.
# Each file contains marketing spend by channel and date.
#
# The index allows us to discover available files without
# guessing dates or constructing nonexistent filenames.

def fetch_file_index():

    response = requests.get(INDEX_URL, timeout=30)
    response.raise_for_status()

    return response.json()["files"]


# -------------------------------------------------------------------
# FUNCTION 2: INGEST NEW SPEND FILES
#
# Checks whether each source file already exists in our Bronze bucket.
# Downloads and saves only files that have not been ingested.
#
# This provides simple file-level incremental ingestion.

def ingest_spend_files(filenames):

    ingested = 0
    skipped = 0

    base_url = INDEX_URL.rsplit("/", 1)[0]

    for filename in filenames:

        object_key = f"bronze/spend/{filename}"

        # Check whether this file already exists in Bronze.
        try:
            s3.head_object(
                Bucket=BRONZE_BUCKET,
                Key=object_key
            )

            print(f"Skipping existing file: {filename}")
            skipped += 1
            continue

        except s3.exceptions.ClientError as error:
            # A 404 means the file does not exist yet.
            # Other errors should not be silently ignored.
            status = error.response["Error"]["Code"]

            if status not in ("404", "NoSuchKey", "NotFound"):
                raise

        # Retrieve the source JSON file.
        file_url = f"{base_url}/{filename}"

        response = requests.get(file_url, timeout=30)
        response.raise_for_status()

        records = response.json()

        # Preserve the source data in S3 Bronze.
        s3.put_object(
            Bucket=BRONZE_BUCKET,
            Key=object_key,
            Body=json.dumps(records),
            ContentType="application/json"
        )

        print(f"Ingested {filename}: {len(records)} records")
        ingested += 1

    return ingested, skipped


# -------------------------------------------------------------------
# MAIN: DAILY MARKETING SPEND INGESTION
#
# 1. Retrieve the public file index.
# 2. Identify files not yet present in S3 Bronze.
# 3. Download and save new files.
#
# Initial run: Historical backfill of indexed files.
# Daily runs: Only newly available files are ingested.

def main():

    filenames = fetch_file_index()

    print(f"Available spend files: {len(filenames)}")

    ingested, skipped = ingest_spend_files(filenames)

    print(
        f"Spend ingestion complete: "
        f"{ingested} ingested, {skipped} skipped"
    )


if __name__ == "__main__":
    main()

