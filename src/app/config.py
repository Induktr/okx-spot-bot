import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Config(BaseSettings):
    """
    Configuration class for A.S.T.R.A.
    Uses pydantic-settings to load variables from environment or .env file.
    """
    
    # Gemini API
    GEMINI_API_KEY: str = Field(..., env="GEMINI_API_KEY")
    GEMINI_MODEL: str = "gemini-3-flash-preview"
    GEMINI_RPM_LIMIT: int = 15
    
    # OKX API
    OKX_API_KEY: str = Field("", env="OKX_API_KEY")
    OKX_SECRET: str = Field("", env="OKX_SECRET")
    OKX_PASSWORD: str = Field("", env="OKX_PASSWORD")

    BINANCE_API_KEY: str = Field("", env="BINANCE_API_KEY")
    BINANCE_SECRET: str = Field("", env="BINANCE_SECRET")

    BYBIT_API_KEY: str = Field("", env="BYBIT_API_KEY")
    BYBIT_SECRET: str = Field("", env="BYBIT_SECRET")

    # List of active exchange IDs (e.g., ['okx', 'binance', 'bybit'])
    ACTIVE_EXCHANGES: list[str] = ["okx"]
    SANDBOX_MODES: dict[str, bool] = {"okx": True, "binance": False, "bybit": False}

    def load_settings(self):
        """Loads persistent settings from data/settings.json."""
        import json
        try:
            with open("data/settings.json", "r") as f:
                data = json.load(f)
                self.ACTIVE_EXCHANGES = data.get("active_exchanges", ["okx"])
                self.SANDBOX_MODES = data.get("sandbox_modes", {"okx": True, "binance": False, "bybit": False})
                self.OKX_API_KEY = data.get("okx_key", self.OKX_API_KEY)
                self.OKX_SECRET = data.get("okx_secret", self.OKX_SECRET)
                self.OKX_PASSWORD = data.get("okx_pass", self.OKX_PASSWORD)
                self.BINANCE_API_KEY = data.get("binance_key", self.BINANCE_API_KEY)
                self.BINANCE_SECRET = data.get("binance_secret", self.BINANCE_SECRET)
                self.BYBIT_API_KEY = data.get("bybit_key", self.BYBIT_API_KEY)
                self.BYBIT_SECRET = data.get("bybit_secret", self.BYBIT_SECRET)
        except Exception:
            self.ACTIVE_EXCHANGES = ["okx"]
            self.SANDBOX_MODES = {"okx": True, "binance": False, "bybit": False}

    def save_settings(self):
        """Saves current settings to data/settings.json."""
        import json
        with open("data/settings.json", "w") as f:
            json.dump({
                "active_exchanges": self.ACTIVE_EXCHANGES,
                "sandbox_modes": self.SANDBOX_MODES,
                "okx_key": self.OKX_API_KEY,
                "okx_secret": self.OKX_SECRET,
                "okx_pass": self.OKX_PASSWORD,
                "binance_key": self.BINANCE_API_KEY,
                "binance_secret": self.BINANCE_SECRET,
                "bybit_key": self.BYBIT_API_KEY,
                "bybit_secret": self.BYBIT_SECRET
            }, f, indent=4)
    
    # Trading Settings
    SYMBOLS: list[str] = []
    
    def load_symbols(self):
        """Loads symbols from local data/symbols.json."""
        import json
        try:
            with open("data/symbols.json", "r") as f:
                self.SYMBOLS = json.load(f)
        except Exception:
            self.SYMBOLS = ["BTC/USDT:USDT", "ETH/USDT:USDT"] # Fallback

    def save_symbols(self):
        """Persists current symbols to JSON."""
        import json
        with open("data/symbols.json", "w") as f:
            json.dump(self.SYMBOLS, f, indent=4)

    TRADE_AMOUNT: float = 20.0

    USE_SANDBOX: bool = True
    
    # Licensing
    ASTRA_LICENSE_KEY: str = Field("DEV-MODE-KEYS", env="ASTRA_LICENSE_KEY")
    
    def check_license(self):
        """
        Licensing Module (The Guard).
        Validates the key against remote or local rules.
        """
        # In production, this would make an API call to Induktr's license server.
        # For now, it uses a pattern validation.
        valid_keys = ["ASTRA-PRO-2026", "DEV-MODE-KEYS"]
        if self.ASTRA_LICENSE_KEY not in valid_keys:
            import sys
            print("\n" + "="*50)
            print("CRITICAL ERROR: LICENSE EXPIRED OR INVALID.")
            print("Contact support: @Induktr")
            print("="*50 + "\n")
            sys.exit(1)
        return True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# Initialize config object
config = Config()
config.load_symbols() # Load persistent symbols
config.load_settings() # Load active exchanges
config.check_license() # Lock system on startup

