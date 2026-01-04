import time
from threading import Lock
from src.app.config import config

class TokenGuard:
    """
    Simple Rate Limiter for Gemini API Free Tier (15 RPM).
    Ensures that we don't exceed the request limit.
    """
    def __init__(self, rpm_limit: int = 15):
        self.rpm_limit = rpm_limit
        # Conservative gap: 40 seconds between calls to avoid Free Tier 'Burst' detection
        self.interval = 40.0 
        self.last_call_time = 0.0
        self.lock = Lock()

    def wait_if_needed(self):
        """
        Ensures a safe cooldown between AI requests.
        Premium users bypass this Limit (High-Frequency).
        """
        if config.SUBSCRIPTION_STATUS == "PREMIUM":
            return

        with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_call_time
            
            if elapsed < self.interval:
                sleep_time = self.interval - elapsed
                import logging
                logging.info(f"TokenGuard: Cooling down Gemini API for {sleep_time:.1f}s...")
                time.sleep(sleep_time)
            
            self.last_call_time = time.time()

# Singleton instance with conservative limits
token_guard = TokenGuard()
