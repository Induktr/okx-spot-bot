import os
import re
import json
from datetime import datetime

class ReportParser:
    """
    Parses ASTRA Markdown reports to extract data for the dashboard.
    """
    def __init__(self, report_dir="."):
        self.report_dir = report_dir

    def get_latest_report_file(self):
        files = [f for f in os.listdir(self.report_dir) if f.startswith("astra_report_") and f.endswith(".md")]
        if not files:
            return None
        return sorted(files, reverse=True)[0]

    def parse_latest(self):
        filename = self.get_latest_report_file()
        if not filename:
            return []

        filepath = os.path.join(self.report_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Split by horizontal rule
        entries = content.split("---")
        parsed_entries = []

        for entry in entries:
            if "## Cycle Entry:" not in entry:
                continue
            
            try:
                # Extract Timestamp
                ts_match = re.search(r"## Cycle Entry: ([\d-]+\s[\d:]+)", entry)
                timestamp = ts_match.group(1) if ts_match else "Unknown"

                # Extract Sentiment Score
                score_match = re.search(r"\*\*Sentiment Score:\*\* (\d+)/10", entry)
                score = int(score_match.group(1)) if score_match else 0

                # Extract Action
                action_match = re.search(r"\*\*Action Strategy:\*\* .*? (BUY|SELL|WAIT|CLOSE|ADJUST|ERROR)", entry)
                action = action_match.group(1) if action_match else "WAIT"

                # Extract Reasoning
                reason_match = re.search(r"\*\*Reasoning:\*\* (.*?)\n- \*\*Execution", entry, re.DOTALL)
                reasoning = reason_match.group(1).strip() if reason_match else ""

                # Extract Execution JSON
                json_match = re.search(r"```json\n(.*?)\n```", entry, re.DOTALL)
                execution_raw = json_match.group(1) if json_match else "{}"
                
                try:
                    execution_data = json.loads(execution_raw)
                except:
                    execution_data = {}

                parsed_entries.append({
                    "timestamp": timestamp,
                    "score": score,
                    "action": action,
                    "reasoning": reasoning,
                    "details": execution_data
                })

            except Exception as e:
                print(f"Error parsing entry: {e}")

        return parsed_entries[::-1] # Newest first

# Singleton
report_parser = ReportParser()
