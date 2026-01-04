"""
User-specific trading instance that uses individual user settings from database.
Each user gets their own isolated trader with their own API keys.
"""

import logging
import time
from src.app import database
from src.features.trade_executor.trader import Trader

class UserTrader:
    """Manages trading for a single user with their personal settings."""
    
    def __init__(self, user_id: int, email: str):
        self.user_id = user_id
        self.email = email
        self.settings = None
        self.trader = None
        self.active = False
        
        logging.info(f"[UserTrader] Initialized for user {email} (ID: {user_id})")
    
    def load_settings(self) -> bool:
        """Load user settings from database."""
        self.settings = database.get_user_settings(self.user_id)
        
        if not self.settings:
            logging.warning(f"[UserTrader] No settings found for user {self.email}")
            return False
        
        # Check if user has at least one API key configured
        has_keys = any([
            self.settings.get('okx_api_key'),
            self.settings.get('binance_api_key'),
            self.settings.get('bybit_api_key')
        ])
        
        if not has_keys:
            logging.warning(f"[UserTrader] User {self.email} has no API keys configured")
            return False
        
        logging.info(f"[UserTrader] Settings loaded for {self.email}")
        return True
    
    def initialize_trader(self) -> bool:
        """Initialize trader with user's API keys."""
        if not self.settings:
            if not self.load_settings():
                return False
        
        try:
            # Create trader instance with user's settings
            self.trader = Trader(
                api_key=self.settings.get('okx_api_key', ''),
                secret=self.settings.get('okx_secret', ''),
                password=self.settings.get('okx_password', ''),
                user_id=self.user_id,
                user_email=self.email
            )
            
            self.active = True
            logging.info(f"[UserTrader] Trader initialized for {self.email}")
            return True
            
        except Exception as e:
            logging.error(f"[UserTrader] Failed to initialize trader for {self.email}: {e}")
            return False
    
    def execute_cycle(self):
        """Execute one trading cycle for this user."""
        if not self.active or not self.trader:
            logging.warning(f"[UserTrader] Cannot execute cycle for {self.email} - not active")
            return
        
        try:
            # Execute trading logic using user's trader instance
            self.trader.run_cycle()
            logging.info(f"[UserTrader] Cycle completed for {self.email}")
            
        except Exception as e:
            logging.error(f"[UserTrader] Cycle failed for {self.email}: {e}")
    
    def stop(self):
        """Stop trading for this user."""
        self.active = False
        logging.info(f"[UserTrader] Stopped trading for {self.email}")
    
    def get_status(self) -> dict:
        """Get current status of this user's trader."""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'active': self.active,
            'has_settings': self.settings is not None,
            'has_trader': self.trader is not None
        }


class UserTradingManager:
    """Manages all active user traders."""
    
    def __init__(self):
        self.user_traders = {}  # {user_id: UserTrader}
        logging.info("[UserTradingManager] Initialized")
    
    def sync_users(self):
        """Sync traders with premium users from database."""
        # Get all users with PREMIUM subscription
        all_users = database.get_all_users_with_subscriptions()
        premium_users = [u for u in all_users if u['status'] == 'PREMIUM']
        
        # Check if subscription is still valid
        current_time = time.time()
        active_premium_users = [
            u for u in premium_users 
            if u['expiry_timestamp'] > current_time
        ]
        
        logging.info(f"[UserTradingManager] Found {len(active_premium_users)} active premium users")
        
        # Remove traders for users who are no longer premium
        for user_id in list(self.user_traders.keys()):
            if user_id not in [u['id'] for u in active_premium_users]:
                logging.info(f"[UserTradingManager] Removing trader for user ID {user_id}")
                self.user_traders[user_id].stop()
                del self.user_traders[user_id]
        
        # Add traders for new premium users
        for user in active_premium_users:
            user_id = user['id']
            if user_id not in self.user_traders:
                logging.info(f"[UserTradingManager] Creating trader for {user['email']}")
                trader = UserTrader(user_id, user['email'])
                if trader.load_settings() and trader.initialize_trader():
                    self.user_traders[user_id] = trader
                else:
                    logging.warning(f"[UserTradingManager] Failed to activate trader for {user['email']}")
    
    def execute_all_cycles(self):
        """Execute trading cycle for all active users."""
        if not self.user_traders:
            logging.debug("[UserTradingManager] No active traders")
            return
        
        logging.info(f"[UserTradingManager] Executing cycles for {len(self.user_traders)} users")
        
        for user_id, trader in self.user_traders.items():
            try:
                trader.execute_cycle()
            except Exception as e:
                logging.error(f"[UserTradingManager] Error in cycle for user {user_id}: {e}")
    
    def get_all_statuses(self) -> list:
        """Get status of all user traders."""
        return [trader.get_status() for trader in self.user_traders.values()]
    
    def stop_all(self):
        """Stop all user traders."""
        for trader in self.user_traders.values():
            trader.stop()
        self.user_traders.clear()
        logging.info("[UserTradingManager] All traders stopped")


# Global instance
user_trading_manager = UserTradingManager()
