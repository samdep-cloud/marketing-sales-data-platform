import json
import os
from unittest.mock import patch, MagicMock

# Set environment variable before importing Lambda
os.environ["BRONZE_BUCKET"] = "test-bucket"

# Mock boto3 before importing Lambda
with patch("boto3.client") as mock_client:
    mock_s3 = MagicMock()
    mock_client.return_value = mock_s3

    from src.ingestion.calendly_webhook import lambda_handler


def test_calendly_webhook():
    # Fictional Calendly webhook payload
    sample_event = {
        "event": "invitee.created",
        "payload": {
            "uri": "https://api.calendly.com/scheduled_events/test-event/invitees/test-invitee",
            "name": "Test User",
            "email": "test@example.com",
        },
    }

    # Simulate API Gateway request
    event = {
        "body": json.dumps(sample_event)
    }

    # Invoke Lambda handler
    response = lambda_handler(event, None)

    # Verify successful response
    assert response["statusCode"] == 200

    # Verify S3 upload
    mock_s3.put_object.assert_called_once()

    # Inspect uploaded object
    call_args = mock_s3.put_object.call_args.kwargs

    assert call_args["Bucket"] == "test-bucket"
    assert call_args["Key"] == "bronze/calendly/invitee_test-invitee.json"
    assert json.loads(call_args["Body"]) == sample_event