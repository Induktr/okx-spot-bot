import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
from src.shared.providers.macro_guardian import MacroGuardian

@pytest.fixture
def guardian():
    return MacroGuardian()

# Explicitly test only with asyncio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
@pytest.mark.anyio
async def test_update_calendar_parsing(guardian):
    """Test correctly parsing the ForexFactory XML response."""
    mock_xml = """
    <weeklycalendar>
        <event>
            <title>CPI m/m</title>
            <country>USD</country>
            <date>02-06-2026</date>
            <time>8:30am</time>
            <impact>High</impact>
        </event>
        <event>
            <title>Unimportant News</title>
            <country>EUR</country>
            <date>02-06-2026</date>
            <time>10:00am</time>
            <impact>Low</impact>
        </event>
    </weeklycalendar>
    """
    
    with patch('aiohttp.ClientSession.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=mock_xml)
        mock_get.return_value.__aenter__.return_value = mock_response
        
        success = await guardian.update_calendar()
        
        assert success is True
        assert len(guardian.events) == 1
        assert guardian.events[0]['title'] == "CPI m/m"
        assert guardian.events[0]['impact'] == "High"

def test_blackout_status_trigger(guardian):
    """Test if blackout mode triggers correctly based on time."""
    now = datetime.now()
    
    # 1. Event is soon (45 mins away) -> Should trigger
    guardian.events = [{
        "title": "FOMC Meeting",
        "time": now + timedelta(minutes=45),
        "impact": "High"
    }]
    status = guardian.get_blackout_status(buffer_minutes=60)
    assert status['active'] is True
    assert status['event'] == "FOMC Meeting"
    
    # 2. Event is far (120 mins away) -> Should NOT trigger
    guardian.events[0]['time'] = now + timedelta(minutes=120)
    status = guardian.get_blackout_status(buffer_minutes=60)
    assert status['active'] is False
    
    # 3. Event just happened (10 mins ago) -> Should trigger (grace period)
    guardian.events[0]['time'] = now - timedelta(minutes=10)
    status = guardian.get_blackout_status(buffer_minutes=60)
    assert status['active'] is True
    
    # 4. Event was long ago (60 mins ago) -> Should NOT trigger
    guardian.events[0]['time'] = now - timedelta(minutes=60)
    status = guardian.get_blackout_status(buffer_minutes=60)
    assert status['active'] is False
