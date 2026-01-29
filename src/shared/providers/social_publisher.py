import logging
import os
import aiohttp
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import telebot
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
        import asyncio
        results = {}
        
        async def safe_post(platform, coro):
            try:
                # 2-minute timeout per platform to prevent total hang
                return await asyncio.wait_for(coro, timeout=120)
            except asyncio.TimeoutError:
                logging.error(f"⌛ {platform.upper()} Upload timed out (120s limit).")
                return "TIMEOUT"
            except Exception as e:
                logging.error(f"❌ {platform.upper()} Error during parallel publish: {e}")
                return f"ERROR: {e}"

        # Setup tasks for parallel execution
        tasks = {
            'telegram': safe_post('telegram', self._post_to_telegram(video_path, description)),
            'tiktok': safe_post('tiktok', self._post_to_tiktok(video_path, description))
        }
        
        if self.yt_refresh_token:
            tasks['youtube'] = safe_post('youtube', self._post_to_youtube(video_path, title, description))
            
        if config.INSTAGRAM_USERNAME:
            tasks['instagram'] = safe_post('instagram', self._post_to_instagram(video_path, description))

        # Run all publishing tasks in parallel
        platforms = list(tasks.keys())
        outputs = await asyncio.gather(*tasks.values())
        
        for i, platform in enumerate(platforms):
            results[platform] = outputs[i]

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
            error_str = str(e)
            if "uploadLimitExceeded" in error_str:
                logging.error("❌ YouTube Error: Daily Upload Limit Exceeded. You must wait 24 hours before posting more videos to this account.")
                return "ERROR: YouTube Daily Limit Hit. Please wait 24 hours."
            logging.error(f"❌ YouTube Error: {e}")
            return f"ERROR: {error_str}"

    async def _add_youtube_comment(self, video_id, text):
        try:
            youtube = self._get_youtube_service()
            body = {'snippet': {'videoId': video_id, 'topLevelComment': {'snippet': {'textOriginal': text}}}}
            youtube.commentThreads().insert(part='snippet', body=body).execute()
        except: pass

    # --- TIKTOK LOGIC (Direct Post API v2) ---
    async def _post_to_tiktok(self, video_path, text):
        """
        TikTok Posting Logic.
        Switching to Stealth Cookie-based method (Playwright) by default.
        """
        try:
            from src.shared.utils.tiktok_stealth import tiktok_stealth_upload
            
            cookie_path = os.path.join(os.getcwd(), "data", "tiktok_cookies.txt")
            if not os.path.exists(cookie_path):
                # Try to find the json state which is more important
                session_state_path = cookie_path.replace('.txt', '.json')
                if not os.path.exists(session_state_path):
                    logging.warning("🎬 TIKTOK: No cookies or session state found. Skipping stealth upload.")
                    return "SKIPPED_NO_COOKIES"
            
            # Use headless mode for servers (Linux)
            is_headless = getattr(config, 'HEADLESS_MODE', True) 
            logging.info(f"🎬 TIKTOK: Starting Stealth Playwright upload (Headless={is_headless})...")
            
            result = await tiktok_stealth_upload(video_path, text, cookie_path, headless=is_headless)
            
            if result == "SUCCESS":
                logging.info("✅ TIKTOK: Stealth Post Successful via Playwright!")
                return "SUCCESS: Stealth Upload Completed"
            else:
                logging.error(f"❌ TikTok Stealth Error: {result}")
                return f"ERROR: {result}"
                
        except Exception as e:
            logging.error(f"❌ TikTok Cookie Error: {e}")
            return f"ERROR: {str(e)}"

    async def _post_to_tiktok_cookies(self, video_path, description):
        """
        Uploads to TikTok using cookies and Playwright (Super Stealth).
        """
        try:
            from src.shared.utils.tiktok_stealth import tiktok_stealth_upload
            cookie_path = os.path.join(os.getcwd(), "data", "tiktok_cookies.txt")
            
            logging.info("🎬 TIKTOK: Starting Super-Stealth Playwright upload...")
            result = await tiktok_stealth_upload(video_path, description, cookie_path)
            
            if result == "SUCCESS":
                logging.info("✅ TIKTOK: Stealth Post Successful via Playwright!")
                return "SUCCESS: Stealth Upload Completed"
            else:
                return f"ERROR: {result}"
                
        except Exception as e:
            logging.error(f"❌ TikTok Cookie Error: {e}")
            return f"ERROR: {str(e)}"

    async def _post_to_instagram(self, video_path, caption):
        """
        Uploads video to Instagram Reels using instagrapi (Unofficial API).
        This mimics a real phone app upload.
        """
        try:
            from instagrapi import Client
            from src.app.config import config
            
            username = config.INSTAGRAM_USERNAME
            password = config.INSTAGRAM_PASSWORD
            
            if not username or not password or "your_" in username:
                logging.warning("⚠️ INSTAGRAM: Credentials missing in .env. Skipping.")
                return "SKIPPED_NO_CREDS"

            logging.info(f"📸 INSTAGRAM: Logging in as @{username}...")
            
            # Инициализация клиента
            cl = Client()
            settings_path = os.path.join(os.getcwd(), "data", "ig_settings.json")
            
            # Попытка загрузки старой сессии
            if os.path.exists(settings_path):
                try:
                    cl.load_settings(settings_path)
                    logging.info("📸 INSTAGRAM: Loaded session from file.")
                except Exception:
                    logging.warning("📸 INSTAGRAM: Failed to load old session.")

            # Попытка входа
            try:
                cl.login(username, password)
                cl.dump_settings(settings_path) # Сохраняем сессию для будущего
            except Exception as login_err:
                if "challenge_required" in str(login_err):
                    logging.error("❌ Instagram: Challenge REQUIRED. Please open the app and confirm 'This was me'.")
                    return "ERROR: Challenge Required. Confirm on your phone."
                raise login_err
            
            logging.info("📸 INSTAGRAM: Starting upload process...")
            
            # Загрузка видео с повторными попытками
            for attempt in range(3):
                try:
                    logging.info(f"📸 INSTAGRAM: Upload attempt {attempt + 1}...")
                    media = cl.video_upload(
                        path=video_path,
                        caption=caption
                    )
                    short_code = media.code
                    logging.info(f"✅ INSTAGRAM: Published! Link: https://www.instagram.com/reel/{short_code}/")
                    return f"SUCCESS: https://www.instagram.com/reel/{short_code}/"
                except Exception as upload_err:
                    if "media_needs_reupload" in str(upload_err) and attempt < 2:
                        logging.warning("⚠️ INSTAGRAM: Server requested re-upload. Retrying in 5s...")
                        import time
                        time.sleep(5)
                        continue
                    raise upload_err

        except Exception as e:
            logging.error(f"❌ Instagram Error: {e}")
            # Часто бывает Challenge Required (проверка на робота)
            if "challenge_required" in str(e):
                return "ERROR: 2FA/Challenge Required. Login manually first."
            return f"ERROR: {str(e)}"

    async def post_image_to_telegram(self, image_path, caption):
        """Sends a photo with a caption to the Telegram channel."""
        try:
            bot_token = config.TELEGRAM_TOKEN
            # Очищаем ID от возможных невидимых символов \r или пробелов
            chat_id = str(config.TELEGRAM_CHAT_ID).strip()
            
            if not bot_token or not chat_id:
                logging.warning("⚠️ TELEGRAM: Bot token or Chat ID missing.")
                return False

            logging.info(f"📤 TELEGRAM: Attempting to send photo to Chat ID: {chat_id}")
            bot = telebot.TeleBot(bot_token)
            with open(image_path, 'rb') as photo:
                bot.send_photo(chat_id, photo, caption=caption)
            
            logging.info("✅ TELEGRAM: Image report sent successfully.")
            return True
        except Exception as e:
            logging.error(f"❌ Telegram Image Error: {e}")
            return False

    async def _post_to_telegram(self, video_path, caption):
        """Internal helper for video posting to Telegram."""
        try:
            bot_token = config.TELEGRAM_TOKEN
            chat_id = config.TELEGRAM_CHAT_ID
            
            if not bot_token or not chat_id: return "SKIPPED_NO_CREDS"

            bot = telebot.TeleBot(bot_token)
            with open(video_path, 'rb') as video:
                bot.send_video(chat_id, video, caption=caption[:1000])
            return "SUCCESS"
        except Exception as e:
            logging.error(f"❌ Telegram Video Error: {e}")
            return f"ERROR: {e}"

social_publisher = SocialPublisher()
