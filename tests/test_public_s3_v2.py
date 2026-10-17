import requests

url = "https://dea-lead-owner.s3.us-east-1.amazonaws.com/lead_aw7xeDwarc9aYKaBsrfEktCUZxVbPQ3Ws8VQwm2lxFO.json"

response = requests.get(url, timeout=30)

print("Status:", response.status_code)