
import unittest
import os
from src.shared.utils.report_parser import ReportParser

class TestReportParser(unittest.TestCase):
    def setUp(self):
        self.test_dir = "tests/temp_reports"
        os.makedirs(self.test_dir, exist_ok=True)
        self.parser = ReportParser(report_dir=self.test_dir)

    def tearDown(self):
        # Cleanup
        for f in os.listdir(self.test_dir):
            os.remove(os.path.join(self.test_dir, f))
        os.rmdir(self.test_dir)

    def test_markdown_parsing_logic(self):
        """Logic Test: Verify that the parser correctly extracts structured data from Markdown logs."""
        # Create a dummy report file
        content = """---
## Cycle Entry: 2026-01-05 12:00:00
**Sentiment Score:** 8/10
**Action Strategy:** 🚀 BUY
**Reasoning:** Bullish convergence on RSI and EMA.
- **Execution Details:**
```json
{"target_symbol": "BTC/USDT:USDT", "budget_usdt": 50, "leverage": 5}
```
---
## Cycle Entry: 2026-01-05 12:05:00
**Sentiment Score:** 3/10
**Action Strategy:** ⚠️ WAIT
**Reasoning:** Market is flat, no clear signals.
- **Execution Details:**
```json
{"reason": "No entry condition met"}
```
"""
        with open(os.path.join(self.test_dir, "astra_report_20260105.md"), "w", encoding="utf-8") as f:
            f.write(content)
        
        parsed = self.parser.parse_latest()
        
        self.assertEqual(len(parsed), 2)
        
        # Newest first (reversed)
        latest = parsed[0]
        self.assertEqual(latest['timestamp'], "2026-01-05 12:05:00")
        self.assertEqual(latest['score'], 3)
        self.assertEqual(latest['action'], "WAIT")
        self.assertEqual(latest['reasoning'], "Market is flat, no clear signals.")
        self.assertEqual(latest['details']['reason'], "No entry condition met")

        # Second entry
        first = parsed[1]
        self.assertEqual(first['score'], 8)
        self.assertEqual(first['action'], "BUY")
        self.assertEqual(first['details']['target_symbol'], "BTC/USDT:USDT")

if __name__ == "__main__":
    unittest.main()
