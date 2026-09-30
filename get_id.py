import requests
import os 
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")

# 1. First, check if the token was successfully loaded from the .env file
if not ACCESS_TOKEN:
    print("⚠️ Error: Token not loaded! Make sure the .env file is in the same directory and the variable is named LINKEDIN_ACCESS_TOKEN.")
    exit()

url = "https://api.linkedin.com/v2/userinfo"

# 2. Updated Headers (Added User-Agent and Protocol version to avoid bot-blocking)
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "X-Restli-Protocol-Version": "2.0.0"
}

try:
    print("🔗 Connecting to LinkedIn API...")
    
    # Added timeout to prevent the request from hanging infinitely
    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code == 200:
        data = response.json()
        my_urn = data.get('sub')
        print("✅ Success!")
        print(f"Your URN is: urn:li:person:{my_urn}")
    else:
        print("❌ API Error:", response.status_code)
        print("Message:", response.text)

except requests.exceptions.ConnectionError as e:
    print("\n🚨 Connection Aborted by Server!")
    print("💡 Fixes to try:")
    print("1. Try changing your internet network (e.g., switch to a Mobile Data hot-spot).")
    print("2. Connect to a VPN (like Cloudflare WARP or ProtonVPN) and run the script again.")
except Exception as e:
    print(f"❌ Unknown Error: {e}")