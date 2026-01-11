import pytest
import datetime
from unittest.mock import patch, MagicMock
from src.app.config import Config
from src.app.main import is_trading_time

# Helper to create a fixed datetime
def create_mock_datetime(weekday, hour, minute=0):
    # Monday=0, Sunday=6
    # 2024-01-01 is a Monday
    # We'll use a fixed reference date and just adjust days/hours
    base = datetime.datetime(2024, 1, 1, hour, minute) 
    return base + datetime.timedelta(days=weekday)

@pytest.fixture
def mock_config():
    """Returns a config object with controllable settings."""
    cfg = MagicMock(spec=Config)
    cfg.TRADING_DAYS = [0, 1, 2, 3, 4] # Mon-Fri
    cfg.TRADING_START_HOUR = 0
    cfg.TRADING_END_HOUR = 24
    return cfg

@patch('src.app.main.config')
@patch('src.app.main.datetime')
def test_trading_time_standard_hours(mock_dt, mock_cfg_module, mock_config):
    """Test standard 24h trading on a weekday."""
    mock_cfg_module.TRADING_DAYS = [0, 1, 2, 3, 4]
    mock_cfg_module.TRADING_START_HOUR = 8
    mock_cfg_module.TRADING_END_HOUR = 20

    # Case 1: Active Time (Monday 10:00)
    mock_now = create_mock_datetime(weekday=0, hour=10)
    mock_dt.datetime.now.return_value = mock_now
    
    active, reason = is_trading_time()
    assert active is True
    assert reason == "Active"

    # Case 2: Before Start (Monday 06:00)
    mock_now = create_mock_datetime(weekday=0, hour=6)
    mock_dt.datetime.now.return_value = mock_now
    
    active, reason = is_trading_time()
    assert active is False
    assert "Outside Hours" in reason

    # Case 3: After End (Monday 22:00)
    mock_now = create_mock_datetime(weekday=0, hour=22)
    mock_dt.datetime.now.return_value = mock_now
    
    active, reason = is_trading_time()
    assert active is False
    assert "Outside Hours" in reason

@patch('src.app.main.config')
@patch('src.app.main.datetime')
def test_trading_time_overnight_schedule(mock_dt, mock_cfg_module):
    """Test overnight schedule (e.g. 22:00 to 06:00)."""
    mock_cfg_module.TRADING_DAYS = [0, 1, 2, 3, 4]
    mock_cfg_module.TRADING_START_HOUR = 22
    mock_cfg_module.TRADING_END_HOUR = 6

    # Case 1: Active Night (Monday 23:00)
    mock_now = create_mock_datetime(weekday=0, hour=23)
    mock_dt.datetime.now.return_value = mock_now
    
    active, reason = is_trading_time()
    assert active is True

    # Case 2: Active Morning (Monday 04:00)
    mock_now = create_mock_datetime(weekday=0, hour=4)
    mock_dt.datetime.now.return_value = mock_now
    
    active, reason = is_trading_time()
    assert active is True

    # Case 3: Updates Inactive Day (Mid-day Monday 12:00)
    mock_now = create_mock_datetime(weekday=0, hour=12)
    mock_dt.datetime.now.return_value = mock_now
    
    active, reason = is_trading_time()
    assert active is False
    assert "Outside Hours" in reason

@patch('src.app.main.config')
@patch('src.app.main.datetime')
def test_trading_time_weekend_lock(mock_dt, mock_cfg_module):
    """Test that day checking precedes hour checking."""
    mock_cfg_module.TRADING_DAYS = [0, 1, 2, 3, 4] # Mon-Fri
    mock_cfg_module.TRADING_START_HOUR = 0
    mock_cfg_module.TRADING_END_HOUR = 24

    # Saturday (weekday=5) at usually active time
    mock_now = create_mock_datetime(weekday=5, hour=12)
    mock_dt.datetime.now.return_value = mock_now
    
    active, reason = is_trading_time()
    assert active is False
    assert reason == "Day Not Configured"
