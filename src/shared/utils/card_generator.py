import os
import logging
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import io

class PNLCardGenerator:
    """
    Institutional-grade PNL Card Generator for A.S.T.R.A. v1.5.
    Creates high-fidelity shareable images of trading performance.
    """
    def __init__(self):
        self.width = 800
        self.height = 450
        self.bg_color = "#0a0a0c"
        self.accent_color = "#3b82f6" # Blue
        self.success_color = "#10b981" # Green
        self.error_color = "#ef4444" # Red
        self.text_color = "#ffffff"
        self.muted_text = "#9ca3af"

    def _get_font(self, size=24, bold=False):
        # Professional fallback font selection
        fonts = [
            "C:/Windows/Fonts/orbitron.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "arial.ttf"
        ]
        
        for f in fonts:
            try:
                return ImageFont.truetype(f, size)
            except:
                continue
        return ImageFont.load_default()

    def generate_trade_card(self, trade_data):
        """
        Generates a PNL card for a specific trade.
        trade_data: {symbol, side, leverage, pnl_pct, entry_price, current_price, hurst, fisher}
        """
        try:
            # 1. Create Base Image
            img = Image.new('RGB', (self.width, self.height), color=self.bg_color)
            draw = ImageDraw.Draw(img)

            # 2. Add Aesthetic Elements (Gradients/Lines)
            # Subtle accent line at top
            draw.rectangle([0, 0, self.width, 8], fill=self.accent_color)
            
            # 3. Branding
            font_title = self._get_font(28, bold=True)
            draw.text((40, 40), "A.S.T.R.A. v1.5", font=font_title, fill=self.text_color)
            
            font_subtitle = self._get_font(14)
            draw.text((40, 75), "QUANTUM TRADING SENTINEL", font=font_subtitle, fill=self.muted_text)

            # 4. Symbol & Context
            symbol = trade_data.get('symbol', 'BTC/USDT').split(':')[0]
            side = trade_data.get('side', 'LONG').upper()
            leverage = trade_data.get('leverage', 1)
            
            font_symbol = self._get_font(48, bold=True)
            draw.text((40, 120), symbol, font=font_symbol, fill=self.text_color)
            
            side_color = self.success_color if side in ["LONG", "BUY"] else self.error_color
            font_side = self._get_font(20, bold=True)
            draw.text((40, 185), f"{side} {leverage}x", font=font_side, fill=side_color)

            # 5. MAIN PNL (The 'Wow' Factor)
            pnl_pct = float(trade_data.get('pnl_pct', 0.0))
            pnl_color = self.success_color if pnl_pct >= 0 else self.error_color
            pnl_text = f"{'+' if pnl_pct >= 0 else ''}{pnl_pct:.2f}%"
            
            font_pnl = self._get_font(100, bold=True)
            # Measure text to center or align right
            draw.text((40, 220), pnl_text, font=font_pnl, fill=pnl_color)

            # 6. Technical Stats (The 'Pro' details)
            font_label = self._get_font(14)
            font_value = self._get_font(18, bold=True)
            
            stats_y = 360
            # Column 1: Entry
            draw.text((40, stats_y), "ENTRY PRICE", font=font_label, fill=self.muted_text)
            draw.text((40, stats_y + 25), f"{trade_data.get('entry_price', 0.0):.2f}", font=font_value, fill=self.text_color)
            
            # Column 2: Current
            draw.text((200, stats_y), "MARK PRICE", font=font_label, fill=self.muted_text)
            draw.text((200, stats_y + 25), f"{trade_data.get('current_price', 0.0):.2f}", font=font_value, fill=self.text_color)
            
            # Column 3: Hurst (Quantum Trace)
            draw.text((450, stats_y), "HURST EXPONENT", font=font_label, fill=self.muted_text)
            draw.text((450, stats_y + 25), f"{trade_data.get('hurst', 0.5):.3f}", font=font_value, fill=self.accent_color)
            
            # Column 4: Fisher
            draw.text((630, stats_y), "FISHER TRANS.", font=font_label, fill=self.muted_text)
            draw.text((630, stats_y + 25), f"{trade_data.get('fisher', 0.0):+.3f}", font=font_value, fill=self.accent_color)

            # 7. Add Watermark / Timestamp
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            draw.text((self.width - 200, 40), ts, font=self._get_font(12), fill=self.muted_text)

            # Save to Bytes
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return buf
        except Exception as e:
            logging.error(f"❌ CARD GEN ERROR: {e}")
            return None

# Singleton
pnl_generator = PNLCardGenerator()
