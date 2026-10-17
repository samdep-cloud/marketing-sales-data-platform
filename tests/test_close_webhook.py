import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Dummy configuration for local testing only
os.environ["BRONZE_BUCKET"] = "test-bronze-bucket"
os.environ["CLOSE_QUEUE_URL"] = (
    "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
)
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

# Create fake AWS clients BEFORE importing our Lambda
with patch("boto3.client") as mock_boto3_client:
    mock_s3 = MagicMock()
    mock_sqs = MagicMock()

    mock_boto3_client.side_effect = [mock_s3, mock_sqs]

    from src.ingestion.close_webhook import lambda_handler


def test_close_webhook():

    # Load our actual Close CRM sample payload
    sample_path = (
        Path(__file__).resolve().parents[1]
        / "sample_data"
        / "close"
        / "close_crm_event.json"
    )

    with open(sample_path, "r") as file:
        crm_event = json.load(file)

    # Simulate the HTTP request passed through API Gateway
    api_gateway_event = {
        "body": json.dumps(crm_event)
    }

    # Execute the Lambda handler locally
    response = lambda_handler(api_gateway_event, None)

    # Verify the HTTP response
    assert response["statusCode"] == 200

    # Verify S3 was called
    mock_s3.put_object.assert_called_once()

    # Verify SQS was called
    mock_sqs.send_message.assert_called_once()

    # Inspect the actual arguments passed to S3 and SQS
    print("\nLambda response:", response)
    print("\nS3 arguments:", mock_s3.put_object.call_args)
    print("\nSQS arguments:", mock_sqs.send_message.call_args)


if __name__ == "__main__":
    test_close_webhook()