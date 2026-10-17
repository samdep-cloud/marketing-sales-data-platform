import requests

lead_id = "lead_XDlrPX7rkhtYXhMIGjpr30w2VX7NMe7yA8DC3ZBFjXR"

url = f"https://dea-lead-owner.s3.us-east-1.amazonaws.com/{lead_id}.json"

response = requests.get(url, timeout=30)

print("Status:", response.status_code)

if response.ok:
    owner_data = response.json()
    print(owner_data)
else:
    print(response.text)