import asyncio
import logging
import os
import sys

# Добавляем корень проекта в путь
sys.path.append(os.getcwd())

from src.features.media_core.orchestrator import MediaCoreOrchestrator
from src.shared.providers.social_publisher import social_publisher
from src.app.config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
# Force UTF-8 stdout for Windows
sys.stdout.reconfigure(encoding='utf-8')

async def test_tiktok_flow():
    print("\n" + "📱" * 20)
    print("🔥 TIKTOK CONTENT PIPELINE TEST")
    print("📱" * 20 + "\n")

    # 1. Проверка конфигурации
    if not config.TIKTOK_ACCESS_TOKEN:
        print("❌ ERROR: TIKTOK_ACCESS_TOKEN не найден в .env!")
        print("Сначала получите токен через src/scripts/get_tiktok_token.py")
        return

    # Импорты синглтонов напрямую, так как они не являются атрибутами класса
    from src.features.media_core.script_writer import script_writer
    from src.shared.providers.audio_provider import audio_provider
    from src.shared.providers.pexels_provider import pexels_provider
    from src.shared.providers.video_editor import video_editor
    
    # 2. Создаем тестовые данные (как будто Астра закрыла сделку)
    test_win = {
        'symbol': 'BTC/USDT',
        'roi': 42.69,
        'pnl': 1250.0,
        'side': 'LONG',
        'reasoning': 'Institutional breakdown of the $95k resistance with massive RVOL spike.',
        'id': f"test_{int(asyncio.get_event_loop().time())}"
    }

    try:
        # 3. Полный цикл генерации видео
        print("🎨 Шаг 1: Генерация ассетов (Сценарий, Звук, Фон)...")
        # script = script_writer.generate_viral_script(test_win) (Gemini ключ сгорел, используем заглушку)
        script = "Bitcoin just smashed resistance! A S T R A indicates a massive long opportunity. Don't miss this moon mission!"
        print(f"📝 Сценарий (Hardcoded): {script}")
        
        audio_path = await audio_provider.generate_speech(script, f"test_audio")
        video_bg = pexels_provider.get_random_background(query="trading candles")
        
        # Генерация оверлея (нужен для assemble_final_video)
        from src.shared.providers.video_generator import video_generator
        overlay_path = video_generator.generate_marketing_media(test_win, script)
        
        print("🎬 Шаг 2: Монтаж финального видео (MoviePy)...")
        # Исправленный вызов: assemble_final_video вместо assemble_short
        final_video = video_editor.assemble_final_video(
            video_bg, 
            audio_path, 
            overlay_path,
            test_win['id']
        )

        if not os.path.exists(final_video):
            print("❌ Ошибка: Видео не было создано.")
            return

        print(f"✅ Видео готово: {final_video}")

        # 4. Публикация в ТикТок
        print("\n🚀 Шаг 3: Публикация в TikTok...")
        description = (
            f"A.S.T.R.A AI detected a breakout! 🚀 {test_win['symbol']} +{test_win['roi']}% profit. "
            f"#trading #crypto #ai #astra #bitcoin"
        )
        
        # Мы вызываем именно метод ТикТока напрямую для теста
        result = await social_publisher._post_to_tiktok(final_video, description)
        
        if "SUCCESS" in result:
            print(f"🍾 ПОБЕДА! Видео отправлено в ТикТок. Результат: {result}")
        else:
            print(f"⚠️ Ошибка публикации: {result}")
            print("\nПодсказка: Если ошибка 403, проверьте, указали ли вы Redirect URI в Sandbox.")

    except Exception as e:
        print(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")
        logging.exception("Test failure details:")

if __name__ == "__main__":
    asyncio.run(test_tiktok_flow())
