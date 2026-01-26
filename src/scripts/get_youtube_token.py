
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

from google_auth_oauthlib.flow import InstalledAppFlow

# Full access to YouTube-uploads
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_refresh_token():
    # We use your credentials from .env or you can use client_secrets.json
    from src.app.config import config
    
    client_id = config.YOUTUBE_CLIENT_ID
    client_secret = config.YOUTUBE_CLIENT_SECRET
    
    if not client_id or not client_secret:
        print("❌ ERROR: YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET must be set in .env")
        return

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    # Force "offline" access to get a REFRESH token, not just an access token
    flow = InstalledAppFlow.from_client_config(
        client_config, 
        scopes=SCOPES,
        redirect_uri='http://localhost:8080/'
    )

    # This will open a browser or provide a link
    # prompt='consent' ensures we get a refresh_token every time during test
    creds = flow.run_local_server(port=8080, prompt='consent', access_type='offline')

    print("\n" + "="*60)
    print("✅ SUCCESS! YOUR YOUTUBE REFRESH TOKEN IS:")
    print("="*60)
    print(creds.refresh_token)
    print("="*60)
    print("\nCopy this value into your .env file as YOUTUBE_REFRESH_TOKEN")

if __name__ == "__main__":
    get_refresh_token()
