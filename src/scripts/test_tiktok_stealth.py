
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

async def test_tiktok_stealth_flow():
    print("\n" + "🎭" * 20)
    print("🚀 TIKTOK STEALTH PUSH TEST (COOKIES)")
    print("🎭" * 20)

    test_data = {
        'symbol': 'ETH/USDT',
        'roi': 32.8,
        'pnl': 850.0,
        'side': 'LONG',
        'id': 'tt_stealth_1'
    }

    script = "Ethereum is heating up! 🚀 A.S.T.R.A. AI just locked in 32% profit. Trading bot link in bio! #crypto #trading #ai #tiktok #astra"

    try:
        # Проверка наличия куков
        cookie_path = os.path.join(os.getcwd(), "data", "tiktok_cookies.txt")
        if not os.path.exists(cookie_path):
            print(f"❌ Файл куков не найден по пути: {cookie_path}")
            return

        print("\n🎨 Шаг 1: Подготовка видео...")
        audio_path = await audio_provider.generate_speech(script, "tt_stealth_audio")
        video_bg = pexels_provider.get_random_background(query="cyberpunk city")
        overlay_path = video_generator.generate_marketing_media(test_data, script)
        
        print("🎬 Шаг 2: Монтаж...")
        final_video = video_editor.assemble_final_video(
            video_bg, audio_path, overlay_path, "tt_stealth_final"
        )

        print("\n🥷 Шаг 3: Загрузка в TikTok через Cookies...")
        # Передаем только 2 аргумента: путь к видео и текст
        result = await social_publisher._post_to_tiktok(final_video, script)
        
        if "SUCCESS" in result:
            print(f"\n✅ УСПЕХ! Видео отправлено в ТикТок: {result}")
        else:
            print(f"\n❌ Ошибка: {result}")

    except Exception as e:
        print(f"\n💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")

if __name__ == "__main__":
    asyncio.run(test_tiktok_stealth_flow())
