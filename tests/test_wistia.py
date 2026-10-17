import os
import requests

token = os.environ["WISTIA_API_TOKEN"]

url = "https://api.wistia.com/v1/medias.json"

response = requests.get(
    url,
    headers={"Authorization": f"Bearer {token}"},
    timeout=30
)

response.raise_for_status()

medias = response.json()

print("Media count:", len(medias))

print("Status code:", response.status_code)
print("Media count:", len(medias))

for media in medias[:3]:
    print({
        "id": media.get("id"),
        "hashed_id": media.get("hashed_id"),
        "name": media.get("name"),
        "created": media.get("created")
    })

media_id = medias[0]["hashed_id"]

stats_url = f"https://api.wistia.com/v1/stats/medias/{media_id}.json"

stats_response = requests.get(
    stats_url,
    headers={"Authorization": f"Bearer {token}"},
    timeout=30
)

print("Stats status:", stats_response.status_code)
stats_response.raise_for_status()

stats = stats_response.json()

print("Stats fields:", list(stats.keys()))
print("Stats:", stats)


visitors_url = "https://api.wistia.com/modern/stats/visitors"

visitors_response = requests.get(
    visitors_url,
    headers={
        "Authorization": f"Bearer {token}",
        "X-Wistia-API-Version": "2026-09"
    },
    params={"page": 1, "per_page": 10},
    timeout=30
)

print("Visitor status:", visitors_response.status_code)
visitors_response.raise_for_status()

visitor_data = visitors_response.json()

print("Response type:", type(visitor_data).__name__)

if isinstance(visitor_data, list):
    print("Records returned:", len(visitor_data))
    if visitor_data:
        print("Visitor fields:", list(visitor_data[0].keys()))
else:
    print("Response fields:", list(visitor_data.keys()))


visitor = visitor_data[0]

print("Visitor identity type:", type(visitor.get("visitor_identity")).__name__)
print("User agent type:", type(visitor.get("user_agent_details")).__name__)

if isinstance(visitor.get("visitor_identity"), dict):
    print("Identity fields:", list(visitor["visitor_identity"].keys()))

if isinstance(visitor.get("user_agent_details"), dict):
    print("User agent fields:", list(visitor["user_agent_details"].keys()))