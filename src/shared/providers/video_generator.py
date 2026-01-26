import logging
import os
import random
from PIL import Image, ImageDraw, ImageFont
from src.app.config import config

class VideoGenerator:
    """
    Advanced Media Generator with Adaptive Theme Engine.
    Creates unique, high-end PnL cards for every trade with randomized styles.
    """
    def __init__(self):
        self.output_dir = "src/data/marketing_outputs"
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_marketing_media(self, win_data, style_directive="DEFAULT"):
        """
        Main entry point. Generates a unique PNG card.
        """
        logging.info(f"🎨 VIDEO GEN: Triggering Adaptive Theme Engine...")
        return self._generate_styled_card(win_data, style_directive)

    def _generate_styled_card(self, win_data, style_directive):
        try:
            width, height = 1080, 1920
            
            # --- ADAPTIVE THEME ENGINE (Ultra-Readable V2) ---
            themes = [
                { # Premium White (Best for complex backgrounds)
                    "bg": (255, 255, 255, 255), "accent": (0, 100, 255), "text": (20, 20, 20),
                    "font": "arialbd.ttf", "radius": 50, "name": "PREMIUM_WHITE"
                },
                { # Stealth Dark (Solid)
                    "bg": (15, 15, 20, 255), "accent": (0, 255, 180), "text": (255, 255, 255),
                    "font": "impact.ttf", "radius": 40, "name": "STEALTH_DARK"
                },
                { # Cyber Neon
                    "bg": (10, 10, 25, 255), "accent": (0, 255, 255), "text": (255, 255, 255),
                    "font": "impact.ttf", "radius": 60, "name": "CYBER_NEON"
                },
                { # Gold Luxury
                    "bg": (15, 15, 15, 255), "accent": (212, 175, 55), "text": (255, 255, 255),
                    "font": "arialbd.ttf", "radius": 40, "name": "GOLD_LUXURY"
                }
            ]
            
            # Select random theme based on trade_id to keep it consistent for one trade but unique for others
            random.seed(win_data.get('id', 0))
            theme = random.choice(themes)
            
            card = Image.new('RGBA', (width, height), color=(0,0,0,0))
            draw = ImageDraw.Draw(card)

            # --- RENDER GLASS PLATE (Rounded & Textured) ---
            plate_box = [120, 650, 960, 1250] # Adjusted to be more central for better visibility
            r = theme['radius']
            
            # 1. Subtle Outer Shadow
            shadow_box = [plate_box[0]+12, plate_box[1]+12, plate_box[2]+12, plate_box[3]+12]
            draw.rounded_rectangle(shadow_box, radius=r, fill=(0, 0, 0, 100))

            # 2. Main Solid Background (100% Opaque)
            draw.rounded_rectangle(plate_box, radius=r, fill=theme['bg'], outline=theme['accent'], width=10)
            
            # 3. Inner Border (Double line effect for premium look)
            inner_box = [plate_box[0]+15, plate_box[1]+15, plate_box[2]-15, plate_box[3]-15]
            draw.rounded_rectangle(inner_box, radius=r-15, outline=(255, 255, 255, 40), width=2)

            # --- CONTENT LAYOUT ---
            # Font Loading with Fallbacks
            def get_font(size):
                try: return ImageFont.truetype(f"C:/Windows/Fonts/{theme['font']}", size)
                except: return ImageFont.load_default()

            title_f = get_font(160)
            symbol_f = get_font(110)
            cta_f = get_font(70)

            # Draw ROI (The Big Hero Number)
            roi = win_data.get('roi', 0)
            draw.text((width//2, 850), f"+{roi}%", font=title_f, fill=theme['accent'], anchor="mm")
            
            # Draw Symbol
            draw.text((width//2, 650), win_data.get('symbol', 'BTC'), font=symbol_f, fill=theme['text'], anchor="mm")

            # Draw PnL
            draw.text((width//2, 1100), f"${win_data.get('pnl', 0)} NET PROFIT", font=cta_f, fill=theme['text'], anchor="mm")

            # Draw Brand Tag
            draw.text((width//2, 1350), "A.S.T.R.A. AI SYSTEM", font=get_font(50), fill=theme['accent'], anchor="mm")

            # Save PNG
            output_png = os.path.join(self.output_dir, f"unique_card_{win_data['id']}.png")
            card.save(output_png)
            logging.info(f"✅ VIDEO GEN: Created unique {theme['name']} style card.")
            return output_png

        except Exception as e:
            logging.error(f"Style Gen Error: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return None

video_generator = VideoGenerator()
