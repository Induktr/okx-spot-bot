
import logging
import os
import asyncio
import json
import time
from playwright.async_api import async_playwright

async def tiktok_stealth_upload(video_path, caption, cookie_path, headless=False):
    """
    Advanced TikTok Upload with Session Harvesting.
    If login fails, lets the user login manually and SAVES the session for next time.
    """
    logging.info(f"🎬 TIKTOK STEALTH: Starting session for {video_path}")
    
    # Path for full session state (much more reliable than cookies)
    session_state_path = cookie_path.replace('.txt', '.json')

    async with async_playwright() as p:
        browser = None
        context = None
        try:
            # Launch browser with advanced stealth
            browser_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-position=0,0",
                "--ignore-certificate-errors",
                "--allow-running-insecure-content",
                "--disable-notifications",
            ]
            
            proxy_config = None
            if os.getenv("TIKTOK_PROXY"):
                proxy_config = {"server": os.getenv("TIKTOK_PROXY")}
                logging.info(f"🥷 TIKTOK: Using Residential Proxy: {proxy_config['server']}")

            browser = await p.chromium.launch(
                headless=headless, 
                args=browser_args,
                proxy=proxy_config
            )
            
            # Use full session state if exists, otherwise try cookies
            iphone_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            
            context_args = {
                "viewport": {'width': 1280, 'height': 800},
                "user_agent": iphone_ua,
                "locale": "en-US",
                "timezone_id": "Europe/London",
                "permissions": ["geolocation"],
            }
            
            if os.path.exists(session_state_path):
                logging.info(f"🎬 TIKTOK: Loading existing full session...")
                context_args["storage_state"] = session_state_path
            
            context = await browser.new_context(**context_args)
            
            # --- STEALTH SCRIPTS ---
            # Mask Playwright/Automation traces
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            """)

            if not os.path.exists(session_state_path) and os.path.exists(cookie_path) and cookie_path.endswith('.txt'):
                logging.info("🎬 TIKTOK: Injecting legacy TXT cookies...")
                try:
                    with open(cookie_path, 'r', encoding='utf-8') as f:
                        cookies = []
                        for line in f:
                            if not line.strip() or line.startswith('#'): continue
                            parts = line.split('\t')
                            if len(parts) >= 7:
                                domain = parts[0].strip()
                                cookies.append({
                                    'name': parts[5].strip(),
                                    'value': parts[6].strip(),
                                    'domain': f".{domain}" if not domain.startswith('.') else domain,
                                    'path': parts[2].strip(),
                                    'secure': parts[3].strip().upper() == 'TRUE',
                                    'expires': int(parts[4]) if parts[4].strip().isdigit() and int(parts[4]) > 0 else -1,
                                    'sameSite': 'Lax'
                                })
                        await context.add_cookies(cookies)
                except Exception as e:
                    logging.warning(f"⚠️ Cookie injection failed: {e}")

            page = await context.new_page()
            
            try:
                # Navigate to upload
                logging.info("🎬 TIKTOK: Navigating to Upload page...")
                await page.goto("https://www.tiktok.com/creator-center/upload?lang=en", wait_until="domcontentloaded", timeout=90000)
                await asyncio.sleep(5)

                # --- SESSION HARVESTING LOGIC ---
                if "login" in page.url or "sign-in" in page.url:
                    logging.warning("🚨 TIKTOK: Auth failed or Session expired.")
                    if not headless:
                        logging.info("👆 PLEASE LOGIN MANUALLY NOW. The bot is waiting for you...")
                        print("\n" + "!"*60)
                        print("!!! ОБНАРУЖЕНА СТРАНИЦА ЛОГИНА !!!")
                        print("Пожалуйста, войдите в свой аккаунт TikTok прямо в открытом окне браузера.")
                        print("Как только вы попадете на страницу загрузки, бот продолжит сам.")
                        print("!"*60 + "\n")
                        
                        # Wait for user to reach upload page
                        for _ in range(120): # Wait up to 2 mins
                            if "upload" in page.url and "login" not in page.url:
                                logging.info("✨ SUCCESS! Login detected. Harvesting session...")
                                await asyncio.sleep(5)
                                # Save state for future use
                                await context.storage_state(path=session_state_path)
                                logging.info(f"💾 SESSION SAVED to {session_state_path}. Next time it will be automatic.")
                                break
                            await asyncio.sleep(1)
                        else:
                            return "ERROR: Manual login timeout"
                    else:
                        return "ERROR: Landed on login page in headless mode"

                logging.info("🎬 TIKTOK: Selecting video file...")
                file_input = page.locator('input[type="file"]').first
                await file_input.wait_for(state="attached", timeout=30000)
                await file_input.set_input_files(video_path)
                
                logging.info("🎬 TIKTOK: Uploading (wait 15s)...")
                await asyncio.sleep(15)

                # --- POPUP CLEANER (Copyright check & Tutorials) ---
                logging.info("🎬 TIKTOK: Cleaning popups (Copyright/Tutorials)...")
                try:
                    # 1. Click 'Увімкнути' / 'Turn on' / 'Allow' for copyright check
                    selectors = [
                        'button:has-text("Увімкнути")', 
                        'button:has-text("Turn on")',
                        'button:has-text("Allow")',
                        'button:has-text("Got it")',
                        'button:has-text("Зрозуміло")'
                    ]
                    for selector in selectors:
                        btns = page.locator(selector)
                        if await btns.count() > 0:
                            logging.info(f"✨ TIKTOK: Dismissing popup via: {selector}")
                            await btns.first.click()
                            await asyncio.sleep(2)
                    
                    # 2. Catch-all for tutorial close buttons (usually small X or specific overlay classes)
                    try:
                        close_btns = page.locator('div[class*="guide"] [class*="close"], div[class*="tooltip"] [class*="close"]').first
                        if await close_btns.is_visible():
                            await close_btns.click()
                            logging.info("✨ TIKTOK: Closed tutorial guide.")
                    except: pass

                except Exception as clean_err:
                    logging.warning(f"⚠️ Popup cleaner encountered an issue: {clean_err}")

                # 3. CAPTION
                try:
                    caption_box = page.locator('.notranslate[contenteditable="true"]').first
                    await caption_box.wait_for(state="visible", timeout=30000)
                    await caption_box.click()
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Backspace")
                    await page.keyboard.type(caption, delay=50)
                    await asyncio.sleep(2)
                except:
                    logging.warning("⚠️ Could not set caption automagically.")

                logging.info("🎬 TIKTOK: Finalizing Post...")
                # Scroll multiple times to ensure visibility
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(3)
                
                post_btn_selectors = [
                     'button:has-text("Post")', 
                     'button:has-text("Publish")', 
                     'button:has-text("Опублікувати")',
                     '.btn-post',
                     'button[data-e2e="post_video_button"]'
                ]
                
                post_btn = None
                for sel in post_btn_selectors:
                    btn = page.locator(sel).last
                    if await btn.count() > 0 and await btn.is_visible():
                        post_btn = btn
                        break
                
                if not post_btn:
                    logging.error("❌ TIKTOK: Post button NOT FOUND.")
                    await page.screenshot(path="data/tiktok_error_post_not_found.png")
                    return "ERROR: Post button not found."

                # WAIT UNTIL ENABLED (Processing check)
                logging.info("🎬 TIKTOK: Waiting for button to be enabled (upload/copyright check)...")
                for _ in range(20): # Wait up to 40s
                    if await post_btn.is_enabled():
                        break
                    await asyncio.sleep(2)
                
                await post_btn.click()

                if not headless:
                    logging.info("👀 Post will be clicked in 5s. Watch the screen.")
                    await asyncio.sleep(5)

                await post_btn.click()
                
                # --- FINAL CONFIRMATION MODAL ---
                logging.info("🎬 TIKTOK: Checking for final confirmation modal...")
                await asyncio.sleep(3)
                
                final_confirm_selectors = [
                     'button:has-text("Опублікувати")',
                     'button:has-text("Post now")',
                     'button:has-text("Publish anyway")',
                     'button:has-text("Continue publishing")'
                ]
                
                for selector in final_confirm_selectors:
                    final_btns = page.locator(selector)
                    if await final_btns.count() > 0:
                        logging.info(f"✨ TIKTOK: Clicking final confirmation: {selector}")
                        await final_btns.last.click()
                        await asyncio.sleep(5)
                        break

                logging.info("✅ SUCCESS! Video is live.")
                await asyncio.sleep(7)
                
                # Final session save (to keep it fresh)
                await context.storage_state(path=session_state_path)
                return "SUCCESS"

            except Exception as e:
                logging.error(f"❌ TIKTOK STEALTH ERROR: {e}")
                return f"ERROR: {e}"
        finally:
            if browser:
                await browser.close()
