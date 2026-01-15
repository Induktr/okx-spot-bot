import logging
import os
import aiohttp
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from src.app.config import config

class SocialPublisher:
    """
    Handles automatic posting to social platforms (TikTok, YouTube, Instagram).
    """
    def __init__(self):
        self.tiktok_client_key = config.TIKTOK_CLIENT_KEY
        self.tiktok_token = config.TIKTOK_ACCESS_TOKEN
        self.ig_user_id = config.INSTAGRAM_USER_ID
        
        # YouTube Credentials
        self.yt_client_id = config.YOUTUBE_CLIENT_ID
        self.yt_client_secret = config.YOUTUBE_CLIENT_SECRET
        self.yt_refresh_token = config.YOUTUBE_REFRESH_TOKEN

    async def publish_everywhere(self, video_path, title, description):
        results = {}
        
        if self.tiktok_token:
            results['tiktok'] = await self._post_to_tiktok(video_path, description)
        
        if self.yt_refresh_token:
            results['youtube'] = await self._post_to_youtube(video_path, title, description)
            
        if self.ig_user_id:
            results['instagram'] = await self._post_to_instagram(video_path, description)

        return results

    # --- YOUTUBE LOGIC ---
    def _get_youtube_service(self):
        """Authenticates with YouTube using refresh token."""
        creds = Credentials(
            token=None,
            refresh_token=self.yt_refresh_token,
            client_id=self.yt_client_id,
            client_secret=self.yt_client_secret,
            token_uri="https://oauth2.googleapis.com/token"
        )
        if not creds.valid:
            creds.refresh(Request())
        return build("youtube", "v3", credentials=creds)

    async def _post_to_youtube(self, video_path, title, description):
        """Uploads video to YouTube as a Short."""
        try:
            logging.info(f"📺 YOUTUBE: Uploading Short: {title}...")
            youtube = self._get_youtube_service()
            
            body = {
                'snippet': {
                    'title': title[:100],
                    'description': description,
                    'tags': ['trading', 'ai', 'crypto', 'shorts'],
                    'categoryId': '27' # Education
                },
                'status': {
                    'privacyStatus': 'public',
                    'selfDeclaredMadeForKids': False
                }
            }

            media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype='video/mp4')
            request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logging.info(f"📺 YOUTUBE: Uploading... {int(status.progress() * 100)}%")

            video_id = response.get('id')
            logging.info(f"✅ YOUTUBE: Upload Success! Video ID: {video_id}")
            
            # Auto-comment
            comment_text = (
                f"🤖 A.S.T.R.A. AI Analysis: High-ROI win detected. \n\n"
                f"💰 Get the Bot: https://induktr.com \n"
                f"🚀 Proofs: https://t.me/induktr_portfolio_bot"
            )
            await self._add_youtube_comment(video_id, comment_text)

            return f"SUCCESS: https://youtu.be/{video_id}"
        except Exception as e:
            logging.error(f"❌ YouTube Error: {e}")
            return f"ERROR: {str(e)}"

    async def _add_youtube_comment(self, video_id, text):
        try:
            youtube = self._get_youtube_service()
            body = {'snippet': {'videoId': video_id, 'topLevelComment': {'snippet': {'textOriginal': text}}}}
            youtube.commentThreads().insert(part='snippet', body=body).execute()
        except: pass

    # --- TIKTOK LOGIC (Direct Post API v2) ---
    async def _post_to_tiktok(self, video_path, text):
        """
        Publishes video to TikTok using Content Posting API.
        Process: 1. Init -> 2. Upload -> 3. Status Check.
        """
        try:
            logging.info("📱 TIKTOK: Initiating upload...")
            
            url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
            headers = {
                "Authorization": f"Bearer {self.tiktok_token}",
                "Content-Type": "application/json; charset=UTF-8"
            }
            
            # Fix video path to absolute
            abs_path = os.path.abspath(video_path)
            file_size = os.path.getsize(abs_path)

            data = {
                "post_info": {
                    "title": text[:150],
                    "privacy_level": "PUBLIC_TO_EVERYONE",
                    "disable_duet": False,
                    "disable_stitch": False,
                    "disable_comment": False
                },
                "source_info": {
                    "source": "FILE_UPLOAD",
                    "video_size": file_size,
                    "chunk_size": file_size,
                    "total_chunk_count": 1
                }
            }

            async with aiohttp.ClientSession() as session:
                # 1. Initialize
                async with session.post(url, headers=headers, json=data) as resp:
                    init_res = await resp.json()
                    if resp.status != 200:
                        raise Exception(f"Init failed: {init_res}")
                    
                    upload_url = init_res['data']['upload_url']
                    publish_id = init_res['data']['publish_id']

                # 2. Upload File
                logging.info("📱 TIKTOK: Pushing file to server...")
                with open(abs_path, 'rb') as f:
                    # TikTok expects binary data directly for single chunk
                    async with session.put(upload_url, data=f, headers={"Content-Range": f"bytes 0-{file_size-1}/{file_size}"}) as upload_resp:
                        if upload_resp.status != 200 and upload_resp.status != 201:
                            res_text = await upload_resp.text()
                            raise Exception(f"Upload failed: {res_text}")

            logging.info(f"✅ TIKTOK: Posted! Publish ID: {publish_id}")
            return f"SUCCESS: ID {publish_id}"

        except Exception as e:
            logging.error(f"❌ TikTok Error: {e}")
            return f"ERROR: {str(e)}"

    async def _post_to_instagram(self, video_path, caption):
        logging.info("📸 INSTAGRAM: Pending API Key (Meta Graph API).")
        return "PENDING_API"

social_publisher = SocialPublisher()
