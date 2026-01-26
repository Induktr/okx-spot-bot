
from gradio_client import Client
import json

client = Client("KlingTeam/LivePortrait")
info = client.view_api(return_format="dict")

print("--- API NAMES ---")
for fn in info["named_endpoints"]:
    print(f"Endpoint: {fn}")
    # print(info["named_endpoints"][fn])

print("\n--- UNNAMED ENDPOINTS ---")
for i, fn in enumerate(info["unnamed_endpoints"]):
    print(f"Unnamed {i}")
