
from gradio_client import Client
import logging

logging.basicConfig(level=logging.INFO)

try:
    # Use the KlingTeam space which KwaiVGI redirects to
    client = Client("KlingTeam/LivePortrait")
    print("\n--- API DETAILS ---")
    client.view_api()
    print("--- END API DETAILS ---")
except Exception as e:
    print(f"Error: {e}")
