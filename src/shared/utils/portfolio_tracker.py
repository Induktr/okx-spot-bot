import json
import os
import time
from datetime import datetime
from typing import Dict, Any, List

class PortfolioTracker:
    def __init__(self, filename=None):
        # Use relative path to src/shared/data to ensure consistency
        self.root_dir = os.getcwd()
        self.data_dir = os.path.join(self.root_dir, "src", "shared", "data")
        if not filename:
            self.filename = os.path.join(self.data_dir, "portfolio_history.json")
        else:
            self.filename = filename
            
        self._ensure_file()
        self._cache = []
        self._last_mtime = 0.0
        print(f"[PortfolioTracker] Tracking file: {self.filename}")

    def _ensure_file(self):
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir, exist_ok=True)
        if not os.path.exists(self.filename):
            with open(self.filename, "w") as f:
                json.dump([], f)

    def record_snapshot(self, balance):
        """Records balance and ensures it's persistent."""
        try:
            balance = float(balance)
            history = self.get_history()
            
            history.append({
                "timestamp": datetime.now().isoformat(),
                "balance": round(float(balance), 2)
            })
            
            # Limit to 1000 entries
            if len(history) > 1000:
                history = list(history[-1000:])
                
            with open(self.filename, "w") as f:
                json.dump(history, f, indent=4)
                
            self._cache = history
            self._last_mtime = float(time.time())
            return True
        except Exception as e:
            print(f"[PortfolioTracker] Record Error: {e}")
            return False

    def get_history(self):
        try:
            if os.path.exists(self.filename):
                with open(self.filename, "r") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            return []
        except:
            return []

    def reset_history(self, initial_balance):
        """Resets the baseline for profit calculation."""
        try:
            initial_balance = float(initial_balance)
            new_history = [{
                "timestamp": datetime.now().isoformat(),
                "balance": round(initial_balance, 2)
            }]
            with open(self.filename, "w") as f:
                json.dump(new_history, f, indent=4)
            self._cache = new_history
            self._last_mtime = float(time.time())
            return True
        except Exception as e:
            print(f"[PortfolioTracker] Reset Error: {e}")
            return False

    def get_analytics(self, live_balance=None, trade_history=None) -> Dict[str, Any]:
        """Returns analytics, ensuring Net Profit is calculated from the Global Portfolio."""
        history = self.get_history()
        
        live_bal_float = float(live_balance) if live_balance is not None else 0.0

        if not history:
            return {
                "net_profit": live_bal_float,
                "roi_pct": 0.0,
                "initial_balance": live_bal_float,
                "current_balance": live_bal_float,
                "total_profit": 0.0,
                "win_rate": 0,
                "profit_factor": 0,
                "start_time": datetime.now().isoformat()
            }

        initial_bal = float(history[0]["balance"])
        current_bal = live_bal_float if live_balance is not None else float(history[-1]["balance"])
        
        total_profit = current_bal - initial_bal
        roi = 0.0 if initial_bal == 0 else (total_profit / initial_bal * 100)
        
        return {
            "total_profit": round(float(total_profit), 2),
            "net_profit": round(float(total_profit), 2),
            "roi_pct": round(float(roi), 2),
            "initial_balance": round(float(initial_bal), 2),
            "current_balance": round(float(current_bal), 2),
            "win_rate": 0,
            "profit_factor": 0,
            "calmar_ratio": 0.0,
            "daily_volatility": 0.0,
            "recovery_factor": 0.0,
            "start_time": history[0]["timestamp"]
        }

# Singleton
portfolio_tracker = PortfolioTracker()
