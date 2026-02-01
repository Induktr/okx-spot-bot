import os
import subprocess
import time
import logging

def launch_manual_browser():
    """
    ULTIMATE STEALTH: Launches real Chrome through WARP tunnel.
    TikTok will see you as a regular user on a Cloudflare IP.
    """
    profile_path = os.path.abspath("src/shared/data/sessions/profile_induktr_astra")
    os.makedirs(profile_path, exist_ok=True)
    
    # Standard Chrome paths
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")

    # Your SSH Tunnel port
    proxy_url = "socks5://127.0.0.1:1080"
    
    print("\n" + "🛡️ " * 20)
    print("GHOST PROTOCOL: MANUAL AUTH ACTIVE")
    print("🛡️ " * 20)
    print(f"1. Открываем настоящий Chrome через SSH-туннель.")
    print(f"2. ВАЖНО: Весь трафик идет через Zomro + Cloudflare WARP.")
    print(f"3. ЗАЙДИТЕ НА: https://whoer.net")
    print("   Убедитесь, что ваш IP скрыт и принадлежит Cloudflare.")
    print(f"4. ПОСЛЕ ЭТОГО: Зайдите в TikTok и залогиньтесь.")
    print("5. ЗАКРОЙТЕ БРАУЗЕР КРЕСТИКОМ, когда закончите.")
    print("🛡️ " * 20 + "\n")

    cmd = [
        chrome_path,
        f"--user-data-dir={profile_path}",
        f"--proxy-server={proxy_url}",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
        "https://whoer.net" # Сразу открываем проверку IP
    ]
    
    try:
        subprocess.run(cmd)
        print("\n✅ СЕССИЯ ПОДГОТОВЛЕНА! Профиль сохранен. Можно запускать основного бота.")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")

if __name__ == "__main__":
    launch_manual_browser()