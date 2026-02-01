import asyncio
import logging
import sys
import os
import time
import io

# Force UTF-8 for Windows Console to avoid charmap errors
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except:
        pass

# Добавляем путь к проекту
sys.path.append(os.getcwd())

from src.features.media_core.orchestrator import MediaCoreOrchestrator

# Настройка логов
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

async def force_run_viral_cycle(dry_run=True):
    print("\n" + "="*60)
    print(f"=== A.S.T.R.A. VIRAL MARKETING ENGINE: MANUAL START {'(DRY RUN)' if dry_run else ''} ===")
    print("="*60)

    import random
    import datetime
    from unittest.mock import patch, MagicMock

    assets = ["SOL/USDT", "AVAX/USDT", "ETH/USDT", "BTC/USDT", "LINK/USDT", "NEAR/USDT"]
    selected_asset = random.choice(assets)
    selected_roi = round(random.uniform(55.0, 185.0), 1)
    
    fake_win = {
        "id": f"test_{int(time.time())}",
        "symbol": selected_asset,
        "roi": selected_roi,
        "pnl": round(selected_roi * 10, 2),
        "close_price": 100,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "visual_analysis": {
            "trendlines": [{"type": "support", "slope": "up"}, {"type": "resistance", "slope": "down"}],
            "key_levels": [14.50, 12.00],
            "zones": [{"type": "demand", "price": 11.50}, {"type": "supply", "price": 15.00}],
            "checked_indicators": ["RSI", "EMA 200", "MACD", "Volume"]
        }
    }
    
    print(f"INPUT: Simulating Unique Win on {fake_win['symbol']} (+{fake_win['roi']}%)")

    # 2. Запускаем Орхестратор вручную
    orchestrator = MediaCoreOrchestrator()
    
    try:
        if dry_run:
            print("🛡️ DRY RUN ACTIVE: Social Publisher will be mocked (No real uploads).")
            # We mock the publisher inside the handler
            with patch('src.features.media_core.orchestrator.social_publisher') as mock_pub:
                mock_pub.publish_everywhere = MagicMock(return_value=asyncio.Future())
                mock_pub.publish_everywhere.return_value.set_result({"status": "DRY_RUN_SUCCESS"})
                
                await orchestrator._handle_video_marketing(fake_win)
        else:
            await orchestrator._handle_video_marketing(fake_win)
        
        print("\n" + "="*60)
        print("SUCCESS: CYCLE COMPLETE! Check 'src/shared/data/marketing_outputs' for the video.")
        print("="*60)
    except Exception as e:
        print(f"\nERROR: CYCLE FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--real", action="store_true", help="Perform real upload instead of dry-run")
    args = parser.parse_args()
    
    asyncio.run(force_run_viral_cycle(dry_run=not args.real))
