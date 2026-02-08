import logging
from datetime import datetime
from typing import Dict, Any, List
from src.shared.providers.db_provider import db_engine

class PortfolioTracker:
    def __init__(self, filename=None):
        self.mode = "REAL"
        logging.info(f"📊 PORTFOLIO: Database-Aware Tracking initialized.")

    def set_demo_mode(self, is_demo: bool):
        """Switches the active mode for database records."""
        self.mode = "DEMO" if is_demo else "REAL"
        logging.info(f"📊 PORTFOLIO: Switched to {self.mode} tracking.")

    def record_snapshot(self, balance):
        """Records balance to the high-performance database."""
        try:
            balance = float(balance)
            db_engine.record_balance(balance, mode=self.mode)
            
            # Update internal metrics for loss streak (still based on recent DB data)
            history = self.get_history()
            if len(history) >= 2:
                last_bal = float(history[-1]['balance'])
                prev_bal = float(history[-2]['balance'])
                if last_bal < prev_bal:
                    self.loss_streak = getattr(self, 'loss_streak', 0) + 1
                elif last_bal > prev_bal:
                    self.loss_streak = 0
            else:
                self.loss_streak = 0
            return True
        except Exception as e:
            logging.error(f"❌ PORTFOLIO ERROR: Record failed: {e}")
            return False

    def get_history(self):
        """Fetches history from the database provider."""
        return db_engine.get_portfolio_history(mode=self.mode)

    def reset_history(self, initial_balance):
        """Clears previous history and starts fresh with given balance."""
        db_engine.clear_portfolio_history(mode=self.mode)
        self.record_snapshot(initial_balance)
        logging.info(f"📊 PORTFOLIO: History reset to {initial_balance} ({self.mode} mode).")
        return True

    def get_analytics(self, live_balance=None, trade_history=None) -> Dict[str, Any]:
        """Returns analytics from database records."""
        history = self.get_history()
        
        live_bal_float = float(live_balance) if live_balance is not None else 0.0

        if not history:
            if live_bal_float > 0:
                self.record_snapshot(live_bal_float)
                history = self.get_history()
            
            if not history:
                return {
                    "net_profit": 0.0,
                    "roi_pct": 0.0,
                    "initial_balance": live_bal_float,
                    "current_balance": live_bal_float,
                    "high_water_mark": live_bal_float,
                    "drawdown_from_peak": 0.0,
                    "total_profit": 0.0,
                    "win_rate": 0,
                    "profit_factor": 0,
                    "start_time": datetime.now().isoformat()
                }

        initial_bal = float(history[0]["balance"]) if history else live_bal_float
        current_bal = live_bal_float if live_balance is not None else (float(history[-1]["balance"]) if history else 0.0)
        
        # High-Water Mark
        all_balances = [float(h["balance"]) for h in history]
        if live_balance is not None:
            all_balances.append(live_bal_float)
        hwm = float(max(all_balances)) if all_balances else initial_bal
        
        # Drawdown
        dd_from_peak = 0.0
        if hwm > 0:
            dd_from_peak = ((hwm - current_bal) / hwm) * 100
        
        total_profit = current_bal - initial_bal
        roi = 0.0 if initial_bal == 0 else (total_profit / initial_bal * 100)
        
        # Win Rate & Profit Factor
        win_rate = 0.0
        profit_factor = 0.0
        if trade_history:
            try:
                wins = 0
                trades_with_pnl = 0
                gross_p = 0.0
                gross_l = 0.0
                
                for t in trade_history:
                    info = t.get('info', {})
                    if not isinstance(info, dict): continue
                    
                    pnl_raw = (t.get('pnl') or info.get('realizedPnl') or info.get('fillPnl') or 0.0)
                    try:
                        pnl = float(pnl_raw)
                        fee_data = t.get('fee')
                        if fee_data and isinstance(fee_data, dict):
                            pnl -= float(fee_data.get('cost', 0))
                    except:
                        pnl = 0.0

                    if pnl != 0:
                        trades_with_pnl += 1
                        if pnl > 0:
                            wins += 1
                            gross_p += pnl
                        else:
                            gross_l += abs(pnl)
                
                if trades_with_pnl > 0:
                    win_rate = round(float(wins / trades_with_pnl) * 100, 2)
                if gross_l > 0:
                    profit_factor = round(float(gross_p / gross_l), 2)
                elif gross_p > 0:
                    profit_factor = 9.99
            except Exception as e:
                logging.error(f"Error calculating PnL metrics: {e}")

        # Metrics
        recovery_factor = 0.0
        max_dd_amount = float(max(0.0, hwm - current_bal))
        if max_dd_amount > 0 and total_profit > 0:
            recovery_factor = round(float(total_profit / max_dd_amount), 2)
        elif total_profit > 0:
            recovery_factor = 9.99
            
        calmar = 0.0
        if dd_from_peak > 0 and roi > 0:
            calmar = round(float(roi / dd_from_peak), 2)
        elif roi > 0:
            calmar = 9.99

        return {
            "total_profit": round(float(total_profit), 2),
            "net_profit": round(float(total_profit), 2),
            "roi_pct": round(float(roi), 2),
            "initial_balance": round(float(initial_bal), 2),
            "current_balance": round(float(current_bal), 2),
            "high_water_mark": round(float(hwm), 2),
            "drawdown_from_peak": round(float(dd_from_peak), 2),
            "max_drawdown_pct": round(float(dd_from_peak), 2),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "calmar_ratio": calmar,
            "recovery_factor": recovery_factor,
            "loss_streak": int(getattr(self, 'loss_streak', 0)),
            "start_time": str(history[0]["timestamp"]) if history else datetime.now().isoformat()
        }

# Singleton
portfolio_tracker = PortfolioTracker()
