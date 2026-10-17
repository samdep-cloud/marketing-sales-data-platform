import json
import requests
from pathlib import Path

url = "https://jn5izdmsii.execute-api.us-east-1.amazonaws.com/calendly"

sample_path = Path("sample_data/calendly/calendly_event.json")

with open(sample_path, "r") as file:
    payload = json.load(file)

response = requests.post(url, json=payload, timeout=30)

print("Status:", response.status_code)
print("Response:", response.text)