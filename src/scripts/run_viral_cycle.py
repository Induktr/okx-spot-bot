import asyncio
import logging
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.getcwd())

from src.features.media_core.orchestrator import MediaCoreOrchestrator

# Настройка логов
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

async def force_run_viral_cycle():
    print("\n" + "="*60)
    print("=== A.S.T.R.A. VIRAL MARKETING ENGINE: MANUAL START ===")
    print("="*60)

    # 1. Эмулируем "Победу" (Win Data)
    fake_win = {
        "id": "test_win_001",
        "symbol": "BTC/USDT",
        "roi": 25.5,
        "pnl": 255.0,
        "close_price": 105.2,
        "timestamp": "2024-01-20 12:00:00"
    }
    
    print(f"INPUT: Simulating High-ROI Win on {fake_win['symbol']} (+{fake_win['roi']}%)")

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
