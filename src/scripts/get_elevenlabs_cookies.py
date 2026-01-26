import os
import sys
import asyncio
import json
from playwright.async_api import async_playwright

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

async def capture_elevenlabs_cookies():
    print("\n" + "="*60)
    print("🚀 ELEVENLABS COOKIE CAPTURE (CHROME PERSISTENT MODE)")
    print("="*60)
    
    # Path to your local Chrome data
    user_data_path = os.path.join(os.environ['LOCALAPPDATA'], 'Google', 'Chrome', 'User Data')
    
    async with async_playwright() as p:
        print("\n⚠️ ВНИМАНИЕ: Убедитесь, что все окна обычного Chrome ЗАКРЫТЫ.")
        
        try:
            # Launch using your ACTUAL Chrome profile to bypass Google protection
            context = await p.chromium.launch_persistent_context(
                user_data_dir=os.path.join(os.getcwd(), "data", "temp_chrome_profile"),
                channel="chrome", # Use installed Chrome
                headless=False,
                viewport={'width': 1280, 'height': 800},
                args=["--disable-blink-features=AutomationControlled"] # Hide automation flag
            )
            
            page = context.pages[0] if context.pages else await context.new_page()
            
            print("\n1. Открываю ElevenLabs...")
            await page.goto("https://elevenlabs.io/app/sign-in")
            
            print("\n📝 ДЕЙСТВИЕ:")
            print("   - Войдите в свой аккаунт (Google вход теперь должен работать).")
            print("   - Как только вы увидите страницу Speech Synthesis, вернитесь сюда.")
            
            print("\n⏳ Жду, пока вы авторизуетесь (таймаут 5 минут)...")
            
            await page.wait_for_url("**/speech-synthesis/**", timeout=300000)
            print("\n✅ Авторизация подтверждена!")
            
            await asyncio.sleep(3)
            cookies = await context.cookies()
            
            data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
            os.makedirs(data_dir, exist_ok=True)
            cookie_path = os.path.join(data_dir, "elevenlabs.io_cookies.txt")
            
            with open(cookie_path, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=4)
                
            print(f"\n🎉 ПРАЗДНИК! Куки сохранены в: {cookie_path}")
            
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            print("Подсказка: Если пишет 'user data directory is already in use', закройте все окна Chrome и попробуйте снова.")
        
        finally:
            if 'context' in locals():
                await context.close()

if __name__ == "__main__":
    asyncio.run(capture_elevenlabs_cookies())
