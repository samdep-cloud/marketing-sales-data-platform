
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Set environment variable before importing Lambda
os.environ["BRONZE_BUCKET"] = "test-bucket"

# Mock boto3 before importing Lambda
with patch("boto3.client") as mock_client:
    mock_s3 = MagicMock()
    mock_client.return_value = mock_s3

    from src.ingestion.calendly_webhook import lambda_handler


def test_calendly_webhook():
    # Load sample Calendly payload
    project_root = Path(__file__).resolve().parents[1]
    sample_path = project_root / "sample_data" / "calendly" / "calendly_event.json"

    with open(sample_path, "r") as file:
        sample_event = json.load(file)

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
    assert call_args["Key"].startswith("bronze/calendly/invitee_")
    assert json.loads(call_args["Body"]) == sample_event
