import requests
import os
import random
import logging
import urllib.parse

class AIImageProvider:
    """
    Generates unique, high-quality background images for videos.
    Uses Pollinations.ai (FREE, no API key required) for radical variety.
    """
    def __init__(self):
        self.output_dir = "src/shared/data/media_assets/generated_bgs"
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.styles = [
            "cinematic 4k vertical, cyberpunk aesthetic, high tech server room",
            "hyper-realistic luxury office overlooking futuristic city at night, vertical",
            "abstract digital data flowing in dark space, neon accents, vertical 8k",
            "minimalist professional trading desk with multiple holograms, clean aesthetic",
            "dark moody 3D render of bitcoin and digital assets, golden lighting"
        ]

    def generate_background(self, theme_query=None):
        """
        Generates a fresh background image based on a theme.
        """
        try:
            # Construct a rich prompt
            base_prompt = theme_query if theme_query else random.choice(self.styles)
            full_prompt = f"{base_prompt}, high resolution, vertical 9:16 aspect ratio, professional cinematography, no text"
            
            encoded_prompt = urllib.parse.quote(full_prompt)
            seed = random.randint(0, 999999)
            # Pollinations.ai endpoint
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed}&width=720&height=1280&nologo=true"
            
            logging.info(f"🎨 AI IMAGE: Generating fresh background for prompt: {base_prompt[:50]}...")
            
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                file_name = f"bg_{seed}.png"
                file_path = os.path.join(self.output_dir, file_name)
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                logging.info(f"✅ AI IMAGE: Successfully generated -> {file_path}")
                return file_path
            else:
                logging.warning(f"⚠️ AI IMAGE: Generation failed (Status {response.status_code}).")
                return None
        except Exception as e:
            logging.error(f"❌ AI IMAGE ERROR: {e}")
            return None

ai_image_provider = AIImageProvider()
