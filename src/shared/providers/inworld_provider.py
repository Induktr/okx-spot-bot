
import requests
import base64
import os
import logging
from src.app.config import config

class InworldProvider:
    """
    Official API implementation for Inworld AI TTS.
    Faster, more reliable, and bypasses UI automation issues.
    """
    def __init__(self):
        self.url = "https://api.inworld.ai/tts/v1/voice"
        self.output_dir = os.path.abspath("src/data/media_assets")
        os.makedirs(self.output_dir, exist_ok=True)

    async def generate_speech(self, text, filename_prefix="inworld_audio"):
        """
        Generates MP3 using Inworld API.
        Reference: https://platform.inworld.ai (TTS Playground API Example)
        """
        api_key = config.INWORLD_API_KEY
        voice_id = config.INWORLD_VOICE_ID
        
        if not api_key:
            logging.warning("🎙️ INWORLD: API Key is missing. Check your .env or settings.json")
            return None

        logging.info(f"🎙️ INWORLD API: Generating speech...")

        headers = {
            "Authorization": f"Basic {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "text": text,
            "voice_id": voice_id,
            "audio_config": {
                "audio_encoding": "MP3",
                "speaking_rate": 1
            },
            "temperature": 1.1,
            "model_id": "inworld-tts-1.5-max"
        }

        try:
            # Note: Using requests.post synchronously here since it's a simple call, 
            # but we could wrap in run_in_executor for full async if needed.
            response = requests.post(self.url, json=payload, headers=headers)
            
            if response.status_code != 200:
                logging.error(f"❌ INWORLD API Error: {response.status_code} - {response.text}")
                return None

            result = response.json()
            if 'audioContent' not in result:
                logging.error(f"❌ INWORLD API response missing 'audioContent': {result}")
                return None

            audio_content = base64.b64decode(result['audioContent'])
            
            output_path = os.path.join(self.output_dir, f"{filename_prefix}.mp3")
            with open(output_path, "wb") as f:
                f.write(audio_content)
            
            logging.info(f"✅ INWORLD API: Success! Saved to {output_path}")
            return output_path

        except Exception as e:
            logging.error(f"❌ INWORLD API FATAL: {e}")
            return None

inworld_provider = InworldProvider()
