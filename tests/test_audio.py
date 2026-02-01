import asyncio
import os
import sys

# Добавляем корень проекта в пути поиска модулей
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.shared.providers.audio_downloader import audio_downloader

async def test_audio_download():
    print("🎵 ТЕСТ: Запуск проверки AudioDownloader...")
    song_query = "Lofi Hip Hop for Trading"
    
    result = audio_downloader.download_trending_track(song_query)
    
    if result and os.path.exists(result):
        print(f"✅ УСПЕХ: Файл успешно скачан: {result}")
        print(f"📊 Размер файла: {os.path.getsize(result)} байт")
    else:
        print("❌ ОШИБКА: Не удалось скачать аудио.")

if __name__ == "__main__":
    asyncio.run(test_audio_download())
