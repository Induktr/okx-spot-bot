import asyncio
import logging
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.getcwd())

from src.shared.providers.social_publisher import social_publisher

# Настройка логов
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

async def test_stealth_tiktok():
    print("\n" + "="*60)
    print("🥷 TIKTOK STEALTH POSTER: MANUAL TEST")
    print("="*60)

    # 1. Ищем готовое видео
    output_dir = "src/data/marketing_outputs"
    videos = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
    
    if not videos:
        print("❌ FAILED: No videos found in 'src/data/marketing_outputs'. Run 'run_viral_cycle.py' first.")
        return

    video_path = os.path.join(output_dir, videos[0])
    caption = "🤖 A.S.T.R.A. AI Trading Bot in action! #trading #crypto #ai #passiveincome"

    print(f"📦 FOUND VIDEO: {video_path}")
    print(f"📝 CAPTION: {caption}")

    # 2. Проверяем куки
    cookie_path = "data/tiktok_cookies.txt"
    if not os.path.exists(cookie_path):
        print(f"❌ FAILED: '{cookie_path}' not found. Please export your TikTok cookies to this file.")
        return

    # 3. Запускаем "партизанский" пост
    print("\n🚀 LAUNCHING STEALTH UPLOAD... (This may take 1-2 minutes)")
    try:
        result = await social_publisher._post_to_tiktok_cookies(video_path, caption)
        
        print("\n" + "="*60)
        print(f"🏁 RESULT: {result}")
        print("="*60)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_stealth_tiktok())
