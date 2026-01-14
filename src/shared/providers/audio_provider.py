import edge_tts
import asyncio
import logging
import os

class AudioProvider:
    """
    FREE Audio Provider using Microsoft Edge TTS (via edge-tts).
    Provides high-quality AI voices without API costs.
    """
    def __init__(self, voice="en-US-ChristopherNeural"):
        self.voice = voice
        self.output_dir = "src/data/marketing_outputs"
        os.makedirs(self.output_dir, exist_ok=True)

    async def generate_speech(self, text, output_filename):
        """
        Converts text to speech and saves as MP3 using edge-tts.
        """
        output_path = os.path.join(self.output_dir, f"{output_filename}.mp3")
        
        # Clean text from visual instructions like [Scene: ...]
        import re
        clean_text = re.sub(r'\[.*?\]', '', text).strip()

        try:
            logging.info(f"🎙️ AUDIO PROVIDER: Generating free speech for script...")
            communicate = edge_tts.Communicate(clean_text, self.voice)
            await communicate.save(output_path)
            logging.info(f"✅ AUDIO PROVIDER: Free audio saved to {output_path}")
            return output_path
        except Exception as e:
            logging.error(f"AudioProvider Error: {e}")
            return None

audio_provider = AudioProvider()
