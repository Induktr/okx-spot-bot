import logging
import os
from PIL import Image, ImageDraw, ImageFont
from src.app.config import config

class VideoGenerator:
    """
    Handles media generation. Connects to Runway/KlingAI API if available, 
    otherwise falls back to generating high-quality PnL summary cards via PIL.
    """
    def __init__(self):
        self.output_dir = "src/data/marketing_outputs"
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_marketing_media(self, win_data, script_text=None):
        """
        Main entry point for media generation.
        """
        # FUTURE: Implement KlingAI/Runway API here
        # if config.RUNWAY_API_KEY:
        #    return self._generate_ai_video(win_data, script_text)
        
        return self._generate_pnl_card(win_data)

    def _generate_pnl_card(self, win_data):
        """
        Generates a sleek, cyberpunk-style PnL card for high-ROI trades.
        """
        try:
            # Create a dark canvas
            width, height = 1080, 1920 # Vertical format for TikTok/Shorts
            card = Image.new('RGB', (width, height), color=(10, 10, 20)) # Dark Blue/Black
            draw = ImageDraw.Draw(card)

            # Draw some 'Cyber' elements
            draw.rectangle([50, 50, 1030, 1870], outline=(0, 255, 200), width=10) # Neon Border
            
            # Load font (falling back to default if necessary)
            try:
                # Assuming a font might be available or we use default
                font_path = "C:/Windows/Fonts/arialbd.ttf" # Common Windows path
                font_large = ImageFont.truetype(font_path, 120)
                font_medium = ImageFont.truetype(font_path, 80)
                font_small = ImageFont.truetype(font_path, 50)
            except:
                font_large = font_medium = font_small = ImageFont.load_default()

            # Text Overlay
            draw.text((width//2, 300), "A.S.T.R.A. WIN", font=font_large, fill=(0, 255, 200), anchor="mm")
            draw.text((width//2, 500), f"{win_data['symbol']}", font=font_medium, fill=(255, 255, 255), anchor="mm")
            
            roi_color = (0, 255, 0) if win_data['roi'] > 0 else (255, 0, 0)
            draw.text((width//2, 800), f"+{win_data['roi']}%", font=font_large, fill=roi_color, anchor="mm")
            draw.text((width//2, 950), "ROI EXTRACTED", font=font_small, fill=(200, 200, 200), anchor="mm")

            draw.text((width//2, 1200), f"PROFIT: {win_data['pnl']} USDT", font=font_medium, fill=(255, 255, 255), anchor="mm")
            
            draw.text((width//2, 1600), "GET THE BOT: INDUKTR.COM", font=font_medium, fill=(0, 255, 200), anchor="mm")

            output_path = f"{self.output_dir}/pnl_card_{win_data['id']}.png"
            card.save(output_path)
            logging.info(f"🎨 VIDEO GENERATOR: PnL Card saved to {output_path}")
            return output_path
        except Exception as e:
            logging.error(f"PnL Card Generation Error: {e}")
            return None

video_generator = VideoGenerator()
