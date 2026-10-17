import json
import sys
from pathlib import Path
from io import BytesIO
from unittest.mock import patch, MagicMock

# Testing samples 

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

# ----------------------------------------------------------------------------
# Imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "enrichment"))

from src.enrichment import close_enrichment

def test_close_enrichment(monkeypatch):

    # 1. Set the Lambda environment variables
    monkeypatch.setenv("BRONZE_BUCKET", "test-bronze-bucket")
    monkeypatch.setenv("ENRICHED_BUCKET", "test-enriched-bucket")

    # 2. Import our actual Lambda   
    from src.enrichment import close_enrichment

    # 3. Create fake responses for external services
    mock_s3 = MagicMock()

    mock_s3.get_object.return_value = {
        "Body": BytesIO(json.dumps(crm_event).encode("utf-8"))
    }

    owner_data = {
        "lead_email": "test@example.com",
        "lead_owner": "Test Owner",
        "funnel": "Direct VSL"
    }

    # 4. Replace the real S3 and HTTP calls
    with patch.object(close_enrichment, "s3", mock_s3), \
         patch.object(close_enrichment.requests, "get") as mock_get:

        mock_get.return_value.json.return_value = owner_data

        # 5. Run our ACTUAL Lambda handler
        close_enrichment.lambda_handler(sqs_event, None)

    # 6. Examine what the Lambda attempted to write to S3
    mock_s3.put_object.assert_called_once()

    saved_object = mock_s3.put_object.call_args.kwargs
    enriched_lead = json.loads(saved_object["Body"])

    assert saved_object["Bucket"] == "test-enriched-bucket"
    assert enriched_lead["lead_id"] == "lead_123"
    assert enriched_lead["display_name"] == "Test Lead"
    assert enriched_lead["lead_email"] == "test@example.com"
    assert enriched_lead["lead_owner"] == "Test Owner"
    assert enriched_lead["funnel"] == "Direct VSL"