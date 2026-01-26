
import asyncio
from playwright.async_api import async_playwright
import sys
import os
import random
import string
import logging
import re
import shutil

# Add project root to path
sys.path.append(os.getcwd())
from src.scripts.hedra_manager import save_account

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

async def human_type(page, text):
    for char in text:
        await page.keyboard.type(char, delay=random.randint(70, 250))
        if random.random() > 0.9: await asyncio.sleep(0.3) # Simulate thinking

async def register_with_real_chrome():
    async with async_playwright() as p:
        try:
            logging.info("🔌 Connecting to your HUMAN Chrome session (Port 9222)...")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            
            # --- CLEAN STATE ---
            # We clear cookies only for Hedra and its auth provider to stay "clean" but "real"
            logging.info("🧹 Clearing Hedra site data to reset registration limits...")
            await context.clear_cookies(domain="hedra.com")
            await context.clear_cookies(domain="authkit.app")
            
            # --- TAB 1: MAIL ---
            mail_page = await context.new_page()
            email_address = None
            
            # Try Nullsto first
            try:
                logging.info("📧 Getting email from Nullsto...")
                await mail_page.goto("https://nullsto.edu.pl/", wait_until="domcontentloaded")
                await asyncio.sleep(5)
                for _ in range(10):
                    content = await mail_page.inner_text("body")
                    match = re.search(r'[a-zA-Z0-9._%+-]+@nullsto\.[a-zA-Z.]{2,}', content)
                    if match:
                        email_address = match.group().strip()
                        break
                    await asyncio.sleep(2)
            except: pass

            if not email_address:
                logging.info("📧 Nullsto failed, trying Mail.tm...")
                await mail_page.goto("https://mail.tm/", wait_until="domcontentloaded")
                await asyncio.sleep(5)
                email_address = await mail_page.locator("#address").input_value()
            
            if not email_address:
                logging.error("❌ Could not get any temporary email.")
                return

            password = "".join(random.choices(string.ascii_letters + string.digits, k=12)) + "A1!"
            logging.info(f"📧 Ready to register: {email_address}")

            # --- TAB 2: HEDRA ---
            hedra_page = await context.new_page()
            logging.info("🎭 Navigating to Hedra...")
            await hedra_page.goto("https://www.hedra.com/login", wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(5, 8))
            
            # Human scroll
            await hedra_page.mouse.wheel(0, 400)
            await asyncio.sleep(1)
            
            # Click Get Started / Login
            login_btn = hedra_page.locator("a:has-text('Get started'), i:has-text('Login')").first
            await login_btn.click()
            await asyncio.sleep(5)
            
            # Click Sign Up link
            try:
                signup_link = hedra_page.locator("text='Sign up', text='Зареєструватися'").last
                await signup_link.click()
                await asyncio.sleep(3)
            except: pass

            # --- DATA ENTRY ---
            logging.info("⌨️ Entering Names and Email...")
            # Fill first/last name to look more human
            try:
                await hedra_page.locator("input[name='firstName']").first.fill(random.choice(["James", "Robert", "John", "Michael", "William"]))
                await asyncio.sleep(0.5)
                await hedra_page.locator("input[name='lastName']").first.fill(random.choice(["Smith", "Brown", "Wilson", "Moore", "Taylor"]))
            except: pass

            email_field = hedra_page.locator("input[type='email'], input[name='emailAddress']").first
            await email_field.click()
            await human_type(hedra_page, email_address)
            await asyncio.sleep(1)
            
            # Click Continue
            continue_btn = hedra_page.locator("button:has-text('Continue'), button:has-text('Продовжити'), button[type='submit']").first
            await continue_btn.click()
            
            # --- CHECK FOR HUMAN VERIFICATION ERROR ---
            await asyncio.sleep(5)
            content = await hedra_page.content()
            if "verify the user is human" in content.lower():
                logging.error("🚨 Hedra blocked us as 'Not Human'.")
                logging.info("💡 ТИП: Попробуй сменить сервер VPN или нажми 'Продовжити' вручную в браузере сейчас.")
                # We wait a bit in case user wants to solve it manually
                await asyncio.sleep(20)
                if "password" not in hedra_page.url: return

            # Password
            logging.info("🔐 Setting password...")
            pwd_field = hedra_page.locator("input[type='password'], input[name='password']").first
            await pwd_field.wait_for(state="visible", timeout=20000)
            await pwd_field.click()
            await human_type(hedra_page, password)
            await asyncio.sleep(1)
            await hedra_page.locator("button[type='submit']").first.click()

            # --- OTP ---
            logging.info("⏳ Waiting for OTP code...")
            await mail_page.bring_to_front()
            otp_code = None
            for _ in range(40):
                content = await mail_page.content()
                matches = re.findall(r'\b\d{6}\b', content)
                for m in matches:
                    if m not in ["000000", "123456", "999999"]:
                        otp_code = m
                        break
                if otp_code: break
                if _ % 5 == 0:
                    try: await mail_page.locator("#fetch_emails, button:has-text('Fetch')").first.click()
                    except: pass
                await asyncio.sleep(4)

            if not otp_code:
                logging.error("❌ OTP not found.")
                return

            await hedra_page.bring_to_front()
            await hedra_page.keyboard.type(otp_code, delay=150)
            await asyncio.sleep(10)

            # Save results
            logging.info("🍪 Extracting cookies and saving account...")
            cookies = await context.cookies()
            save_account(email_address, password, cookies=cookies)
            logging.info(f"🎉 SUCCESS! Created: {email_address}")

        except Exception as e:
            logging.error(f"❌ Error: {e}")
        finally:
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(register_with_real_chrome())
