import asyncio
import os
import sys
import logging

# Добавляем корень проекта в пути
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.shared.utils.tiktok_stealth import tiktok_stealth_upload

async def setup_main_account():
    print("🚀 GHOST PROTOCOL: Запуск сессии безопасного входа...")
    
    # Путь к сессии нашего жирного аккаунта
    cookie_path = "src/shared/data/sessions/induktr_astra.json"
    os.makedirs("src/shared/data/sessions", exist_ok=True)
    
    # Прямой путь к видео (любому, просто для запуска браузера)
    test_video = "src/shared/data/assets/temp_setup.mp4"
    if not os.path.exists(test_video):
        os.makedirs(os.path.dirname(test_video), exist_ok=True)
        with open(test_video, "wb") as f: f.write(b"\0" * 1024)

    # Использование SOCKS5 туннеля через SSH
    proxy_url = "socks5://127.0.0.1:1080"
    
    print(f"🌐 ТРАФИК: Направляем через {proxy_url} (Zomro Server)")
    print("📢 ИНСТРУКЦИЯ: Сейчас откроется браузер. Залогиньтесь в ваш старый аккаунт TikTok.")
    print("📢 После успешного входа НЕ ЗАКРЫВАЙТЕ БРАУЗЕР сразу, побудьте в нем 1 минуту.")
    
    # Запускаем БЕЗ прогрева ленты, чтобы сразу попасть на страницу логина
    result = await tiktok_stealth_upload(
        video_path=test_video,
        caption="Setup session",
        cookie_path=cookie_path,
        headless=False,
        proxy=proxy_url,
        skip_warmup=True
    )
    
    print(f"🏁 РЕЗУЛЬТАТ: {result}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(setup_main_account())
