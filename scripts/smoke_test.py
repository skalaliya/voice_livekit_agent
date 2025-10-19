# smoke_test.py
import os, json, requests
from dotenv import load_dotenv

load_dotenv(".env")

BASE = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:11434/v1")
API  = os.getenv("OPENAI_API_KEY", "ollama")
MODEL = os.getenv("LLM_MODEL", "llama3.2:3b")

payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "You are a concise, friendly assistant."},
        {"role": "user", "content": "Say hello in one short sentence."}
    ]
}

r = requests.post(
    f"{BASE}/chat/completions",
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {API}"},
    data=json.dumps(payload)
)

print("HTTP", r.status_code)
print(r.json()["choices"][0]["message"]["content"])
