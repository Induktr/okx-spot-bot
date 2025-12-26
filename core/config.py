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
    
    # Trading Settings
    SYMBOL: str = "BTC/USDT"

    TRADE_AMOUNT: float = 10.0
    USE_SANDBOX: bool = True
    
    # Scheduler
    CYCLE_HOURS: int = 3
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# Initialize config object
config = Config()
