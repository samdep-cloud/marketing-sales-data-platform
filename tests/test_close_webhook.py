import json
import os
from unittest.mock import patch, MagicMock

# Test configuration
os.environ["BRONZE_BUCKET"] = "test-bronze-bucket"
os.environ["CLOSE_QUEUE_URL"] = (
    "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
)
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

# Mock AWS clients before importing Lambda
with patch("boto3.client") as mock_boto3_client:
    mock_s3 = MagicMock()
    mock_sqs = MagicMock()
    mock_boto3_client.side_effect = [mock_s3, mock_sqs]

    from src.ingestion.close_webhook import lambda_handler


def test_close_webhook():
    # Fictional Close CRM event
    crm_event = {
        "event": {
            "id": "ev_test_456",
            "action": "created",
            "object_type": "lead",
            "data": {
                "id": "lead_test_123",
                "display_name": "Test Lead",
                "date_created": "2026-10-15",
                "status_label": "Potential"
            }
        }
    }

    # Simulate API Gateway request
    api_gateway_event = {
        "body": json.dumps(crm_event)
    }

    # Execute Lambda
    response = lambda_handler(api_gateway_event, None)

    # Verify HTTP response
    assert response["statusCode"] == 200

    # Verify S3 upload
    mock_s3.put_object.assert_called_once()
    s3_args = mock_s3.put_object.call_args.kwargs

    assert s3_args["Bucket"] == "test-bronze-bucket"
    assert s3_args["Key"] == "bronze/close/crm_event_lead_test_123.json"
    assert json.loads(s3_args["Body"]) == crm_event

    # Verify SQS message
    mock_sqs.send_message.assert_called_once()
    sqs_args = mock_sqs.send_message.call_args.kwargs
    message = json.loads(sqs_args["MessageBody"])

    assert message["lead_id"] == "lead_test_123"
    assert message["event_id"] == "ev_test_456"
    assert message["s3_key"] == s3_args["Key"]
    assert sqs_args["DelaySeconds"] == 600