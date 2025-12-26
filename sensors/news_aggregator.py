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
        "https://cryptopanic.com/news/rss/"
    ]

    @staticmethod
    def clean_text(text: str) -> str:
        """Removes HTML tags and extra whitespace."""
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', text)
        return " ".join(text.split())

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
                    # Parse published date
                    # feedparser dates can be tricky, handling common formats
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

# Initialize aggregator
news_aggregator = NewsAggregator()
