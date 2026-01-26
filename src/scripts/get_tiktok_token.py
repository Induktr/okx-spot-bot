import os
import sys
import requests
import webbrowser
import logging
import hashlib
import base64
import secrets
from urllib.parse import urlencode, urlparse, parse_qs

# Add project root to path so we can import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.app.config import config

# Configuration
REDIRECT_URI = "https://www.google.com/"
SCOPES = "video.upload,video.publish,user.info.basic"

# TikTok Auth Endpoints
AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
# Back to Sandbox because Production endpoint may reject Sandbox credentials with 'malformed' error
TOKEN_URL = "https://open-sandbox.tiktokapis.com/v2/oauth/token/"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_pkce():
    """Generates PKCE code_verifier and code_challenge."""
    code_verifier = secrets.token_urlsafe(64)
    code_challenge_hash = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge_hash).decode('utf-8').replace('=', '')
    return code_verifier, code_challenge

def get_sandbox_tokens(auth_code, client_key, client_secret, code_verifier):
    """Exchanges auth code for tokens."""
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_key": client_key.strip().strip('"').strip("'"),
        "client_secret": client_secret.strip().strip('"').strip("'"),
        "code": auth_code.strip(),
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier
    }
    try:
        response = requests.post(TOKEN_URL, headers=headers, data=data, timeout=10)
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "DNS_ERROR", "message": f"Не удалось найти сервер {TOKEN_URL}. Проверьте интернет или VPN."}
    except Exception as e:
        return {"error": str(e)}

def main():
    print("\n" + "="*60)
    print("💎 A.S.T.R.A. MANUAL TOKEN GENERATOR (SANDBOX + PKCE)")
    print("="*60)

    client_key = config.TIKTOK_CLIENT_KEY.strip().strip('"').strip("'")
    client_secret = config.TIKTOK_CLIENT_SECRET.strip().strip('"').strip("'")
    
    if not client_key or not client_secret or "your_" in client_key:
        print("❌ ERROR: Missing TIKTOK_CLIENT_KEY or TIKTOK_CLIENT_SECRET in .env!")
        return

    # 1. Generate PKCE
    code_verifier, code_challenge = generate_pkce()

    print(f"\n🔑 ВАШ VERIFIER (сохраните его!): {code_verifier}")

    # 2. Prepare Auth URL
    params = {
        "client_key": client_key,
        "scope": SCOPES,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    full_auth_url = f"{AUTH_URL}?{urlencode(params)}"
    
    print(f"\n1️⃣  Добавьте в TikTok Console: {REDIRECT_URI}")
    print(f"\n2️⃣  Откройте эту ссылку и авторизуйтесь:")
    print(f"🔗 {full_auth_url}")
    
    print("\n" + "-"*60)
    print("ИНСТРУКЦИЯ:")
    print("1. Разрешите доступ в браузере.")
    print("2. Вас перекинет на Google.")
    print("3. СКОПИРУЙТЕ всю адресную строку (URL) из браузера.")
    print("-"*60)
    
    callback_url = input("\n👉 Вставьте скопированный URL сюда: ").strip()
    
    try:
        # Extract code from URL
        parsed_url = urlparse(callback_url)
        query = parse_qs(parsed_url.query)
        auth_code = query.get('code', [None])[0]
        
        if not auth_code:
            # Maybe the user pasted just the code?
            if len(callback_url) > 20 and " " not in callback_url:
                auth_code = callback_url
            else:
                print("❌ Ошибка: Не удалось найти параметр 'code' в ссылке.")
                return

        print(f"✅ Код получен: {auth_code[:10]}...")
        
        # 3. Exchange for tokens
        print("\n📦 Запрашиваю Access Token (Sandbox Mode)...")
        token_data = get_sandbox_tokens(auth_code, client_key, client_secret, code_verifier)
        
        if isinstance(token_data, dict) and "data" in token_data and "access_token" in token_data["data"]:
            creds = token_data["data"]
            print("\n" + "🌟" * 20)
            print("   ПОЗДРАВЛЯЮ! ТОКЕН ПОЛУЧЕН   ")
            print("🌟" * 20)
            print(f"\nTIKTOK_ACCESS_TOKEN=\"{creds['access_token']}\"")
            print(f"\n✅ Скопируйте это в ваш .env файл.")
            print("="*60 + "\n")
        else:
            if isinstance(token_data, dict) and token_data.get("error") == "DNS_ERROR":
                print(f"\n⚠️ СЕТЕВАЯ ОШИБКА: {token_data.get('message')}")
            else:
                error_val = token_data.get('error') if isinstance(token_data, dict) else str(token_data)
                error_desc = token_data.get('error_description') if isinstance(token_data, dict) else ""
                print(f"\n❌ ОШИБКА TikTok: {error_val}")
                if error_desc: print(f"📝 Описание: {error_desc}")
                print(f"🔍 Полный ответ сервера: {token_data}")

    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")

if __name__ == "__main__":
    main()
