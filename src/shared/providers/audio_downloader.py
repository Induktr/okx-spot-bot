import os
import logging
from yt_dlp import YoutubeDL

class AudioDownloader:
    """
    Downloads trending audio tracks from the web based on search queries.
    Used to ensure every video has high-quality background music.
    """
    def __init__(self):
        self.output_dir = "data/assets/sounds"
        os.makedirs(self.output_dir, exist_ok=True)

    def download_trending_track(self, song_name: str):
        """
        Searches for a song and downloads it as MP3.
        """
        logging.info(f"🎵 AUDIO DOWNLOADER: Searching for trend: {song_name}")
        
        # Clean filename
        clean_name = "".join([c for c in song_name if c.isalnum() or c in (' ', '_')]).rstrip()
        output_filename = f"{clean_name}.mp3"
        output_path = os.path.join(self.output_dir, output_filename)

        if os.path.exists(output_path):
            logging.info(f"🎵 AUDIO DOWNLOADER: Track already exists: {output_filename}")
            return output_path

        # Updated options to NOT require FFmpeg for conversion
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.output_dir, f"{clean_name}.%(ext)s"),
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch1:',
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.google.com/',
            'headers': {
                'Accept-Language': 'en-US,en;q=0.9',
            },
            'socket_timeout': 10, # 10 seconds timeout
            'retries': 0,        # Don't try again if blocked
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{song_name} trading audio", download=True)
                downloaded_file = ydl.prepare_filename(info)
                
                # Double check the file exists with any extension
                if not os.path.exists(downloaded_file):
                    base, _ = os.path.splitext(downloaded_file)
                    for ext in ['.mp3', '.webm', '.m4a', '.wav']:
                        if os.path.exists(base + ext):
                            downloaded_file = base + ext
                            break

            logging.info(f"✅ AUDIO DOWNLOADER: Successfully downloaded {os.path.basename(downloaded_file)}")
            return os.path.abspath(downloaded_file)
            
        except Exception as e:
            logging.error(f"❌ AUDIO DOWNLOADER Error: {e}")
            logging.info("🔊 AUDIO DOWNLOADER: Falling back to local library...")
            
            # FALLBACK: Pick a random existing sound file
            try:
                local_sounds = [f for f in os.listdir(self.output_dir) if f.endswith(('.mp3', '.webm', '.m4a'))]
                if local_sounds:
                    chosen = random.choice(local_sounds)
                    fallback_path = os.path.join(self.output_dir, chosen)
                    logging.info(f"🎸 AUDIO DOWNLOADER: Selected local fallback: {chosen}")
                    return os.path.abspath(fallback_path)
            except:
                pass
                
            return None

import random # Ensure random is available for fallback
audio_downloader = AudioDownloader()
