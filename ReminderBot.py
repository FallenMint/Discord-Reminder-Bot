import requests, os

url = os.getenv("WEBHOOK_URL")
print("Webhook URL:", url)

if not url:
    raise Exception("WEBHOOK_URL is missing!")

r = requests.post(url, json={"content": "✅ GitHub Actions is working"})
print("Status:", r.status_code)
print("Response:", r.text)
