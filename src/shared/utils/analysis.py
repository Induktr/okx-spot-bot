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

# Singleton instance
tech_analysis = TechnicalAnalysis()
