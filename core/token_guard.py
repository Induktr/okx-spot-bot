import time
from threading import Lock
from .config import config

class TokenGuard:
    """
    Simple Rate Limiter for Gemini API Free Tier (15 RPM).
    Ensures that we don't exceed the request limit.
    """
    def __init__(self, rpm_limit: int = 15):
        self.rpm_limit = rpm_limit
        self.interval = 60.0 / rpm_limit
        self.last_call_time = 0.0
        self.lock = Lock()

    def wait_if_needed(self):
        """
        Calculates the time since the last call and sleeps if necessary
        to maintain the RPM limit.
        """
        with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_call_time
            
            if elapsed < self.interval:
                sleep_time = self.interval - elapsed
                time.sleep(sleep_time)
            
            self.last_call_time = time.time()

# Singleton instance for token guard
token_guard = TokenGuard(rpm_limit=config.GEMINI_RPM_LIMIT)
