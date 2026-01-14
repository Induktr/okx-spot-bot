import os
import google_auth_oauthlib.flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Scopes required for YouTube Upload
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def main():
    # 1. Point to the client_secrets.json you downloaded
    client_secrets_file = "client_secrets.json"
    
    if not os.path.exists(client_secrets_file):
        print(f"❌ Error: {client_secrets_file} not found in project root.")
        return

    # 2. Setup the flow
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, SCOPES
    )

    # 3. Run the local server for auth
    # This will open your browser
    credentials = flow.run_local_server(port=0)

    # 4. Extract tokens
    print("\n" + "="*50)
    print("✅ AUTHENTICATION SUCCESSFUL!")
    print("="*50)
    print(f"CLIENT_ID: {credentials.client_id}")
    print(f"CLIENT_SECRET: {credentials.client_secret}")
    print(f"REFRESH_TOKEN: {credentials.refresh_token}")
    print("="*50)
    print("\n👉 COPY these values to your .env file.")

if __name__ == "__main__":
    main()
