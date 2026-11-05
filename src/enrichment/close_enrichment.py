
import os
import json

import boto3
import requests


s3 = boto3.client("s3")

BRONZE_BUCKET = os.environ["BRONZE_BUCKET"]
ENRICHED_BUCKET = os.environ["ENRICHED_BUCKET"]
LEAD_OWNER_BUCKET = os.environ["LEAD_OWNER_BUCKET"]


def send_slack_notification(enriched_lead):
    """Notify the team when a new lead has been enriched."""
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]

    message = {
        "text": (
            "*New Lead Alert*\n"
            f"Name: {enriched_lead['display_name']}\n"
            f"Lead ID: {enriched_lead['lead_id']}\n"
            f"Created Date: {enriched_lead['date_created']}\n"
            f"Label: {enriched_lead['status_label']}\n"
            f"Email: {enriched_lead['lead_email']}\n"
            f"Lead Owner: {enriched_lead['lead_owner']}\n"
            f"Funnel: {enriched_lead['funnel']}"
        )
    }

    response = requests.post(
        webhook_url,
        json=message,
        timeout=10
    )
    response.raise_for_status()


def lambda_handler(event, context):
    """Enrich queued Close leads and notify the team via Slack."""

    for record in event["Records"]:
        message = json.loads(record["body"])

        lead_id = message["lead_id"]
        s3_key = message["s3_key"]

        # Retrieve additional lead attributes from the external lookup.
        file_name = f"{lead_id}.json"
        lookup_url = (
            f"https://{LEAD_OWNER_BUCKET}.s3.us-east-1.amazonaws.com/"
            f"{file_name}"
        )

        response = requests.get(lookup_url, timeout=30)
        response.raise_for_status()
        owner_data = response.json()

        # Retrieve the original Close CRM event from Bronze.
        s3_response = s3.get_object(
            Bucket=BRONZE_BUCKET,
            Key=s3_key
        )

        crm_event = json.loads(s3_response["Body"].read())
        lead_data = crm_event["event"]["data"]

        # Combine CRM attributes with the lead-owner lookup.
        enriched_lead = {
            "lead_id": lead_data["id"],
            "display_name": lead_data["display_name"],
            "date_created": lead_data["date_created"],
            "status_label": lead_data["status_label"],
            "lead_email": owner_data["lead_email"],
            "lead_owner": owner_data["lead_owner"],
            "funnel": owner_data["funnel"]
        }

        # Persist the enriched record.
        object_key = f"close/enriched_lead_{lead_id}.json"

        s3.put_object(
            Bucket=ENRICHED_BUCKET,
            Key=object_key,
            Body=json.dumps(enriched_lead),
            ContentType="application/json"
        )

        # Notify Slack after successful enrichment.
        send_slack_notification(enriched_lead)

    return {"message": "Enrichment completed"}

