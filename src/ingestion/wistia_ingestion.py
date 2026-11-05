import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

import boto3
import requests
from dotenv import load_dotenv


# Configuration: local development uses .env; AWS Glue uses job parameters.
if "--BRONZE_BUCKET" in sys.argv:
    from awsglue.utils import getResolvedOptions

    args = getResolvedOptions(sys.argv, ["BRONZE_BUCKET"])
    BRONZE_BUCKET = args["BRONZE_BUCKET"]
else:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")
    BRONZE_BUCKET = os.environ["BRONZE_BUCKET"]


def get_wistia_token():
    """Retrieve the Wistia API token from Secrets Manager or local environment."""
    if "--BRONZE_BUCKET" in sys.argv:
        client = boto3.client("secretsmanager", region_name="us-east-1")
        response = client.get_secret_value(SecretId="sdep/wistia/api-token")
        return json.loads(response["SecretString"])["WISTIA_API_TOKEN"]

    return os.environ["WISTIA_API_TOKEN"]


WISTIA_API_TOKEN = get_wistia_token()

TARGET_MEDIA_IDS = ["8hunphufxp", "9k4tbcdfg0"]
BASE_URL = "https://api.wistia.com/modern"

HEADERS = {
    "Authorization": f"Bearer {WISTIA_API_TOKEN}",
    "X-Wistia-API-Version": "2026-09"
}

s3 = boto3.client("s3")


def fetch_media(media_id):
    """Retrieve metadata for a Wistia video."""
    response = requests.get(
        f"{BASE_URL}/medias/{media_id}",
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()

    return response.json()


def fetch_media_stats(media_id):
    """Retrieve cumulative engagement statistics for a Wistia video."""
    response = requests.get(
        f"{BASE_URL}/stats/medias/{media_id}",
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()

    return response.json()


def fetch_visitors(media_id, start_date, end_date):
    """Retrieve all pages of viewing events within the specified date range."""
    url = f"{BASE_URL}/stats/events"

    all_events = []
    page = 1
    per_page = 100

    while True:
        response = requests.get(
            url,
            headers=HEADERS,
            params={
                "media_id": media_id,
                "start_date": start_date,
                "end_date": end_date,
                "page": page,
                "per_page": per_page
            },
            timeout=30
        )
        response.raise_for_status()

        events = response.json()

        if not isinstance(events, list):
            raise ValueError("Unexpected Wistia events response format")

        all_events.extend(events)

        print(
            f"Media {media_id}: page {page}, "
            f"{len(events)} events, "
            f"{len(all_events)} total",
            flush=True
        )

        if len(events) < per_page:
            break

        page += 1

    return all_events


def save_to_s3(dataset, records, timestamp):
    """Preserve API responses as timestamped JSON files in S3 Bronze."""
    object_key = (
        f"bronze/wistia/{dataset}/"
        f"{dataset}_{timestamp}.json"
    )

    s3.put_object(
        Bucket=BRONZE_BUCKET,
        Key=object_key,
        Body=json.dumps(records),
        ContentType="application/json"
    )

    print(f"Saved {len(records)} {dataset} records to S3")

    return object_key


def main():
    """Ingest Wistia metadata, statistics, and recent viewing events."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

    # Overlap daily ingestion windows to capture recent viewing events.
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=2)).date().isoformat()
    end_date = now.date().isoformat()

    media_records = []
    stats_records = []
    visitor_events = []

    for media_id in TARGET_MEDIA_IDS:
        print(f"Processing media: {media_id}", flush=True)

        media = fetch_media(media_id)
        media_records.append(media)

        stats = fetch_media_stats(media_id)
        stats_records.append({
            "media_id": media_id,
            "stats": stats
        })

        events = fetch_visitors(
            media_id,
            start_date,
            end_date
        )

        for event in events:
            visitor_events.append({
                "media_id": media_id,
                "event": event
            })

    # Preserve each source dataset independently for Silver processing.
    save_to_s3("media", media_records, timestamp)
    save_to_s3("stats", stats_records, timestamp)
    save_to_s3("visitors", visitor_events, timestamp)

    print("Wistia ingestion completed successfully.")

    return {
        "media_count": len(media_records),
        "stats_count": len(stats_records),
        "visitor_event_count": len(visitor_events),
        "start_date": start_date,
        "end_date": end_date
    }


if __name__ == "__main__":
    result = main()
    print(result)
