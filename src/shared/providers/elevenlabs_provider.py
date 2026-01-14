import requests
import json
import logging
import os
from src.app.config import config

class ElevenLabsProvider:
    """
    Service to convert text scripts into professional AI-generated audio (MP3).
    """
    def __init__(self):
        self.api_key = config.ELEVENLABS_API_KEY
        self.voice_id = config.ELEVENLABS_VOICE_ID
        self.base_url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"

    def generate_speech(self, text, output_filename):
        """
        Sends text to ElevenLabs and saves the resulting MP3.
        """
        if not self.api_key:
            logging.warning("ElevenLabs API Key missing. Skipping audio generation.")
            return None

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }

        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        try:
            logging.info(f"🎙️ ELEVENLABS: Generating audio for script...")
            response = requests.post(self.base_url, json=data, headers=headers)
            
            if response.status_code == 200:
                output_path = f"src/data/marketing_outputs/{output_filename}.mp3"
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(response.content)
                logging.info(f"✅ ELEVENLABS: Audio saved to {output_path}")
                return output_path
            else:
                logging.error(f"ElevenLabs API Error [{response.status_code}]: {response.text}")
                return None
        except Exception as e:
            logging.error(f"ElevenLabs Provider Error: {e}")
            return None

elevenlabs_provider = ElevenLabsProvider()
