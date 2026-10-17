import os
import json
import requests
import boto3

# {
#     "lead_id": "lead_abc123",
#     "event_id": "evt_456",
#     "s3_key": "bronze/close/crm_event_lead_abc123.json"
# }

# Enriched Lead Alert Requirements --> sent to team via Slack
# Name:  {display_name} - Fetch from the CRM Event data
# Lead ID : {lead_id} - Fetch from the CRM Event data
# Created Date: {date_created} - Fetch from the CRM Event data
# Label: {status_label} - Fetch from the CRM Event data
# Email: {lead_email} - Fetch from the lookup data
# Lead Owner: {lead_owner} - Fetch from the lookup data
# Funnel: {funnel} - Fetch from the lookup data
# Reference : Sending messages using incoming webhooks in Slack

#-------------------------------------------------------------------------------

def send_slack_notification(enriched_lead):
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

# -------------------------------------------------------------------------------

s3 = boto3.client('s3')
BRONZE_BUCKET = os.environ["BRONZE_BUCKET"]
ENRICHED_BUCKET = os.environ["ENRICHED_BUCKET"]

def lambda_handler(event, context):

    # dea-lead-owner data -- lead_email, lead_owner, funnel
    for record in event["Records"]:
        message = json.loads(record["body"])

        # Extract lead_id, s3 key
        lead_id = message["lead_id"]
        s3_key = message["s3_key"]

        bucket_name = "dea-lead-owner"
        file_name = f"{lead_id}.json"

        public_url = f"https://{bucket_name}.s3.us-east-1.amazonaws.com/{file_name}"

        response = requests.get(public_url, timeout=30)
        response.raise_for_status()

        owner_data = response.json()

        # dea crm lead data -- lead_id, display_name, date_created, status_label
        # Retrieve original Close webhook from S3
        s3_response = s3.get_object(
            Bucket=BRONZE_BUCKET,
            Key=s3_key
        )

        crm_event = json.loads(s3_response["Body"].read())

        lead_data = crm_event["event"]["data"]

        enriched_lead = {
            "lead_id": lead_data["id"],
            "display_name": lead_data["display_name"],
            "date_created": lead_data["date_created"],
            "status_label": lead_data["status_label"],
            "lead_email": owner_data["lead_email"],
            "lead_owner": owner_data["lead_owner"],
            "funnel": owner_data["funnel"]

        }

        # Load enriched lead data to s3 enriched bucket
        
        # object key
        object_key = f"close/enriched_lead_{lead_id}.json"

        s3.put_object(
            Bucket=ENRICHED_BUCKET,
            Key=object_key,
            Body=json.dumps(enriched_lead),
            ContentType="application/json"
        )

        # Notify Slack after successful enrichment
        send_slack_notification(enriched_lead)


    return {"message": "Enrichment completed"}





