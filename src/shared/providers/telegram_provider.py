import requests
import logging
from src.app.config import config

class TelegramProvider:
    """
    Feature 5: Telegram Command Center & Signal Hub.
    Handles remote notifications and emergency alerts.
    """
    def __init__(self):
        self.token = config.TELEGRAM_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, text, parse_mode="Markdown"):
        if not self.token or not self.chat_id or not config.TG_SIGNALS_ACTIVE:
            return
            
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.json()
        except Exception as e:
            logging.error(f"Telegram Error: {e}")
            return None

    def send_emergency_alert(self, event_type, details):
        """Feature 6: Black Swan Alerting."""
        msg = (
            f"🚨 *BLACK SWAN ALERT: {event_type}*\n\n"
            f"⚠️ *DETAILS:* {details}\n"
            f"🛡️ *ACTION:* System entering defensive mode / executing emergency liquidation if configured."
        )
        return self.send_message(msg)

    def send_trade_signal(self, symbol, side, reasoning, score):
        """Feature 5: High-fidelity trade signals."""
        emoji = "🚀" if side == "BUY" else "🔻"
        msg = (
            f"{emoji} *TRADE SIGNAL: {side} {symbol}*\n\n"
            f"🧠 *AI SCORE:* {score}/10\n"
            f"📝 *REASONING:* {reasoning}\n\n"
            f"🔗 [Open Dashboard](http://localhost:5000)"
        )
        return self.send_message(msg)

# Singleton
telegram_bot = TelegramProvider()
