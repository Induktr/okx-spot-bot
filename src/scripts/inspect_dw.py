
from gradio_client import Client
try:
    client = Client("D-W/LivePortrait")
    client.view_api()
except Exception as e:
    print(f"Error: {e}")
