import asyncio
import logging
import sys
import os
import time

# Добавляем путь к проекту
sys.path.append(os.getcwd())

from src.features.media_core.orchestrator import MediaCoreOrchestrator

# Настройка логов
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

async def force_run_viral_cycle():
    print("\n" + "="*60)
    print("=== A.S.T.R.A. VIRAL MARKETING ENGINE: MANUAL START ===")
    print("="*60)

    import random
    import datetime
    assets = ["SOL/USDT", "AVAX/USDT", "ETH/USDT", "BTC/USDT", "LINK/USDT", "NEAR/USDT"]
    selected_asset = random.choice(assets)
    selected_roi = round(random.uniform(55.0, 185.0), 1)
    
    fake_win = {
        "id": f"test_{int(time.time())}",
        "symbol": selected_asset,
        "roi": selected_roi,
        "pnl": round(selected_roi * 10, 2),
        "close_price": 100,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    print(f"INPUT: Simulating Unique Win on {fake_win['symbol']} (+{fake_win['roi']}%)")

    # 2. Запускаем Орхестратор вручную
    orchestrator = MediaCoreOrchestrator()
    
    try:
        # Вызываем новый метод с Trend Scout
        # Обратите внимание: мы используем приватный метод _handle_video_marketing для теста
        await orchestrator._handle_video_marketing(fake_win)
        
        print("\n" + "="*60)
        print("SUCCESS: CYCLE COMPLETE! Check 'src/data/marketing_outputs' for the video.")
        print("="*60)
    except Exception as e:
        print(f"\nERROR: CYCLE FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(force_run_viral_cycle())
