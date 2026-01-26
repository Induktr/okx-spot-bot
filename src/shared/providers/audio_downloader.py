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
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{song_name} trading audio", download=True)
                # Get the actual filename created
                downloaded_file = ydl.prepare_filename(info)
                # Ensure it has the right extension if it changed during download
                if not os.path.exists(downloaded_file):
                    # Fallback search for any file starting with clean_name in that dir
                    files = [f for f in os.listdir(self.output_dir) if f.startswith(clean_name)]
                    if files: downloaded_file = os.path.join(self.output_dir, files[0])
            
            logging.info(f"✅ AUDIO DOWNLOADER: Successfully downloaded {os.path.basename(downloaded_file)}")
            return os.path.abspath(downloaded_file)
        except Exception as e:
            logging.error(f"❌ AUDIO DOWNLOADER Error: {e}")
            return None

audio_downloader = AudioDownloader()
