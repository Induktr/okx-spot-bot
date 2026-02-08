import requests
import logging
import io
from src.app.config import config

class DiscordProvider:
    """
    Discord Marketing Hub (Webhook Based).
    Used for sending visual trade reports to Discord channels.
    """
    def __init__(self):
        self.webhook_url = config.DISCORD_WEBHOOK_URL

    def send_pnl_report(self, photo_bytes, caption):
        """Sends a PNL card image and caption to Discord via Webhook."""
        if not self.webhook_url:
            logging.warning("Discord Webhook URL not set. Skipping.")
            return False

        try:
            # Prepare the file
            files = {
                'file': ('pnl_card.png', photo_bytes, 'image/png')
            }
            # Prepare the message
            payload = {
                'content': caption
            }
            
            response = requests.post(self.webhook_url, data=payload, files=files, timeout=30)
            
            if response.status_code in [200, 204]:
                logging.info("🚀 Discord PNL Report Sent successfully.")
                return True
            else:
                logging.error(f"Discord Webhook Error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"Failed to send Discord Webhook: {e}")
            return False

# Singleton
discord_provider = DiscordProvider()
