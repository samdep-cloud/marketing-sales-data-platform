
import json
import os
import boto3

s3 = boto3.client("s3")

BUCKET_NAME = os.environ["BRONZE_BUCKET"]

def lambda_handler(event, context):
    # Parse incoming webhook
    body = event["body"]
    calendly_event = json.loads(body)

    event_type = calendly_event["event"]
    payload = calendly_event["payload"]

    # Process only invitee.created events
    if event_type != "invitee.created":
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Event ignored"})
        }

    # Extract invitee ID from Calendly URI
    invitee_uri = payload["uri"]
    invitee_id = invitee_uri.rstrip("/").split("/")[-1]

    # Persist original webhook payload to S3
    object_key = f"bronze/calendly/invitee_{invitee_id}.json"

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=object_key,
        Body=json.dumps(calendly_event),
        ContentType="application/json"
    )

    # Return successful response
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Calendly event received",
            "invitee_id": invitee_id
        })
    }

