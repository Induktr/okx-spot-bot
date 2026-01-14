import requests
import logging
import os
import random
from src.app.config import config

class PexelsProvider:
    """
    Downloads free high-quality video backgrounds for trading reels.
    """
    def __init__(self):
        self.api_key = config.PEXELS_API_KEY
        self.base_url = "https://api.pexels.com/videos/search"
        self.output_dir = "src/data/media_assets"
        os.makedirs(self.output_dir, exist_ok=True)

    def get_random_background(self, query="trading"):
        """
        Searches for videos on Pexels and downloads a random high-quality vertical video.
        """
        if not self.api_key:
            logging.warning("Pexels API Key missing. Skipping video download.")
            return None

        headers = {"Authorization": self.api_key}
        params = {
            "query": query,
            "per_page": 15,
            "orientation": "portrait"
        }

        try:
            logging.info(f"📹 PEXELS: Searching for '{query}' background videos...")
            response = requests.get(self.base_url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                videos = data.get("videos", [])
                if not videos:
                    logging.warning(f"No videos found for query: {query}")
                    return None
                
                # Pick a random video
                selected_video = random.choice(videos)
                # Find the HD file in video_files
                video_files = selected_video.get("video_files", [])
                # Prefer HD/Full HD
                video_url = None
                for vf in video_files:
                    if vf.get("quality") == "hd":
                        video_url = vf.get("link")
                        break
                
                if not video_url and video_files:
                    video_url = video_files[0].get("link")

                if video_url:
                    filename = f"bg_{selected_video['id']}.mp4"
                    local_path = os.path.join(self.output_dir, filename)
                    
                    if os.path.exists(local_path):
                        return local_path

                    logging.info(f"📥 PEXELS: Downloading video background...")
                    v_res = requests.get(video_url, stream=True)
                    with open(local_path, "wb") as f:
                        for chunk in v_res.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)
                    
                    logging.info(f"✅ PEXELS: Background saved to {local_path}")
                    return local_path
            else:
                logging.error(f"Pexels API Error: {response.text}")
                return None
        except Exception as e:
            logging.error(f"Pexels Provider Error: {e}")
            return None

pexels_provider = PexelsProvider()
