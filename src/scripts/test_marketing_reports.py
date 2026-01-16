
import asyncio
import logging
import os
import sys

# Добавляем корень проекта в путь
sys.path.append(os.getcwd())

from src.features.media_core.orchestrator import MediaCoreOrchestrator
from src.app.config import config
from src.features.media_core.script_writer import script_writer
from src.shared.providers.video_generator import video_generator
from src.shared.providers.social_publisher import social_publisher

logging.basicConfig(level=logging.INFO)
sys.stdout.reconfigure(encoding='utf-8')

async def test_telegram_ai_report():
    print("\n" + "🤖" * 20)
    print("🔥 TELEGRAM AI REPORT TEST")
    print("🤖" * 20)

    # Имитируем сделку со средним ROI (для триггера текстового поста)
    config.TELEGRAM_CHAT_ID = "-1003590962510" 
    
    test_win = {
        'symbol': 'BTC/USDT',
        'roi': 24.5,
        'pnl': 540.0,
        'side': 'LONG',
        'id': 'tg_report_test_123'
    }

    try:
        print("\n✍️ Шаг 1: AI перефразирует отчет (Gemini)...")
        report_text = script_writer.generate_rephrased_report(test_win)
        print(f"📝 Текст от AI:\n{report_text}")

        print("\n🎨 Шаг 2: Генерация PnL карточки...")
        image_path = video_generator.generate_marketing_media(test_win, "Telegram Report")
        
        print("\n📤 Шаг 3: Отправка в Telegram...")
        # Мы используем метод отправки изображения
        # Сначала убедимся, что он есть в social_publisher.py
        if hasattr(social_publisher, 'post_image_to_telegram'):
            await social_publisher.post_image_to_telegram(image_path, report_text)
            print("\n✅ УСПЕХ! Проверьте ваш Telegram канал.")
        else:
            # Если я забыл добавить метод, используем общую логику
            print("⚠️ Метод post_image_to_telegram не найден, пробую альтернативу...")
            # (Для теста просто выведем в консоль)
            print(f"Файл: {image_path}")

    except Exception as e:
        print(f"\n💥 ОШИБКА ТЕСТА: {e}")

if __name__ == "__main__":
    asyncio.run(test_telegram_ai_report())
