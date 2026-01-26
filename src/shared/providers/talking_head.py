
import os
import time
import requests
import json
import logging
from moviepy.editor import ImageClip

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class SyncLabsProvider:
    def __init__(self, output_dir="src/data/marketing_outputs"):
        self.output_dir = output_dir
        self.tmp_dir = "src/data/tmp_assets"
        self.vault_path = "data/api_vault.json"
        self.api_key = self._load_api_key()
        self.base_url = "https://api.sync.so/v2"
        
        for d in [self.output_dir, self.tmp_dir]:
            if not os.path.exists(d): os.makedirs(d)

    def _load_api_key(self):
        try:
            with open(self.vault_path, 'r') as f:
                vault = json.load(f)
                for entry in vault.get("synclabs", []):
                    if entry.get("status") == "active":
                        return entry.get("api_key")
        except Exception as e:
            logging.error(f"Vault error: {e}")
        return None

    def _convert_image_to_video(self, image_path):
        """Converts a static image to a 1-second MP4 video for SyncLabs."""
        try:
            logging.info(f"Converting image to video: {image_path}")
            video_path = os.path.join(self.tmp_dir, "input_video.mp4")
            
            # Create a 1-second clip from the image
            clip = ImageClip(image_path).set_duration(1)
            # Set a standard FPS for the video
            clip.write_videofile(video_path, fps=24, codec="libx264", audio=False, logger=None)
            
            logging.info(f"Video created: {video_path}")
            return video_path
        except Exception as e:
            logging.error(f"Image to Video conversion failed: {e}")
            return None

    def generate_video(self, source_image_path, driving_audio_path, filename="synced_avatar"):
        if not self.api_key:
            logging.error("No active SyncLabs API key!")
            return None

        logging.info("SYNCLABS: Starting Lip-Sync process (Direct Upload)...")
        try:
            # Step 1: Convert Image to Video (SyncLabs needs a video container)
            video_input_path = self._convert_image_to_video(source_image_path)
            if not video_input_path: return None

            # Step 2: Prepare Multipart Request
            logging.info("SYNCLABS: Sending direct upload request...")
            
            # Open files for streaming
            with open(video_input_path, 'rb') as video_file, open(driving_audio_path, 'rb') as audio_file:
                files = {
                    'video': ('video.mp4', video_file, 'video/mp4'),
                    'audio': ('audio.mp3', audio_file, 'audio/mpeg')
                }
                data = {
                    'model': 'lipsync-1.9.0-beta'
                }
                headers = {
                    'x-api-key': self.api_key
                }
                
                res = requests.post(f"{self.base_url}/generate", headers=headers, files=files, data=data)
            
            if res.status_code not in [200, 201]:
                logging.error(f"Direct upload failed ({res.status_code}): {res.text}")
                return None

            job_id = res.json().get("id")
            logging.info(f"SYNCLABS: Job {job_id} created successfully via direct upload. Polling...")
            return self._poll_job(job_id, filename)
            
        except Exception as e:
            logging.error(f"Fatal error: {e}")
            return None

    def _poll_job(self, job_id, filename):
        for _ in range(120): # Polling for up to 10 minutes
            res = requests.get(f"{self.base_url}/generate/{job_id}", headers={"x-api-key": self.api_key})
            if res.status_code == 200:
                data = res.json()
                status = data.get("status")
                if status == "COMPLETED":
                    logging.info(f"Job COMPLETED. Response keys: {list(data.keys())}")
                    # Look for URL in various possible fields
                    video_url = data.get("videoUrl") or data.get("url") or data.get("video_url")
                    
                    if not video_url and "output" in data:
                        video_url = data["output"]
                    
                    if video_url:
                        return self._download(video_url, filename)
                    else:
                        logging.error(f"FATAL: Could not find video URL. Full data: {json.dumps(data, indent=2)}")
                        return None
                if status in ["FAILED", "REJECTED"]:
                    logging.error(f"Job {status}: {data.get('error') or data}")
                    return None
                logging.info(f"Processing... ({status})")
            time.sleep(5)
        return None

    def _download(self, url, filename):
        path = os.path.join(self.output_dir, f"{filename}.mp4")
        res = requests.get(url, stream=True)
        with open(path, 'wb') as f:
            for c in res.iter_content(8192): f.write(c)
        logging.info(f"✅ Success! Video saved at: {path}")
        return path

if __name__ == "__main__":
    p = SyncLabsProvider()
    img = "C:/Users/USER/.gemini/antigravity/brain/e70dfc00-b85a-47f9-a48b-c5e26df4a1da/pro_trader_avatar_png_1769170904670.png"
    aud = os.path.abspath("src/data/voice_library/narrative/1 Narative.mp3")
    if os.path.exists(img) and os.path.exists(aud):
        p.generate_video(img, aud, "astrano_direct_upload_test")
    else:
        print("Test assets not found.")
