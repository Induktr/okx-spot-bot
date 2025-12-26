import schedule
import time
import logging
from core.config import config
from sensors.news_aggregator import news_aggregator
from brain.ai_client import ai_client
from hands.trader import trader
from scribe.logger import scribe

# Configure internal logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def astra_cycle():
    """
    The main autonomous cycle of A.S.T.R.A.
    """
    logging.info("--- Starting A.S.T.R.A. Cycle ---")
    
    try:
        # 0. Check Balance and Positions
        logging.info("Step 0: Checking account status...")
        balance = trader.get_balance()
        positions = trader.get_positions()
        current_price = trader.get_ticker()
        
        logging.info(f"Balance: {balance} USDT | Open Positions: {len(positions)}")
        
        # Format position data for AI context
        pos_context = "No open positions."
        if positions:
            p = positions[0] # Monitor the primary position
            unrealized_pnl = p.get('unrealizedPnl', 0)
            percentage = p.get('percentage', 0) # ROE %
            side = p.get('side', 'unknown')
            entry = p.get('entryPrice', 0)
            
            pos_context = (
                f"Position: {side.upper()} {p['symbol']}\n"
                f"Entry Price: {entry}\n"
                f"Current Price: {current_price}\n"
                f"Unrealized PnL: {unrealized_pnl} USDT\n"
                f"ROE: {percentage}%"
            )
            logging.info(f"Current Position: {side.upper()} | PnL: {unrealized_pnl} | ROE: {percentage}%")

        # 1. Sensors: Fetch News
        logging.info("Step 1: Fetching news headlines...")
        headlines = news_aggregator.get_recent_headlines(hours=6)
        
        # 2. Brain: Analyze Sentiment & Position
        logging.info("Step 2: Analysis by Gemini 3.0 (News + Position)...")
        analysis = ai_client.analyze_news(headlines, pos_context)
        
        # 3. Hands: Execute Strategy
        decision = analysis.get('action', 'WAIT').upper()
        logging.info(f"Step 3: Strategy result -> {decision}")
        
        execution_msg = "No execution needed."



        # Manage existing entry TP/SL if open
        if positions and decision == "WAIT":
            logging.info("Step 3.1: Syncing TP/SL for current position...")
            sync_res = trader.sync_sl_tp(positions[0])
            execution_msg = f"Synced TP/SL: {str(sync_res)}"

        if decision == "CLOSE" and positions:
            logging.info("Step 3.2: AI decided to CLOSE position.")
            result = trader.close_position(positions[0])
            execution_msg = f"CLOSED POSITION: {str(result)}"
        elif decision in ["BUY", "SELL"]:
            logging.info(f"Step 3.2: AI decided to open {decision} position.")
            result = trader.execute_order(decision, config.TRADE_AMOUNT)
            execution_msg = f"EXECUTED {decision}: {str(result)}"

        
        # 4. Scribe: Log results
        logging.info("Step 4: Recording results in report...")
        scribe.log_cycle(analysis, execution_msg)
        
        logging.info("A.S.T.R.A. Cycle finished successfully.")

        
    except Exception as e:
        error_msg = f"CRITICAL CYCLE ERROR: {str(e)}"
        logging.error(error_msg)
        # Log failure even if exception occurs
        scribe.log_cycle(
            {"sentiment_score": 0, "action": "ERROR", "reasoning": error_msg},
            "Failed to complete cycle."
        )

def main():
    """Entry point of the application."""
    logging.info("Initializing A.S.T.R.A. System...")
    
    # Run once at startup
    astra_cycle()
    
    # Schedule every 6 hours
    schedule.every(config.CYCLE_HOURS).hours.do(astra_cycle)
    
    logging.info(f"Scheduler active: Running every {config.CYCLE_HOURS} hours.")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
