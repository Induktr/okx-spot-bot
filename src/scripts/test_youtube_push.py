
import asyncio
import logging
import os
import sys

# Добавляем корень проекта в путь
sys.path.append(os.getcwd())

from src.shared.providers.social_publisher import social_publisher
from src.shared.providers.video_editor import video_editor
from src.shared.providers.audio_provider import audio_provider
from src.shared.providers.pexels_provider import pexels_provider
from src.shared.providers.video_generator import video_generator

logging.basicConfig(level=logging.INFO)
sys.stdout.reconfigure(encoding='utf-8')

async def test_youtube_flow():
    print("\n" + "📺" * 20)
    print("🔥 YOUTUBE SHORTS PUSH TEST")
    print("📺" * 20)

    test_data = {
        'symbol': 'SOL/USDT',
        'roi': 88.5,
        'pnl': 2400.0,
        'side': 'LONG',
        'id': 'yt_test_1'
    }

    title = "Solana is UNSTOPPABLE! 🚀 +88% Profit"
    script = (
        "Solana is on fire! 🚀 Our A.S.T.R.A. AI bot just captured a massive 88% move. "
        "Don't trade alone, let the AI work for you. Check the link in the first comment! "
        "#solana #crypto #trading #ai #shorts"
    )

    try:
        print("\n🎨 Шаг 1: Подготовка видео...")
        audio_path = await audio_provider.generate_speech(script, "yt_test_audio")
        video_bg = pexels_provider.get_random_background(query="abstract technology")
        overlay_path = video_generator.generate_marketing_media(test_data, script)
        
        print("🎬 Шаг 2: Монтаж...")
        final_video = video_editor.assemble_final_video(
            video_bg, audio_path, overlay_path, "yt_final_shorts"
        )

        print("\n🚀 Шаг 3: Публикация в YouTube Shorts...")
        result = await social_publisher._post_to_youtube(final_video, title, script)
        
        if "SUCCESS" in result:
            print(f"\n✅ ГИГА-УСПЕХ! Видео на YouTube: {result}")
            print("💬 Также бот должен был оставить закрепленный комментарий под видео.")
        else:
            print(f"\n❌ Ошибка YouTube: {result}")

    except Exception as e:
        print(f"\n💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")

if __name__ == "__main__":
    asyncio.run(test_youtube_flow())
