import json
import os
from datetime import datetime

class PortfolioTracker:
    """
    Persistence layer for portfolio performance tracking.
    Saves snapshots of total balance to calculate ROI over time.
    """
    def __init__(self, filename="data/portfolio_history.json"):
        self.filename = filename
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists("data"):
            os.makedirs("data")
        if not os.path.exists(self.filename):
            with open(self.filename, "w") as f:
                json.dump([], f)

    def record_snapshot(self, total_balance):
        """Saves a timestamped balance snapshot."""
        try:
            with open(self.filename, "r") as f:
                history = json.load(f)
            
            # Keep only the last 500 snapshots to avoid file bloat
            if len(history) > 500:
                history = history[-500:]

            history.append({
                "timestamp": datetime.now().isoformat(),
                "balance": round(total_balance, 2)
            })

            with open(self.filename, "w") as f:
                json.dump(history, f, indent=4)
        except Exception as e:
            print(f"Error recording portfolio snapshot: {e}")

    def get_history(self):
        """Returns the full historical balance data."""
        try:
            with open(self.filename, "r") as f:
                return json.load(f)
        except:
            return []

    def get_analytics(self, live_balance=None, trade_history=None):
        """Calculates key performance indicators including trading fees and adjusted metrics."""
        history = self.get_history()
        
        # Calculate Estimated Fees from trade history (typical 0.05% taker fee for OKX)
        total_fees = 0
        win_trades = 0
        loss_trades = 0
        total_win_val = 0
        total_loss_val = 0
        
        if trade_history:
            for trade in trade_history:
                cost = float(trade.get('cost', 0))
                # Estimated fee (Taker 0.05%)
                fee = cost * 0.0005 
                total_fees += fee
                
                # Simple win/loss logic based on side (this is naive, usually we need realized PnL)
                # But as an estimate for MVP:
                if trade.get('pnl'): # If exchange provides realized PnL
                    pnl = float(trade['pnl'])
                    if pnl > 0:
                        win_trades += 1
                        total_win_val += pnl
                    else:
                        loss_trades += 1
                        total_loss_val += abs(pnl)

        if not history:
            return {
                "total_profit": 0,
                "fees": total_fees,
                "net_profit": -total_fees,
                "roi_pct": 0,
                "profit_factor": 0,
                "initial_balance": live_balance or 0,
                "current_balance": live_balance or 0,
                "is_new": True
            }

        initial = history[0]["balance"]
        current = live_balance if live_balance is not None else history[-1]["balance"]
        gross_profit = current - initial
        net_profit = gross_profit - total_fees
        roi = (net_profit / initial * 100) if initial > 0 else 0
        
        # Calculate Max Drawdown and Peak
        peak = 0
        max_dd = 0
        for entry in history:
            bal = entry['balance']
            if bal > peak:
                peak = bal
            
            dd = (peak - bal) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        
        # Check current live balance for new peak/drawdown
        if live_balance:
            if live_balance > peak:
                peak = live_balance
            dd = (peak - live_balance) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        profit_factor = round(total_win_val / total_loss_val, 2) if total_loss_val > 0 else (1.0 if total_win_val > 0 else 0)
        
        # New High-Level Metrics
        trade_count = len(trade_history) if trade_history else 0
        win_rate = round((win_trades / trade_count) * 100, 2) if trade_count > 0 else 0
        recovery_factor = round(net_profit / (initial * (max_dd)), 2) if max_dd > 0 else (round(net_profit/1, 2) if net_profit > 0 else 0)
        avg_trade_pnl = round((total_win_val - total_loss_val) / trade_count, 2) if trade_count > 0 else 0
        
        # Win/Loss Ratio
        avg_win = total_win_val / win_trades if win_trades > 0 else 0
        avg_loss = total_loss_val / loss_trades if loss_trades > 0 else 0
        wl_ratio = avg_win / avg_loss if avg_loss > 0 else 1.0
        
        # Kelly Criterion: K% = W - [(1-W)/R]
        w_decimal = win_rate / 100
        kelly = w_decimal - ((1 - w_decimal) / wl_ratio) if wl_ratio > 0 else 0
        
        # Estimated Sharpe (Simplified: Avg Return / Std Dev of Returns)
        # Using a fixed risk-free rate of 0 for simplification in this context
        returns = []
        if trade_history:
            for t in trade_history:
                if t.get('pnl'):
                    returns.append(float(t['pnl']) / initial)
        
        import math
        def stdev(data):
            if len(data) < 2: return 0
            mean = sum(data) / len(data)
            return math.sqrt(sum((x - mean) ** 2 for x in data) / (len(data) - 1))
        
        std_dev = stdev(returns)
        sharpe = (sum(returns)/len(returns)) / std_dev if std_dev > 0 and len(returns) > 0 else 0

        # Advanced Sortino & Streak Calculations
        consecutive_losses = 0
        max_consecutive_losses = 0
        downside_returns = []
        
        if trade_history:
            current_loss_streak = 0
            for t in trade_history:
                pnl = float(t.get('pnl', 0))
                ret = pnl / initial if initial > 0 else 0
                
                # Sortino: only negative returns
                if pnl < 0:
                    downside_returns.append(ret)
                    current_loss_streak += 1
                    if current_loss_streak > max_consecutive_losses:
                        max_consecutive_losses = current_loss_streak
                else:
                    current_loss_streak = 0

        # Sortino Ratio calculation
        def downside_deviation(data):
            if len(data) < 2: return 0.0001 # Avoid div by zero
            return math.sqrt(sum(x ** 2 for x in data) / len(data))
        
        dd_dev = downside_deviation(downside_returns)
        sortino = (sum(returns)/len(returns)) / dd_dev if dd_dev > 0 and len(returns) > 0 else 0
        
        # Profit Efficiency (Net Profit per hour of session)
        session_duration = (datetime.now() - datetime.fromisoformat(history[0]["timestamp"])).total_seconds() / 3600
        efficiency_per_hour = net_profit / session_duration if session_duration > 0 else 0

        return {
            "total_profit": round(gross_profit, 2),
            "fees": round(total_fees, 2),
            "net_profit": round(net_profit, 2),
            "roi_pct": round(roi, 2),
            "profit_factor": profit_factor,
            "win_rate": win_rate,
            "recovery_factor": recovery_factor,
            "avg_trade_pnl": avg_trade_pnl,
            "kelly_criterion": round(max(0, kelly) * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "max_loss_streak": max_consecutive_losses,
            "profit_efficiency": round(efficiency_per_hour, 2),
            "expectancy": round(avg_trade_pnl / initial * 100, 4) if initial > 0 else 0,
            "initial_balance": round(initial, 2),
            "current_balance": round(current, 2),
            "peak": round(peak, 2),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "start_time": history[0]["timestamp"],
            "is_new": len(history) < 2
        }

# Singleton
portfolio_tracker = PortfolioTracker()
