
import asyncio
import logging
import os
import sys

# Добавляем корень проекта в путь, чтобы импорты работали
sys.path.append(os.getcwd())

from src.shared.providers.social_publisher import social_publisher
from src.shared.providers.video_editor import video_editor
from src.shared.providers.audio_provider import audio_provider
from src.shared.providers.pexels_provider import pexels_provider
from src.shared.providers.video_generator import video_generator

logging.basicConfig(level=logging.INFO)
sys.stdout.reconfigure(encoding='utf-8')

async def test_instagram_flow():
    print("\n" + "📸" * 20)
    print("🔥 INSTAGRAM REELS PUSH TEST")
    print("📸" * 20)

    test_data = {
        'symbol': 'BTC/USDT',
        'roi': 45.2,
        'pnl': 1500.0,
        'side': 'LONG',
        'id': 'ig_test_1'
    }

    script = "Bitcoin moon mission is real! A.S.T.R.A. AI just caught a 45% move. Link in bio for the bot! #crypto #trading #ai #reels"

    try:
        print("\n🎨 Шаг 1: Подготовка медиа...")
        audio_path = await audio_provider.generate_speech(script, "ig_test_audio")
        video_bg = pexels_provider.get_random_background(query="finance neon")
        overlay_path = video_generator.generate_marketing_media(test_data, script)
        
        print("🎬 Шаг 2: Монтаж...")
        final_video = video_editor.assemble_final_video(
            video_bg, audio_path, overlay_path, "ig_final"
        )

        print("\n🚀 Шаг 3: Публикация в Instagram...")
        # Вызываем напрямую метод инстаграма
        result = await social_publisher._post_to_instagram(final_video, script)
        
        if "SUCCESS" in result:
            print(f"\n✅ ПОБЕДА! Видео в Инстаграме: {result}")
        else:
            print(f"\n❌ Ошибка: {result}")

    except Exception as e:
        print(f"\n💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")

if __name__ == "__main__":
    asyncio.run(test_instagram_flow())
