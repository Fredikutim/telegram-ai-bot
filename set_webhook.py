import os
import requests

BOT_TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

if not BOT_TOKEN:
    print("Error: BOT_TOKEN not set")
    exit(1)
if not WEBHOOK_URL:
    print("Error: WEBHOOK_URL not set (e.g. https://your-app.vercel.app/api/)")
    exit(1)

url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={WEBHOOK_URL}"
res = requests.get(url)
print(res.json())
