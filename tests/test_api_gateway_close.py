import requests

url = "https://jn5izdmsii.execute-api.us-east-1.amazonaws.com/close"


test_payload = {
    "event": {
        "id": "ev_api_test_002",
        "action": "created",
        "object_type": "lead",
        "data": {
            "id": "lead_api_test_002"
        }
    }
}

response = requests.post(
    url,
    json=test_payload,
    timeout=15
)

print("Status code:", response.status_code)
print("Response:", response.text)