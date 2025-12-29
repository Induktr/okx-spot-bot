import feedparser
import time
from datetime import datetime, timedelta
import re

class NewsAggregator:
    """
    Sensors module for A.S.T.R.A.
    Responsible for fetching and cleaning news from RSS feeds.
    """
    FEEDS = [
        "https://cointelegraph.com/rss",
        "https://cryptopanic.com/news/rss/",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://bitcoinmagazine.com/.rss/full/",
        "https://www.newsbtc.com/feed/",
        "https://cryptoslate.com/feed/",
        "https://decrypt.co/feed",
        "https://beincrypto.com/feed/"
    ]

    @staticmethod
    def clean_text(text: str) -> str:
        """Removes HTML tags and extra whitespace."""
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', text)
        return " ".join(text.split())

    def get_market_sentiment(self) -> dict:
        """
        Fetches the Crypto Fear & Greed Index (from alternative.me).
        Returns a dict: {'value': 50, 'classification': 'Neutral'}
        """
        try:
            import requests
            response = requests.get("https://api.alternative.me/fng/", timeout=10)
            data = response.json()
            if 'data' in data:
                sentiment = data['data'][0]
                return {
                    "value": sentiment.get('value'),
                    "classification": sentiment.get('value_classification')
                }
        except Exception as e:
            print(f"Error fetching sentiment: {e}")
        return {"value": "Unknown", "classification": "Unknown"}

    def get_recent_headlines(self, hours: int = 6) -> str:
        """
        Fetches news from RSS feeds and returns headlines from the last N hours.
        """
        headlines = []
        now = datetime.now()
        threshold = now - timedelta(hours=hours)

        for url in self.FEEDS:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    published_parsed = entry.get('published_parsed')
                    if published_parsed:
                        pub_date = datetime(*published_parsed[:6])
                        if pub_date > threshold:
                            title = self.clean_text(entry.title)
                            headlines.append(f"- {title}")
            except Exception as e:
                print(f"Error fetching feed {url}: {e}")

        # Remove duplicates
        unique_headlines = list(set(headlines))
        
        if not unique_headlines:
            return "No news headlines found in the last 6 hours."
            
        return "\n".join(unique_headlines)


    # Words that indicate market-moving events
    TRIGGER_KEYWORDS = [
        "SEC", "ETF", "Fed", "Rate", "Binance", "Coinbase", "Hack", "Exploit", 
        "Listing", "Delisting", "Arrest", "Approval", "Lawsuit", "Bankruptcy",
        "Surge", "Plunge", "ATH", "Crash", "Rally", "Bull", "Bear", "Launch",
        "Partnership", "Upgrade", "Mainnet", "Protocol", "Regulation", "Ban"
    ]

    def has_significant_events(self, headlines_text: str) -> bool:
        """
        Smart Wake-Up System. 
        Checks if the collected headlines contain any market-moving keywords.
        Returns True if AI analysis is required, False if the market is quiet.
        """
        if "No news headlines found" in headlines_text:
            return False
            
        # Check for keywords
        for keyword in self.TRIGGER_KEYWORDS:
            if keyword.lower() in headlines_text.lower():
                return True
        
        return False

# Initialize aggregator
news_aggregator = NewsAggregator()
