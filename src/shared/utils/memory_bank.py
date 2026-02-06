import json
import os
import logging
import datetime
from typing import Dict, Any, Optional

class MemoryBank:
    """
    Module 4: MemoryBank
    Responsibility: Persisting AI analysis and market context across cycles.
    Helps to detect trend strengthening and avoid repetitive mistakes.
    """
    def __init__(self, storage_path: str = "src/shared/data/memory_bank.json"):
        self.storage_path = storage_path
        self.memory = self._load_storage()

    def _load_storage(self) -> Dict[str, Any]:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"❌ MEMORY: Failed to load storage: {e}")
        return {"history": {}, "last_decisions": {}}

    def _save_storage(self):
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=4)
        except Exception as e:
            logging.error(f"❌ MEMORY: Failed to save storage: {e}")

    def store_analysis(self, symbol: str, analysis: Dict[str, Any], market_context: str):
        """Records a new analysis cycle for a symbol."""
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "sentiment_score": analysis.get("sentiment_score"),
            "action": analysis.get("action"),
            "reasoning": analysis.get("reasoning"),
            "market_context": market_context[:500] # Limit size
        }
        
        if symbol not in self.memory["history"]:
            self.memory["history"][symbol] = []
            
        # Keep last 5 entries for trend analysis
        self.memory["history"][symbol].append(entry)
        self.memory["history"][symbol] = self.memory["history"][symbol][-5:]
        
        # Update last decision
        self.memory["last_decisions"][symbol] = entry
        self._save_storage()

    def get_context_summary(self, symbol: str) -> str:
        """Returns a string summary of past analysis to feed back into AI."""
        history = self.memory["history"].get(symbol, [])
        if not history:
            return "No previous analysis for this symbol."
            
        summary_lines = ["--- RECENT HISTORY ---"]
        for h in history:
            summary_lines.append(f"[{h['timestamp'][:16]}] Score: {h['sentiment_score']} | Action: {h['action']} | Reason: {h['reasoning']}")
        
        return "\n".join(summary_lines)

    def get_last_action(self, symbol: str) -> Optional[Dict[str, Any]]:
        return self.memory["last_decisions"].get(symbol)

# Global Memory Bank instance
memory_bank = MemoryBank()
