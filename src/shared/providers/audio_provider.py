import logging
import os
import asyncio
import edge_tts
from src.app.config import config

class AudioProvider:
    """
    Unified Audio Provider.
    Default: Uses Edge-TTS (Free, High Quality).
    Fallback/Premium: Can integrate ElevenLabs if API key is present.
    """
    def __init__(self):
        self.output_dir = "src/data/media_assets"
        os.makedirs(self.output_dir, exist_ok=True)
        # Voice mapping for different "Vibes"
        self.voices = {
            "DEFAULT": "en-US-ChristopherNeural",       # Deep, calm male
            "NEWS": "en-US-AriaNeural",                 # Professional female
            "HYPE": "en-US-EricNeural",                 # Energetic male
            "CYBER": "en-US-GuyNeural"                  # Neutral male
        }

    async def generate_speech(self, text, filename_prefix="audio"):
        """
        Generates MP3 from text.
        Priority: Inworld AI (Free/High Quality) -> ElevenLabs (Premium) -> Edge-TTS (Free/Fallback)
        """
        try:
            # 1. TRY INWORLD AI (NEW - BEST FREE ALTERNATIVE)
            try:
                from src.shared.providers.inworld_provider import inworld_provider
                logging.info("🎙️ AUDIO: Attempting Inworld AI generation...")
                path = await inworld_provider.generate_speech(text, filename_prefix)
                if path and os.path.exists(path):
                    return path
            except Exception as inworld_err:
                logging.warning(f"⚠️ AUDIO: Inworld failed, trying ElevenLabs: {inworld_err}")

            # 2. TRY ELEVENLABS STEALTH
            try:
                from src.shared.providers.elevenlabs_stealth import elevenlabs_stealth
                logging.info("🎙️ AUDIO: Attempting ElevenLabs Stealth...")
                path = await elevenlabs_stealth.generate_speech_stealth(text, filename_prefix, voice_name="Popular Trader")
                if path and os.path.exists(path):
                    return path
            except Exception as stealth_err:
                logging.warning(f"⚠️ AUDIO: ElevenLabs Stealth failed, falling back to Edge-TTS: {stealth_err}")

            # 2. FALLBACK TO EDGE-TTS (Free & Fast)
            output_file = os.path.join(self.output_dir, f"{filename_prefix}.mp3")
            voice = self.voices["DEFAULT"]
            
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_file)
            
            logging.info(f"🎙️ AUDIO: Generated speech via Edge-TTS -> {output_file}")
            return output_file

        except Exception as e:
            logging.error(f"Audio Generation Error: {e}")
            return None

audio_provider = AudioProvider()
