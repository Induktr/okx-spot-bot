import pytest
import unittest.mock as mock
from src.app.main import astra_cycle, check_equity_guardian, trigger_mindless_safety, apply_trailing_stop_engine
from src.app.config import config
import datetime

@pytest.fixture
def mock_trader():
    with mock.patch('src.app.main.traders') as m_traders:
        mock_t = mock.MagicMock()
        # Mock dictionary/list behaviors for traders
        m_traders.get.side_effect = lambda k, default=None: mock_t if k == 'okx' else default
        m_traders.values.return_value = [mock_t]
        m_traders.items.return_value = [('okx', mock_t)]
        m_traders.__iter__.return_value = iter(['okx'])
        
        # Internal exchange mock
        mock_t.exchange = mock.MagicMock()
        mock_t.exchange_id = 'okx'
        yield mock_t

@pytest.fixture
def mock_ai():
    with mock.patch('src.app.main.ai_client') as m_ai:
        yield m_ai

@pytest.fixture
def mock_portfolio():
    with mock.patch('src.app.main.portfolio_tracker') as m_pt:
        yield m_pt

@pytest.fixture
def mock_news():
    with mock.patch('src.app.main.news_aggregator') as m_news:
        m_news.get_combined_headlines.return_value = ["Standard market news"]
        m_news.get_market_mood.return_value = "Neutral"
        m_news.has_significant_events.return_value = (True, "Events found")
        yield m_news

def test_system_harmony_flow(mock_trader, mock_ai, mock_news, mock_portfolio):
    """
    Ensures Brain (AI) and Safety systems follow the hierarchy:
    1. Equity Guardian (Total Stop)
    2. Trading Schedule
    3. AI Brain (Decision)
    4. Trailing Stop (Constant Protection)
    """
    # Setup state
    config.BOT_ACTIVE = True
    config.SYMBOLS = ["BTC/USDT:USDT"]
    config.TRADING_DAYS = [0, 1, 2, 3, 4, 5, 6]
    config.TRADING_START_HOUR = 0
    config.TRADING_END_HOUR = 24
    
    mock_portfolio.get_analytics.return_value = {'max_drawdown_pct': 0.0}
    
    # Mock position
    pos = {
        'symbol': 'BTC/USDT:USDT',
        'side': 'long',
        'entryPrice': 90000,
        'markPrice': 95000,
        'unrealizedPnl': 500,
        'notional': 5000,
        'leverage': 10,
        'contracts': 1
    }
    mock_trader.get_positions.return_value = [pos]
    mock_trader.exchange.fetch_ticker.return_value = {'last': 95000, 'quoteVolume': 10000000}
    mock_trader.get_ohlcv.return_value = [[0, 0, 96000, 94000, 95000, 1000]] * 30
    mock_trader.get_funding_rate.return_value = 0.0001

    # AI wants to RE-ALIGN (ADJUST)
    mock_ai.analyze_news.return_value = {
        'target_symbol': 'BTC/USDT:USDT',
        'action': 'BUY', # Decision matches current side, should trigger re-align
        'sentiment_score': 10,
        'tp_pct': 0.1,
        'sl_pct': 0.05,
        'reasoning': 'Strong trend continuation'
    }

    # Execute cycle
    astra_cycle()

    # VERIFY: In long_short_mode or simple mode, sync_sl_tp should be called to protect position
    assert mock_trader.sync_sl_tp.called, "AI Decision should have triggered SL/TP synchronization"

def test_mindless_safety_activation(mock_trader):
    """Verify emergency mindless guard closes deep losses when AI is 'dead'."""
    pos = {
        'symbol': 'ETH/USDT:USDT',
        'side': 'long',
        'unrealizedPnl': -150, # -15% on $1000 notional
        'notional': 1000,
        'contracts': 1
    }
    mock_trader.get_positions.return_value = [pos]
    
    trigger_mindless_safety()
    
    mock_trader.close_position.assert_called_with(pos)
