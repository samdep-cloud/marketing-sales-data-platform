
import os
import json
import requests
import boto3

from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone


# -------------------------------------------------------------------
# CONFIGURATION
#
# Load local environment variables from .env.
# In AWS Glue, these values will come from the job configuration
# and a secure token store rather than a local .env file.

project_root = Path(__file__).resolve().parents[2]
load_dotenv(project_root / ".env")

WISTIA_API_TOKEN = os.environ["WISTIA_API_TOKEN"]
BRONZE_BUCKET = os.environ["BRONZE_BUCKET"]

TARGET_MEDIA_IDS = ["8hunphufxp", "9k4tbcdfg0"]

BASE_URL = "https://api.wistia.com/modern"

HEADERS = {
    "Authorization": f"Bearer {WISTIA_API_TOKEN}",
    "X-Wistia-API-Version": "2026-09"
}

s3 = boto3.client("s3")


# -------------------------------------------------------------------
# FUNCTION 1: FETCH MEDIA METADATA
#
# Retrieves information about ONE specific Wistia video.
#
# Media metadata describes WHAT the video is, including
# its ID, title, creation date, and other attributes.
#
# We call this function once for each required media ID.
# No account-wide pagination is needed.

def fetch_media(media_id):

    url = f"{BASE_URL}/medias/{media_id}"

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


# -------------------------------------------------------------------
# FUNCTION 2: FETCH MEDIA ENGAGEMENT STATISTICS
#
# Retrieves aggregate performance metrics for ONE video.
#
# These include measures such as plays, loads, play rate,
# and engagement, depending on the API response.
#
# Refresh daily because existing videos continue to
# accumulate views and engagement.

def fetch_media_stats(media_id):

    url = f"{BASE_URL}/stats/medias/{media_id}"

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


# -------------------------------------------------------------------
# FUNCTION 3: FETCH VIDEO VIEWING EVENTS
#
# Retrieves individual viewing events for ONE video.
#
# Unlike aggregate statistics, these records represent
# viewing activity and may contain visitor identifiers,
# engagement details, and other event attributes.
#
# Uses:
# - media_id: Restricts events to the requested video
# - start_date/end_date: Restricts the activity period
# - page/per_page: Retrieves all pages of matching events
#
# Wistia retains viewing events for up to two years.

def fetch_visitors(media_id, start_date, end_date):

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
            raise ValueError(
                "Unexpected Wistia events response format"
            )

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


# -------------------------------------------------------------------
# HELPER: SAVE RAW DATA TO S3 BRONZE
#
# Saves each dataset separately as a timestamped JSON file.
# Bronze preserves the raw API responses for later processing.

def save_to_s3(dataset, records, timestamp):

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


# -------------------------------------------------------------------
# MAIN: DAILY WISTIA BATCH INGESTION
#
# Processes only the two videos required by the assignment.
#
# 1. Refresh video metadata
# 2. Refresh aggregate engagement statistics
# 3. Retrieve viewing events within the configured date window
# 4. Save each dataset separately to S3 Bronze
#
# Daily event ingestion uses a two-day overlapping window.
# An optional WISTIA_START_DATE allows a historical backfill.
#
# Silver will deduplicate overlapping event records.
# Gold will recalculate reporting metrics.

def main():

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

    # Initial historical backfill: Wistia retains up to 2 years of events.
    start_date = (
        datetime.now(timezone.utc) - timedelta(days=730)
    ).date().isoformat()

    end_date = datetime.now(timezone.utc).date().isoformat()

    media_records = []
    stats_records = []
    visitor_events = []

    # Process only the two required Wistia videos
    for media_id in TARGET_MEDIA_IDS:

        print(f"Processing media: {media_id}", flush=True)

        # -----------------------------------------------------------
        # DATASET 1: MEDIA METADATA
        # Describes the video: ID, title, creation date, etc.

        media = fetch_media(media_id)
        media_records.append(media)

        # -----------------------------------------------------------
        # DATASET 2: MEDIA ENGAGEMENT STATISTICS
        # Aggregate plays, watch time, play rate, etc.

        stats = fetch_media_stats(media_id)

        stats_records.append({
            "media_id": media_id,
            "stats": stats
        })

        # -----------------------------------------------------------
        # DATASET 3: VISITOR VIEWING EVENTS
        # Individual viewing activity for this video.
        # Restricted to January 1, 2026 through today.

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

    # ---------------------------------------------------------------
    # SAVE ALL THREE DATASETS TO S3 BRONZE

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


# -------------------------------------------------------------------

if __name__ == "__main__":
    result = main()
    print(result)