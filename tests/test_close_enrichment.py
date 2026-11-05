import json
from io import BytesIO
from unittest.mock import MagicMock, patch
import os

os.environ["BRONZE_BUCKET"] = "test-bronze-bucket"
os.environ["ENRICHED_BUCKET"] = "test-enriched-bucket"
os.environ["LEAD_OWNER_BUCKET"] = "test-owner-bucket"
os.environ["SLACK_WEBHOOK_URL"] = "https://example.com/test-slack"

from src.enrichment import close_enrichment


def test_close_enrichment(monkeypatch):
    # Fictional SQS event
    sqs_event = {
        "Records": [
            {
                "body": json.dumps({
                    "lead_id": "lead_123",
                    "event_id": "ev_456",
                    "s3_key": "bronze/close/crm_event_lead_123.json"
                })
            }
        ]
    }

    # Fictional CRM record
    crm_event = {
        "event": {
            "id": "ev_456",
            "data": {
                "id": "lead_123",
                "display_name": "Test Lead",
                "date_created": "2026-10-15",
                "status_label": "Potential"
            }
        }
    }

    owner_data = {
        "lead_email": "test@example.com",
        "lead_owner": "Test Owner",
        "funnel": "Direct VSL"
    }

    # Lambda configuration
    monkeypatch.setenv("BRONZE_BUCKET", "test-bronze-bucket")
    monkeypatch.setenv("ENRICHED_BUCKET", "test-enriched-bucket")
    monkeypatch.setenv("LEAD_OWNER_BUCKET", "test-owner-bucket")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://example.com/test-slack")

    mock_s3 = MagicMock()
    mock_s3.get_object.return_value = {
        "Body": BytesIO(json.dumps(crm_event).encode("utf-8"))
    }

    # Mock external services
    with (
        patch.object(close_enrichment, "s3", mock_s3),
        patch.object(close_enrichment.requests, "get") as mock_get,
        patch.object(close_enrichment.requests, "post") as mock_post,
    ):
        mock_get.return_value.json.return_value = owner_data
        mock_get.return_value.raise_for_status.return_value = None
        mock_post.return_value.raise_for_status.return_value = None

        # Execute Lambda
        close_enrichment.lambda_handler(sqs_event, None)

    # Verify enriched S3 output
    mock_s3.put_object.assert_called_once()

    saved_object = mock_s3.put_object.call_args.kwargs
    enriched_lead = json.loads(saved_object["Body"])

    assert saved_object["Bucket"] == "test-enriched-bucket"
    assert enriched_lead["lead_id"] == "lead_123"
    assert enriched_lead["display_name"] == "Test Lead"
    assert enriched_lead["lead_email"] == "test@example.com"
    assert enriched_lead["lead_owner"] == "Test Owner"
    assert enriched_lead["funnel"] == "Direct VSL"

    # Verify notification was attempted
    mock_post.assert_called_once()