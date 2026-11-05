
import os
import sys
import json
from pathlib import Path

import boto3
import requests
from dotenv import load_dotenv


# Configuration: local development uses .env; AWS Glue uses job parameters.
if "--INDEX_URL" in sys.argv:
    from awsglue.utils import getResolvedOptions

    args = getResolvedOptions(
        sys.argv,
        ["INDEX_URL", "BRONZE_BUCKET"]
    )

    INDEX_URL = args["INDEX_URL"]
    BRONZE_BUCKET = args["BRONZE_BUCKET"]

else:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")

    INDEX_URL = os.environ["INDEX_URL"]
    BRONZE_BUCKET = os.environ["BRONZE_BUCKET"]


s3 = boto3.client("s3")


def fetch_file_index():
    """Retrieve available marketing spend filenames from the source index."""
    response = requests.get(INDEX_URL, timeout=30)
    response.raise_for_status()

    return response.json()["files"]


def ingest_spend_files(filenames):
    """Ingest source files not already present in S3 Bronze."""
    ingested = 0
    skipped = 0

    base_url = INDEX_URL.rsplit("/", 1)[0]

    for filename in filenames:
        object_key = f"bronze/spend/{filename}"

        # Skip files already ingested.
        try:
            s3.head_object(
                Bucket=BRONZE_BUCKET,
                Key=object_key
            )

            print(f"Skipping existing file: {filename}")
            skipped += 1
            continue

        except s3.exceptions.ClientError as error:
            status = error.response["Error"]["Code"]

            if status not in ("404", "NoSuchKey", "NotFound"):
                raise

        # Retrieve source data.
        file_url = f"{base_url}/{filename}"

        response = requests.get(file_url, timeout=30)
        response.raise_for_status()

        records = response.json()

        # Preserve source records in S3 Bronze.
        s3.put_object(
            Bucket=BRONZE_BUCKET,
            Key=object_key,
            Body=json.dumps(records),
            ContentType="application/json"
        )

        print(f"Ingested {filename}: {len(records)} records")
        ingested += 1

    return ingested, skipped


def main():
    """Run incremental marketing spend ingestion."""
    filenames = fetch_file_index()

    print(f"Available spend files: {len(filenames)}")

    ingested, skipped = ingest_spend_files(filenames)

    print(
        f"Spend ingestion complete: "
        f"{ingested} ingested, {skipped} skipped"
    )


if __name__ == "__main__":
    main()
