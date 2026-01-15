import os
import sys
import requests
import logging
import webbrowser
import hashlib
import base64
from dotenv import load_dotenv

# Принудительная загрузка .env
load_dotenv()
sys.path.append(os.getcwd())
from src.app.config import config

logging.basicConfig(level=logging.INFO)

CLIENT_KEY = config.TIKTOK_CLIENT_KEY
CLIENT_SECRET = config.TIKTOK_CLIENT_SECRET
REDIRECT_URI = "https://www.google.com"

# --- ФИКС ДЛЯ ПЕРЕЗАПУСКОВ ---
# Используем фиксированный verifier, чтобы он не менялся при перезапуске скрипта.
# Это позволяет вам скопировать ссылку, закрыть скрипт, открыть снова и вставить код.
FIXED_VERIFIER = "astra_stable_verifier_key_for_manual_auth_process_1234567890"

def get_challenge(verifier):
    sha256 = hashlib.sha256(verifier.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(sha256).decode('utf-8').replace('=', '')

def main():
    print("\n" + "="*60)
    print("🚀 TIKTOK AUTH v3 (RESTART-SAFE)")
    print("="*60)
    
    challenge = get_challenge(FIXED_VERIFIER)
    scope = "user.info.basic,video.upload,video.publish,video.list"
    
    auth_url = (
        f"https://www.tiktok.com/v2/auth/authorize/"
        f"?client_key={CLIENT_KEY}"
        f"&scope={scope}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&code_challenge={challenge}"
        f"&code_challenge_method=S256"
    )
    
    print("\n1. Ссылка для входа (откроется в браузере):")
    print(auth_url)
    print("\n2. После авторизации вас перекинет на Google.")
    print("3. Скопируйте ВСЮ ссылку из адресной строки Google.")
    print("-" * 60)
    
    webbrowser.open(auth_url)
    
    full_url = input("\n👉 Вставьте ПОЛНУЮ ссылку Google сюда: ").strip()
    
    # Умное извлечение кода из любой ссылки
    code = ""
    if "code=" in full_url:
        # Берем кусок между code= и следующим & (или концом строки)
        code = full_url.split("code=")[1].split("&")[0]
        # Декодируем %-символы на случай, если браузер их закодировал
        import urllib.parse
        code = urllib.parse.unquote(code)
    else:
        # Если вдруг вставили "голый" код
        code = full_url

    print(f"\n🎯 Используем код: {code[:10]}...")
    print("🔄 Обмениваю на токен...")
    
    url = "https://open.tiktokapis.com/v2/oauth/token/"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_key": CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code_verifier": FIXED_VERIFIER  # Отправляем тот же verifier!
    }
    
    try:
        response = requests.post(url, headers=headers, data=data)
        res_data = response.json()
        
        if response.status_code == 200 and 'access_token' in res_data:
            token = res_data['access_token']
            print("\n" + "✅" * 10)
            print("УСПЕХ! Токен получен.")
            
            # Сохранение
            env_path = os.path.join(os.getcwd(), '.env')
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            new_lines = []
            token_saved = False
            for line in lines:
                if line.startswith('TIKTOK_ACCESS_TOKEN='):
                    new_lines.append(f'TIKTOK_ACCESS_TOKEN={token}\n')
                    token_saved = True
                else:
                    new_lines.append(line)
            
            if not token_saved:
                new_lines.append(f'\nTIKTOK_ACCESS_TOKEN={token}\n')
                
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
                
            print(f"💾 Токен сохранен в .env")
            print("🎬 Можно запускать тест видео!")
        else:
            print(f"\n❌ Ошибка TikTok API: {res_data}")
            
    except Exception as e:
        print(f"\n❌ Ошибка сети: {e}")

if __name__ == "__main__":
    main()
