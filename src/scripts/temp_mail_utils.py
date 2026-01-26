
from mailtm import Email
import time
import re
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class HedraTempMail:
    def __init__(self):
        self.mail = Email()
        self.latest_code = None
        self.is_listening = False

    def create_account(self):
        """Creates a new temporary email account."""
        logging.info("📧 TEMP MAIL: Registering new account...")
        self.mail.register()
        logging.info(f"📧 TEMP MAIL: Created {self.mail.address}")
        return self.mail.address

    def _message_handler(self, message):
        """Callback for when a new message arrives."""
        subject = message.get('subject', 'No Subject')
        logging.info(f"📨 TEMP MAIL: New message received: {subject}")
        
        # Check text and html content
        text = message.get('text', '')
        html = message.get('html', [])
        content = text + " " + (html[0] if html and isinstance(html, list) else str(html))
        
        # Look for a 6-digit code
        code_match = re.search(r'\b\d{6}\b', content)
        if code_match:
            self.latest_code = code_match.group()
            logging.info(f"✨ TEMP MAIL: Found Verification Code: {self.latest_code}")
            self.is_listening = False

    def wait_for_hedra_code(self, timeout=120):
        """Starts listening and waits for the 6-digit code."""
        logging.info("⏳ TEMP MAIL: Waiting for Hedra verification code...")
        self.latest_code = None
        self.is_listening = True
        
        # Start listening in a non-blocking way if possible or use a loop
        self.mail.start(self._message_handler, interval=5)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.latest_code:
                self.mail.stop()
                return self.latest_code
            time.sleep(1)
            
        self.mail.stop()
        logging.error("❌ TEMP MAIL: Timeout reached while waiting for code.")
        return None

def farm_one_account():
    """Helper to test the flow."""
    tm = HedraTempMail()
    email = tm.create_account()
    print(f"EMAIL: {email}")
    print("Now trigger the 'Send Code' in Hedra, then I will catch it...")
    code = tm.wait_for_hedra_code()
    if code:
        print(f"SUCCESS! Code is: {code}")
        return {"email": email, "code": code}
    return None

if __name__ == "__main__":
    farm_one_account()
