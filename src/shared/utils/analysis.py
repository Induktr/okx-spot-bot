import math
from typing import List, Optional, Dict, Any, Union

class TechnicalAnalysis:
    """
    Shared utility for manual technical indicators calculation.
    Avoids heavy dependencies like pandas-ta for compatibility.
    """
    
    @staticmethod
    def calculate_rsi(prices, period=14):
        """
        Calculates the Relative Strength Index (RSI).
        prices: list of closing prices.
        """
        if len(prices) < period + 1:
            return 50.0
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        
        avg_gain = float(sum(gains[:period])) / period
        avg_loss = float(sum(losses[:period])) / period
        
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        
        # Wilder's smoothing
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + float(gains[i])) / period
            avg_loss = (avg_loss * (period - 1) + float(losses[i])) / period
            
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100.0 - (100.0 / (1.0 + rs))
                
        return round(float(rsi), 2)

    @staticmethod
    def calculate_sma(prices, period=20):
        """Calculates Simple Moving Average."""
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        return round(float(sum(prices[-period:])) / period, 2)

    @staticmethod
    def calculate_ema(prices, period=20):
        """Calculates Exponential Moving Average."""
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        
        ema = float(sum(prices[:period])) / period
        multiplier = 2.0 / (period + 1)
        
        for price in prices[period:]:
            ema = (float(price) - ema) * multiplier + ema
            
        return round(float(ema), 2)

    @staticmethod
    def calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9):
        """Calculates MACD, Signal line and Histogram."""
        if len(prices) < slow_period + signal_period:
            return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
        
        def compute_ema(data, p):
            alpha = 2 / (p + 1)
            ema_val = sum(data[:p]) / p
            for val in data[p:]:
                ema_val = (val - ema_val) * alpha + ema_val
            return ema_val

        # Simple manual calculation of MACD
        fast_ema = []
        slow_ema = []
        
        # We need to build the EMA series
        curr_fast = float(sum(prices[:fast_period])) / fast_period
        curr_slow = float(sum(prices[:slow_period])) / slow_period
        
        macd_line: list[float] = []
        for i in range(len(prices)):
            price = float(prices[i])
            if i >= fast_period:
                curr_fast = (price - curr_fast) * (2.0 / (fast_period + 1)) + curr_fast
            if i >= slow_period:
                curr_slow = (price - curr_slow) * (2.0 / (slow_period + 1)) + curr_slow
            
            if i >= slow_period:
                macd_line.append(float(curr_fast - curr_slow))
        
        if len(macd_line) < signal_period:
            return None
            
        # Signal line
        signal_line = float(sum(macd_line[:signal_period])) / signal_period
        for val in macd_line[signal_period:]:
            signal_line = (float(val) - float(signal_line)) * (2.0 / (signal_period + 1)) + float(signal_line)
            
        macd_val = float(macd_line[-1])
        histogram = float(macd_val - signal_line)
        
        return {
            "macd": round(macd_val, 4),
            "signal": round(signal_line, 4),
            "histogram": round(histogram, 4)
        }

    @staticmethod
    def calculate_bollinger_bands(prices, period=20, std_dev=2):
        """Calculates Upper and Lower Bollinger Bands."""
        if len(prices) < period:
            # Return current price as bands if not enough data
            val = prices[-1] if prices else 0.0
            return {"upper": val, "lower": val, "middle": val}
        
        sma_val = float(sum(prices[-period:])) / period
        variance = float(sum([(float(x) - sma_val)**2 for x in prices[-period:]])) / period
        stdev = float(variance)**0.5
        
        return {
            "upper": round(float(sma_val + (std_dev * stdev)), 2),
            "mid": round(sma_val, 2),
            "lower": round(float(sma_val - (std_dev * stdev)), 2)
        }

    @staticmethod
    def calculate_atr(candles: List[List[Any]], period: int = 14) -> float:
        """Calculates Average True Range."""
        if not candles or len(candles) < period + 1:
            return 0.0
            
        tr_list: list[float] = []
        for i in range(1, len(candles)):
            high = float(candles[i][2])
            low = float(candles[i][3])
            prev_close = float(candles[i-1][4])
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            tr_list.append(float(tr))
            
        # Initial ATR (SMA of TR)
        atr = float(sum(tr_list[:period])) / period
        # Wilder's Smoothing
        for i in range(period, len(tr_list)):
            atr = (atr * (period - 1) + float(tr_list[i])) / period
            
        return round(float(atr), 2)

    @staticmethod
    def calculate_rvol(volumes: list, period: int = 20) -> float:
        """Calculates Relative Volume (RVOL)."""
        if len(volumes) < period:
            return 1.0
        relevant_vols = [float(v) for v in volumes[-period-1:-1]]
        avg_vol = sum(relevant_vols) / period
        if avg_vol == 0: return 1.0
        return round(float(volumes[-1]) / avg_vol, 2)

    @staticmethod
    def calculate_adx(candles: List[List[Any]], period: int = 14) -> float:
        """Calculates Average Directional Index."""
        if not candles or len(candles) < (period * 2):
            return 20.0 # Neutral ADX
        
        tr_list, dm_plus, dm_minus = [], [], []
        
        for i in range(1, len(candles)):
            high, low, close = float(candles[i][2]), float(candles[i][3]), float(candles[i][4])
            prev_high, prev_low = float(candles[i-1][2]), float(candles[i-1][3])
            prev_close = float(candles[i-1][4])
            
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_list.append(float(tr))
            
            move_up = high - prev_high
            move_down = prev_low - low
            
            if move_up > move_down and move_up > 0:
                dm_plus.append(float(move_up))
            else:
                dm_plus.append(0.0)
                
            if move_down > move_up and move_down > 0:
                dm_minus.append(float(move_down))
            else:
                dm_minus.append(0.0)
        
        def smooth(data: list[float], p: int) -> list[float]:
            if not data: return []
            smoothed = [float(sum(data[:p]))]
            for j in range(p, len(data)):
                smoothed.append(float(smoothed[-1]) - (float(smoothed[-1]) / p) + float(data[j]))
            return smoothed

        s_tr = smooth(tr_list, period)
        s_dm_plus = smooth(dm_plus, period)
        s_dm_minus = smooth(dm_minus, period)
        
        di_plus = [100.0 * (s_dm_plus[j] / s_tr[j]) if s_tr[j] != 0 else 0.0 for j in range(len(s_tr))]
        di_minus = [100.0 * (s_dm_minus[j] / s_tr[j]) if s_tr[j] != 0 else 0.0 for j in range(len(s_tr))]
        
        dx = []
        for j in range(len(di_plus)):
            div = di_plus[j] + di_minus[j]
            dx.append(100.0 * abs(di_plus[j] - di_minus[j]) / div if div != 0 else 0.0)
            
        if not dx: return None
        adx = float(sum(dx[:period])) / period
        for j in range(period, len(dx)):
            adx = (adx * (period - 1) + float(dx[j])) / period
            
        return round(float(adx), 2)

    @staticmethod
    def detect_pivots(candles: list, period: int = 10) -> Dict[str, Any]:
        """Detects local Support and Resistance."""
        if len(candles) < 2:
            return {"p": 0.0, "r1": 0.0, "s1": 0.0}
            
        last_c = candles[-2] # Use previous finished candle
        h, l, c = float(last_c[2]), float(last_c[3]), float(last_c[4])
        p = (h + l + c) / 3.0
        r1 = 2.0 * p - l
        s1 = 2.0 * p - h
        
        return {
            "p": round(float(p), 2),
            "r1": round(float(r1), 2),
            "s1": round(float(s1), 2)
        }

    # --- ADVANCED QUANTUM INDICATORS (Idea 5) ---
    
    @staticmethod
    def calculate_hurst(prices: List[float]) -> float:
        """
        Calculates the Hurst Exponent (Chaos vs Trend detector).
        H > 0.5: Persistent (Trend-following)
        H < 0.5: Anti-persistent (Mean Reverting)
        H = 0.5: Random Walk
        """
        if len(prices) < 20: return 0.5
        
        try:
            # 1. Calculate returns
            returns = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            n = len(returns)
            
            # 2. Mean of returns
            mean_ret = sum(returns) / n
            
            # 3. Cumulative deviations from mean
            deviations = [r - mean_ret for r in returns]
            cum_devs = [sum(deviations[:i+1]) for i in range(n)]
            
            # 4. Range
            r = max(cum_devs) - min(cum_devs)
            
            # 5. Standard Deviation
            variance = sum([(x - mean_ret)**2 for x in returns]) / n
            s = math.sqrt(variance)
            
            if s == 0: return 0.5
            
            # 6. Hurst result (R/S formula)
            hurst = math.log(r / s) / math.log(n)
            return round(float(hurst), 3)
        except Exception:
            return 0.5

    @staticmethod
    def calculate_fisher(prices: List[float], period: int = 10) -> float:
        """
        Ehlers Fisher Transform (DSP-based Zero-Lag Oscillator).
        Turns price into a Gaussian distribution for sharp turning point detection.
        """
        if len(prices) < period + 2: return 0.0
        
        try:
            # Fisher works on (High+Low)/2 or Close, we'll use limited prices
            relevant = prices[-(period + 2):]
            
            # Simple Normalized Price to [-1, 1]
            max_p = max(relevant)
            min_p = min(relevant)
            curr_p = prices[-1]
            
            if max_p == min_p: return 0.0
            
            # Value between -0.999 and 0.999
            value = 0.66 * ( (curr_p - min_p) / (max_p - min_p) - 0.5) * 2
            # Limit value to avoid ln(0) or ln(infinity)
            value = max(-0.999, min(0.999, value))
            
            # Fisher Transform formula
            fisher = 0.5 * math.log((1 + value) / (1 - value))
            return round(float(fisher), 3)
        except Exception:
            return 0.0

# Singleton instance
tech_analysis = TechnicalAnalysis()
