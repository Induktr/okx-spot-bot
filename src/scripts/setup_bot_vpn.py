import os
import subprocess
import sys

def open_profile():
    # Путь к профилю бота
    profile_path = os.path.join(os.getcwd(), "data", "temp_chrome_profile")
    
    if not os.path.exists(profile_path):
        os.makedirs(profile_path, exist_ok=True)
        print(f"📁 Создан новый каталог профиля: {profile_path}")

    print(f"\n🚀 Запуск Chrome с профилем бота...")
    print(f"📍 Путь: {profile_path}")
    print("\nЧТО НУЖНО СДЕЛАТЬ:")
    print("1. Установите Planet VPN из Chrome Web Store.")
    print("2. Включите его и выберите нужную страну.")
    print("3. Убедитесь, что ElevenLabs открывается без ошибок.")
    print("4. Просто ЗАКРОЙТЕ браузер, когда закончите.\n")

    # Пытаемся найти Chrome
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]
    
    chrome_exe = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_exe = path
            break
            
    if not chrome_exe:
        print("❌ Не удалось найти chrome.exe. Пожалуйста, запустите Chrome вручную с флагом:")
        print(f'--user-data-dir="{profile_path}"')
        return

    cmd = [
        chrome_exe,
        f"--user-data-dir={profile_path}",
        "--no-first-run",
        "https://elevenlabs.io/app/speech-synthesis/text-to-speech"
    ]
    
    subprocess.Popen(cmd)
    print("✅ Браузер запущен. Жду настройки...")

if __name__ == "__main__":
    open_profile()
