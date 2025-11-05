import os
import httpx
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GROQ_API_KEY")

if not key:
    print("❌ No GROQ_API_KEY found in .env")
    exit()

url = "https://api.groq.com/openai/v1/models"
headers = {"Authorization": f"Bearer {key}"}

try:
    r = httpx.get(url, headers=headers, timeout=60)
    r.raise_for_status()
    print("\n✅ Available Groq model IDs:\n")
    for m in r.json().get("data", []):
        print(" -", m["id"])
    print()
except Exception as e:
    print("❌ Error listing models:", e)
