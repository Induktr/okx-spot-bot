
from gradio_client import Client
try:
    client = Client("OpenTalker/SadTalker")
    client.view_api()
except Exception as e:
    print(f"Error: {e}")
