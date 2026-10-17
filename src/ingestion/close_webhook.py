import json
import os
import boto3

s3 = boto3.client("s3")
sqs = boto3.client("sqs")

# Complete Lambda will:

# Receive the HTTP request from API Gateway
# Parse the JSON body into a dictionary
# Validate that the Close event is a newly created lead
# Extract the lead ID and webhook event ID
# Write the original Close payload to S3
# Queue the event for delayed enrichment using SQS
# Return a successful HTTP response to Close

BUCKET_NAME = os.environ["BRONZE_BUCKET"]
QUEUE_URL = os.environ["CLOSE_QUEUE_URL"]

def lambda_handler(event, context):
    # Parse the incoming webhook
    body = event["body"]
    crm_event = json.loads(body)

    # Extract Close event metadata
    close_event = crm_event["event"]

    event_id = close_event["id"]
    lead_id = close_event["data"]["id"]
    action = close_event["action"]
    object_type = close_event["object_type"]

    # Process only newly created leads
    if action != "created" or object_type != "lead":
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Event ingored"})
        }

    # Persist the original webhook payload
    object_key = f"bronze/close/crm_event_{lead_id}.json"

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=object_key,
        Body=json.dumps(crm_event),
        ContentType="application/json"

    )

    # Queue the lead for delayed enrichment
    sqs.send_message(
        QueueUrl=QUEUE_URL,
        DelaySeconds=600,
        MessageBody=json.dumps({
            "lead_id": lead_id,
            "event_id": event_id,
            "s3_key": object_key
        })

    )

    # Return a success response
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Close event received",
            "lead_id": lead_id
        })
    }