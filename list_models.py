from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("Listing available models...")
# In the new SDK, client.models.list() returns an iterator of model objects
for m in client.models.list():
    # In search/list results, we can just print the model names
    print(f"Name: {m.name}")

