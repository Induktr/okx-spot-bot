import logging

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
            return None
        
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
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # Wilder's smoothing
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                
        return round(rsi, 2)

    @staticmethod
    def calculate_sma(prices, period=20):
        """Calculates Simple Moving Average."""
        if len(prices) < period:
            return None
        return round(sum(prices[-period:]) / period, 2)

    @staticmethod
    def calculate_ema(prices, period=20):
        """Calculates Exponential Moving Average."""
        if len(prices) < period:
            return None
        
        ema = sum(prices[:period]) / period
        multiplier = 2 / (period + 1)
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
            
        return round(ema, 2)

    @staticmethod
    def calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9):
        """Calculates MACD, Signal Line, and Histogram."""
        if len(prices) < slow_period + signal_period:
            return None
        
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
        curr_fast = sum(prices[:fast_period]) / fast_period
        curr_slow = sum(prices[:slow_period]) / slow_period
        
        macd_line = []
        for i in range(len(prices)):
            if i >= fast_period:
                curr_fast = (prices[i] - curr_fast) * (2/(fast_period+1)) + curr_fast
            if i >= slow_period:
                curr_slow = (prices[i] - curr_slow) * (2/(slow_period+1)) + curr_slow
            
            if i >= slow_period:
                macd_line.append(curr_fast - curr_slow)
        
        if len(macd_line) < signal_period:
            return None
            
        # Signal line
        signal_line = sum(macd_line[:signal_period]) / signal_period
        for val in macd_line[signal_period:]:
            signal_line = (val - signal_line) * (2/(signal_period+1)) + signal_line
            
        macd_val = macd_line[-1]
        histogram = macd_val - signal_line
        
        return {
            "macd": round(macd_val, 4),
            "signal": round(signal_line, 4),
            "histogram": round(histogram, 4)
        }

    @staticmethod
    def calculate_bollinger_bands(prices, period=20, std_dev=2):
        """Calculates Upper and Lower Bollinger Bands."""
        if len(prices) < period:
            return None
        
        sma = sum(prices[-period:]) / period
        variance = sum([(x - sma)**2 for x in prices[-period:]]) / period
        stdev = variance**0.5
        
        return {
            "upper": round(sma + (std_dev * stdev), 2),
            "mid": round(sma, 2),
            "lower": round(sma - (std_dev * stdev), 2)
        }

    @staticmethod
    def calculate_atr(candles, period=14):
        """Calculates Average True Range."""
        if len(candles) < period + 1:
            return None
            
        tr_list = []
        for i in range(1, len(candles)):
            high = candles[i][2]
            low = candles[i][3]
            prev_close = candles[i-1][4]
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            tr_list.append(tr)
            
        # Initial ATR (SMA of TR)
        atr = sum(tr_list[:period]) / period
        # Wilder's Smoothing
        for i in range(period, len(tr_list)):
            atr = (atr * (period - 1) + tr_list[i]) / period
            
        return round(atr, 2)

    @staticmethod
    def calculate_rvol(volumes, period=20):
        """
        Calculates Relative Volume (RVOL).
        RVOL > 2.0 indicates institutional interest/breakout.
        """
        if len(volumes) < period:
            return 1.0
        avg_vol = sum(volumes[-period-1:-1]) / period
        if avg_vol == 0: return 1.0
        return round(volumes[-1] / avg_vol, 2)

    @staticmethod
    def detect_pivots(candles, period=10):
        """
        Detects local Support and Resistance (Swing Highs/Lows).
        """
        if len(candles) < period * 2 + 1:
            return {"sup": None, "res": None}
            
        closes = [c[4] for c in candles]
        highs = [c[2] for c in candles]
        lows = [c[3] for c in candles]
        
        # Simple Pivot Point calculation (Standard)
        last_c = candles[-2] # Use previous finished candle
        p = (last_c[2] + last_c[3] + last_c[4]) / 3
        r1 = 2 * p - last_c[3]
        s1 = 2 * p - last_c[2]
        
        return {
            "p": round(p, 2),
            "r1": round(r1, 2),
            "s1": round(s1, 2)
        }

# Singleton instance
tech_analysis = TechnicalAnalysis()
