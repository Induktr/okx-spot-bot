import logging
from typing import Dict, Any, Optional
from src.shared.providers.db_provider import db_engine

class MemoryBank:
    """
    Module 4: MemoryBank
    Responsibility: Persisting AI analysis and market context via Database.
    """
    def __init__(self, storage_path: str = None):
        logging.info("🧠 MEMORY: Database storage active.")

    def store_analysis(self, symbol: str, analysis: Dict[str, Any], market_context: str):
        """Records a new analysis cycle to the database."""
        db_engine.store_analysis(symbol, analysis, market_context)

    def get_context_summary(self, symbol: str) -> str:
        """Returns a string summary of past analysis from the database."""
        history = db_engine.get_memory_history(symbol, limit=5)
        if not history:
            return "No previous analysis for this symbol."
            
        summary_lines = ["--- RECENT HISTORY ---"]
        for h in history:
            summary_lines.append(f"[{h['timestamp']}] Score: {h['score']} | Action: {h['action']} | Reason: {h['reasoning']}")
        
        return "\n".join(summary_lines)

    def get_last_action(self, symbol: str) -> Optional[Dict[str, Any]]:
        history = db_engine.get_memory_history(symbol, limit=1)
        return history[0] if history else None

# Global Memory Bank instance
memory_bank = MemoryBank()
