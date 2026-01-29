import logging
import os
import random
from PIL import Image, ImageDraw, ImageFont
from src.app.config import config

class VideoGenerator:
    """
    Advanced Media Generator with Radical Theme Engine.
    Creates unique, high-end PnL cards with varying structures, semantics, and aesthetics.
    """
    def __init__(self):
        self.output_dir = "src/data/marketing_outputs"
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_marketing_media(self, win_data, style_directive="DEFAULT", heading=None, status=None):
        """
        Main entry point. Generates a unique PNG card.
        """
        logging.info(f"🎨 VIDEO GEN: Triggering Radical Radical Theme Engine...")
        return self._generate_styled_card(win_data, style_directive, heading, status)

    def _generate_styled_card(self, win_data, style_directive, heading_override=None, status_override=None):
        try:
            width, height = 1080, 1920
            random.seed(os.urandom(8))
            
            card = Image.new('RGBA', (width, height), color=(0,0,0,0))
            draw = ImageDraw.Draw(card)
            
            # --- DYNAMIC SEMANTICS ---
            headings = ["PROFIT CAPTURED", "LIQUIDITY EXTRACTED", "MARKET DOMINANCE", "WIN DETECTED", "ALGO EXECUTION"]
            statuses = ["SYSTEM_OK", "SECURE", "NEURAL_SYNC", "HFT_LINK", "ASTR_v1.5"]
            
            heading = heading_override or random.choice(headings)
            status_text = status_override or random.choice(statuses)

            # --- STYLE MAPPING (AI Directive -> Layout Mode) ---
            mode_map = {
                "FLASH_CYBER": "CYBER",
                "MINIMAL_TEXT": "MINIMAL",
                "GLITCH_TRANSITION": "BRUTALIST",
                "CINEMATIC_ZOOM": "LUXURY",
                "INFOGRAPHIC": "DATA_DUMP"
            }
            target_mode = mode_map.get(style_directive, random.choice(["CYBER", "MINIMAL", "LUXURY", "BRUTALIST", "DATA_DUMP"]))

            # --- THEME PRESETS ---
            color_palettes = {
                "CYBER": {"bg": (10, 10, 20, 230), "accent": (0, 255, 180), "text": (255, 255, 255), "font": "impact.ttf"},
                "MINIMAL": {"bg": (255, 255, 255, 250), "accent": (0, 100, 255), "text": (20, 20, 30), "font": "arialbd.ttf"},
                "LUXURY": {"bg": (15, 15, 15, 240), "accent": (212, 175, 55), "text": (255, 255, 240), "font": "timesbd.ttf"},
                "BRUTALIST": {"bg": (255, 240, 0, 255), "accent": (0, 0, 0), "text": (0, 0, 0), "font": "impact.ttf"},
                "DATA_DUMP": {"bg": (0, 0, 0, 200), "accent": (255, 0, 80), "text": (255, 255, 255), "font": "courier.ttf"}
            }
            theme = color_palettes.get(target_mode)
            
            # Fonts
            def get_f(size, custom_font=None):
                f_name = custom_font or theme['font']
                try: return ImageFont.truetype(f"C:/Windows/Fonts/{f_name}", size)
                except: return ImageFont.load_default()

            symbol = str(win_data.get('symbol', 'BTC/USDT')).upper()
            roi = f"+{win_data.get('roi', 0)}%"
            pnl = f"${win_data.get('pnl', 0)} NET"
            
            # --- COMPONENT: RADICAL LAYOUTS ---
            if target_mode == "CYBER":
                # Layout: Scanning Interface
                draw.rectangle([100, 700, 980, 1200], fill=theme['bg'], outline=theme['accent'], width=5)
                scan_y = random.randint(700, 1200)
                draw.line([(100, scan_y), (980, scan_y)], fill=theme['accent'], width=2)
                # content
                draw.text((width//2, 800), heading, font=get_f(40), fill=theme['accent'], anchor="mm")
                draw.text((width//2, 1000), roi, font=get_f(220), fill=theme['text'], anchor="mm")
                draw.text((width//2, 1150), f"TARGET: {symbol}", font=get_f(60), fill=theme['accent'], anchor="mm")
                # Detailing
                draw.text((120, 720), status_text, font=get_f(30), fill=theme['accent'])
                draw.text((880, 1160), "SECURE", font=get_f(30), fill=theme['accent'])

            elif target_mode == "LUXURY":
                draw.rectangle([0, 0, width, height], fill=(0,0,0,140))
                plate = [200, 750, 880, 1150]
                draw.rounded_rectangle(plate, radius=30, fill=theme['bg'], outline=theme['accent'], width=10)
                draw.text((width//2, 800), heading, font=get_f(40), fill=theme['accent'], anchor="mm")
                draw.text((width//2, 900), symbol, font=get_f(90), fill=theme['text'], anchor="mm")
                draw.text((width//2, 1050), roi, font=get_f(180), fill=theme['accent'], anchor="mm")
                draw.text((width//2, 1200), status_text, font=get_f(35), fill=theme['text'], anchor="mm")

            elif target_mode == "BRUTALIST":
                draw.rectangle([0, 600, width, 1300], fill=theme['bg'])
                draw.text((50, 650), heading, font=get_f(60), fill=theme['accent'])
                draw.text((50, 800), symbol, font=get_f(200), fill=theme['accent'])
                draw.text((50, 1100), roi, font=get_f(300), fill=theme['accent'])
                draw.text((width-50, 1250), status_text, font=get_f(50), fill=theme['accent'], anchor="rm")

            elif target_mode == "MINIMAL":
                draw.rectangle([0, 400, 400, 1500], fill=theme['accent'])
                draw.text((450, 500), heading, font=get_f(60), fill=theme['accent'])
                draw.text((450, 800), symbol, font=get_f(120), fill=(255,255,255))
                draw.text((450, 1000), roi, font=get_f(280), fill=theme['accent'])
                draw.text((450, 1300), status_text, font=get_f(50), fill=(100,100,100))

            elif target_mode == "DATA_DUMP":
                # Layout: Matrix Style
                for i in range(12):
                    y = 400 + (i * 100)
                    txt = f"[{status_text}] " + "".join([random.choice("01") for _ in range(15)])
                    draw.text((50, y), txt, font=get_f(30), fill=(theme['accent'][0], theme['accent'][1], theme['accent'][2], 80))
                
                draw.rectangle([100, 850, 980, 1150], fill=(0,0,0,255), outline=theme['accent'], width=10)
                draw.text((width//2, 930), heading, font=get_f(50), fill=theme['accent'], anchor="mm")
                draw.text((width//2, 1050), roi, font=get_f(180), fill=theme['accent'], anchor="mm")

            # --- NOISE & GLITCH OVERLAY ---
            for _ in range(3000):
                x, y = random.randint(0, width-1), random.randint(0, height-1)
                draw.point((x, y), fill=(255, 255, 255, random.randint(0, 50)))
            
            # Rare Glitch Stripe
            if random.random() > 0.7:
                gy = random.randint(500, 1500)
                draw.rectangle([0, gy, width, gy+15], fill=(random.randint(0,255), random.randint(0,255), random.randint(0,255), 100))

            # Save PNG
            out_name = f"r_card_{win_data['id']}_{random.randint(100, 999)}.png"
            output_png = os.path.join(self.output_dir, out_name)
            card.save(output_png)
            
            logging.info(f"✅ VIDEO GEN: Radical {target_mode} card generated.")
            return output_png

        except Exception as e:
            logging.error(f"Style Gen Error: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return None

video_generator = VideoGenerator()
