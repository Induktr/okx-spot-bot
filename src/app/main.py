import asyncio
import datetime
import logging
import threading
import sys
import os

# Core ASTRA Modules
from src.app.orchestrator import AstraOrchestrator
from src.features.trade_executor.trader import refresh_traders, traders
from src.app.config import config
from src.shared.providers.telegram_provider import telegram_bot
from src.shared.utils.portfolio_tracker import portfolio_tracker
from src.features.media_core.orchestrator import MediaCoreOrchestrator
from src.app.dashboard.app import run_dashboard, start_dashboard_sync
from src.shared.utils.logger import scribe

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("astra_system.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

async def main_async():
    """Modern Async Entry Point for A.S.T.R.A. v1.5"""
    logging.info("🚀 A.S.T.R.A. v1.5: System Starting (Async Mode)...")
    
    # 0. Initialize System State
    await refresh_traders()
    orchestrator = AstraOrchestrator()
    
    # 1. Start Dashboard & Sync
    start_dashboard_sync()
    db_thread = threading.Thread(target=run_dashboard, daemon=True)
    db_thread.start()
    logging.info("🖥️ DASHBOARD: Active at http://localhost:5000")

    # 2. Start Telegram Command Listener - Legacy Sync Thread
    def start_tg_listener():
        try:
            telegram_bot.setup_commands(traders, portfolio_tracker)
            telegram_bot.start_polling()
        except Exception as e:
            logging.error(f"Telegram listener failed: {e}")

    tg_thread = threading.Thread(target=start_tg_listener, daemon=True)
    tg_thread.start()
    logging.info("📡 TELEGRAM: Signal listener active.")

    # 3. Media Core (Parallel AI Content Worker)
    media_orchestrator = MediaCoreOrchestrator()
    asyncio.create_task(media_orchestrator.run_forever(interval_hours=12))
    logging.info("📢 MEDIA CORE: AI Marketing Engine active.")

    next_run_time = datetime.datetime.now()
    FAILURE_THRESHOLD = 5
    consecutive_ai_failures = 0

    logging.info("⚡ SYSTEM: Fully Operational. Entering main decision loop.")

    while True:
        now = datetime.datetime.now()

        # Check if it's time for a scheduled run or a forced cycle
        if now >= next_run_time or config.FORCE_CYCLE:
            config.FORCE_CYCLE = False # Reset flag
            
            logging.info(f"⏳ CYCLE TRIGGER: Starting Astra Analysis Cycle...")
            status = await orchestrator.run_cycle()
            
            if status == "RETRY":
                consecutive_ai_failures += 1
                delay_sec = 60
                next_run_time = datetime.datetime.now() + datetime.timedelta(seconds=delay_sec)
                logging.warning(f"🔄 AI Brain was down ({consecutive_ai_failures}/{FAILURE_THRESHOLD}). Retry in {delay_sec}s...")
                
                if consecutive_ai_failures >= FAILURE_THRESHOLD:
                    logging.critical("🧠 AI Brain is unresponsive. Switching to Defensive Mode...")
                    # Possible emergency logic here
            elif status == "ERROR":
                logging.error("❌ Cycle failed due to internal error. Cooling down...")
                next_run_time = datetime.datetime.now() + datetime.timedelta(minutes=5)
            else:
                consecutive_ai_failures = 0
                next_run_time = datetime.datetime.now() + datetime.timedelta(minutes=config.CYCLE_INTERVAL_MINUTES)
                logging.info(f"✅ Cycle complete. Next run at: {next_run_time.strftime('%H:%M:%S')}")
            
        await asyncio.sleep(1)

def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logging.info("Shutdown requested by user.")
    except Exception as e:
        import traceback
        logging.critical(f"FATAL SYSTEM CRASH: {e}")
        logging.critical(traceback.format_exc())

if __name__ == "__main__":
    main()
