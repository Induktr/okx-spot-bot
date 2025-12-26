from datetime import datetime
import os

class Scribe:
    """
    Scribe module for A.S.T.R.A.
    Handles Markdown report generation.
    """
    def log_cycle(self, sentiment_data: dict, execution_result: str):
        """
        Logs the results of a trading cycle to a Markdown file.
        """
        today = datetime.now().strftime("%Y_%m_%d")
        log_file = f"astra_report_{today}.md"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        score = sentiment_data.get('sentiment_score', 0)

        action = sentiment_data.get('action', 'WAIT')
        reasoning = sentiment_data.get('reasoning', 'N/A')
        
        emoji = "🟡"
        if action == "BUY":
            emoji = "🟢"
        elif action == "SELL":
            emoji = "🔴"
        elif action == "CLOSE":
            emoji = "⚪"
            
        usage = sentiment_data.get('usage', {})

        prompt_tokens = usage.get('prompt_tokens', 0)
        output_tokens = usage.get('candidates_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)
        
        # Estimation for Gemini 3 Flash (approx 1M token limit)
        LIMIT = 1000000
        remaining_tokens = LIMIT - total_tokens
        remaining_percentage = (remaining_tokens / LIMIT) * 100
            
        report_entry = f"""
## Cycle Entry: {timestamp}
- **Sentiment Score:** {score}/10
- **Action Strategy:** {emoji} {action}
- **Token Usage Details:**
    - **Intake Tokens:** {prompt_tokens} (The size of news + history)
    - **Reflection Tokens:** {output_tokens} (The complexity of AI thinking)
    - **Total Tokens:** {total_tokens}
- **Analysis Capacity Remaining:** {remaining_percentage:.2f}% (Approx. {remaining_tokens:,} tokens left for today)
- **Reasoning:** {reasoning}
- **Execution Details:** 
```json
{execution_result}
```
---
"""
        
        # Write to file
        file_exists = os.path.exists(log_file)
        with open(log_file, "a", encoding="utf-8") as f:
            if not file_exists:
                f.write(f"# A.S.T.R.A. Activity Report - {today}\n")
            f.write(report_entry)

# Initialize logger
scribe = Scribe()
