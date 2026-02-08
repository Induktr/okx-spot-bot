import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import logging

class MacroGuardian:
    """
    Protection module for A.S.T.R.A.
    Tracks high-impact economic events (CPI, Fed, FOMC) and triggers Blackout Mode.
    Data Source: ForexFactory Economic Calendar (XML).
    """
    CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"

    def __init__(self):
        self.events = []
        self.blackout_active = False
        self.last_update = None

    async def update_calendar(self):
        """Fetches and parses the economic calendar."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.CALENDAR_URL, timeout=15) as response:
                    if response.status == 200:
                        content = await response.text()
                        root = ET.fromstring(content)
                        
                        new_events = []
                        for event in root.findall('event'):
                            def get_field(name):
                                el = event.find(name)
                                return el.text if el is not None else None

                            impact = get_field('impact')
                            if impact != 'High':
                                continue
                                
                            title = get_field('title')
                            country = get_field('country')
                            date_str = get_field('date')
                            time_str = get_field('time')
                            
                            if not all([title, country, date_str, time_str]):
                                continue

                            try:
                                dt_str = f"{date_str} {time_str}"
                                event_dt = datetime.strptime(dt_str, "%m-%d-%Y %I:%M%p")
                                
                                if country == "USD":
                                    new_events.append({
                                        "title": title,
                                        "time": event_dt,
                                        "impact": impact
                                    })
                            except Exception:
                                continue
                                
                        self.events = new_events
                        self.last_update = datetime.now()
                        logging.info(f"🛡️ MACRO: Calendar updated. Found {len(self.events)} high-impact USD events.")
                        return True
        except Exception as e:
            logging.error(f"❌ MACRO: Failed to update economic calendar: {e}")
            return False

    def get_blackout_status(self, buffer_minutes: int = 60) -> dict:
        """
        Checks if we are currently in or near a high-impact event window.
        Returns: {'active': bool, 'event': str or None, 'minutes_to_event': int}
        """
        now = datetime.now()
        for event in self.events:
            # Time difference in minutes
            diff = (event['time'] - now).total_seconds() / 60
            
            # If event is in the next 60m OR happened in the last 30m
            if -30 <= diff <= buffer_minutes:
                return {
                    "active": True,
                    "event": event['title'],
                    "minutes_to_event": int(diff)
                }
        
        return {"active": False, "event": None, "minutes_to_event": 0}

# Initialize Guardian
macro_guardian = MacroGuardian()
