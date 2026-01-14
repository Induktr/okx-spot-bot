import logging
import os
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
            
            # 7. ADD AUTO-COMMENT (The Sales Hook)
            comment_text = (
                f"🤖 A.S.T.R.A. AI Analysis: This trade on {title.split('on ')[-1].split('!')[0]} "
                f"was executed using real-time sentiment analysis. \n\n"
                f"💰 Get your own trading empire here: https://induktr.com \n"
                f"🚀 Join our Telegram for proofs: https://t.me/induktr_portfolio_bot"
            )
            await self._add_youtube_comment(video_id, comment_text)

            return f"SUCCESS: https://youtu.be/{video_id}"

        except Exception as e:
            logging.error(f"❌ YouTube Upload Error: {e}")
            return f"ERROR: {str(e)}"

    async def _add_youtube_comment(self, video_id, text):
        """Adds a top-level comment to the video."""
        try:
            logging.info(f"💬 YOUTUBE: Adding sales comment to video {video_id}...")
            youtube = self._get_youtube_service()
            
            body = {
                'snippet': {
                    'videoId': video_id,
                    'topLevelComment': {
                        'snippet': {
                            'textOriginal': text
                        }
                    }
                }
            }
            
            youtube.commentThreads().insert(part='snippet', body=body).execute()
            logging.info("✅ YOUTUBE: Sales comment posted successfully.")
        except Exception as e:
            logging.error(f"❌ YouTube Comment Error: {e}")

    async def _post_to_tiktok(self, video_path, text):
        logging.info("📱 TIKTOK: API implementation pending (v1.8).")
        return "PENDING_IMPLEMENTATION"

    async def _post_to_instagram(self, video_path, caption):
        logging.info("📸 INSTAGRAM: API implementation pending (v1.8).")
        return "PENDING_IMPLEMENTATION"

social_publisher = SocialPublisher()
