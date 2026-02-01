import asyncio
import os
import sys

# Добавляем корень проекта в пути поиска модулей
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.shared.utils.tiktok_stealth import tiktok_stealth_upload

async def test_browser_init():
    print("👽 ТЕСТ: Запуск проверки Браузера (Visible Mode)...")
    
    # Реальный файл для теста
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_video = os.path.join(base_dir, "src", "shared", "data", "marketing_outputs", "Export_20260130_201622.mp4")
    
    if not os.path.exists(test_video):
        # Fallback на любой mp4 в папке
        out_dir = os.path.join(base_dir, "src", "shared", "data", "marketing_outputs")
        potential = [f for f in os.listdir(out_dir) if f.endswith('.mp4')]
        if potential:
            test_video = os.path.join(out_dir, potential[0])
        else:
            print("❌ ОШИБКА: Нет MP4 файлов для теста.")
            return

    print(f"🎬 Используем для теста файл: {test_video}")
    dummy_caption = "A.S.T.R.A. Test Run #TradingAI #GhostProtocol"
    cookie_path = os.path.join(base_dir, "src", "shared", "data", "tiktok_cookies.txt")
    # Создаем папку если нет
    os.makedirs("src/shared/data", exist_ok=True)
    
    print("🚀 Попытка инициализации Undetected Chromedriver (v144)...")
    # Запускаем в видимом режиме (headless=False)
    result = await tiktok_stealth_upload(test_video, dummy_caption, cookie_path, headless=False)
    
    print(f"🏁 РЕЗУЛЬТАТ ТЕСТА: {result}")
    
    if "ERROR" in result:
        print("❌ Браузер не смог корректно инициализироваться или упал.")
    else:
        print("✅ БРАУЗЕР ОТКРЫЛСЯ! Ghost Protocol работает.")

if __name__ == "__main__":
    asyncio.run(test_browser_init())
