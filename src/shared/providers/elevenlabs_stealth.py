
import logging
import os
import asyncio
import json
import time
import re
from playwright.async_api import async_playwright

class ElevenLabsStealth:
    def __init__(self):
        self.url = "https://elevenlabs.io/app/speech-synthesis/text-to-speech"
        self.cookies_path = None
        self.cookie_format = None
        
        # Priority 1: JSON Cookies
        json_p = os.path.join(os.getcwd(), "data", "elevenlabs_cookies.json")
        if os.path.exists(json_p):
            self.cookies_path = json_p
            self.cookie_format = "JSON"
        else:
            # Priority 2: Netscape TXT
            for f in ["elevenlabs.io_cookies.txt", "elevenlabs_cookies.txt"]:
                p = os.path.join(os.getcwd(), "data", f)
                if os.path.exists(p):
                    self.cookies_path = p
                    self.cookie_format = "TXT"
                    break
        
        self.output_dir = os.path.abspath("src/data/media_assets")
        os.makedirs(self.output_dir, exist_ok=True)

    def _parse_netscape_cookies(self, file_path):
        cookies = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip() or line.startswith('#'): continue
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        domain = parts[0].strip()
                        cookie = {
                            'name': parts[5].strip(),
                            'value': parts[6].strip(),
                            'domain': domain,
                            'path': parts[2].strip(),
                            'secure': parts[3].strip().upper() == 'TRUE',
                            'expires': int(parts[4]) if parts[4].strip().isdigit() and int(parts[4]) > 0 else int(time.time() + 3600*24),
                            'sameSite': 'Lax'
                        }
                        if cookie['secure']: cookie['sameSite'] = 'None'
                        cookies.append(cookie)
            return cookies
        except Exception as e:
            logging.error(f"🎙️ ELEVENLABS COOKIE ERROR: {e}")
            return []

    async def generate_speech_stealth(self, text, filename, voice_name="Popular Trader"):
        async with async_playwright() as p:
            browser = None
            context = None
            is_cdp = False
            
            # --- CONNECTION STRATEGY ---
            try:
                logging.info("🎙️ ELEVENLABS: Trying to connect to existing Chrome (9222)...")
                browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
                context = browser.contexts[0]
                is_cdp = True
                logging.info("✅ ELEVENLABS: Connected to active session!")
            except:
                logging.info("🎙️ ELEVENLABS: No active Chrome. Launching isolated...")
                browser = await p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
                context = await browser.new_context(viewport={'width': 1280, 'height': 800})

            # --- FORCED COOKIE SYNC ---
            if self.cookies_path:
                logging.info(f"🎙️ ELEVENLABS: Syncing {self.cookie_format} session keys...")
                try:
                    cookies_to_add = []
                    if self.cookie_format == "JSON":
                        with open(self.cookies_path, 'r') as f: cookies_to_add = json.load(f)
                    else:
                        cookies_to_add = self._parse_netscape_cookies(self.cookies_path)
                    
                    if cookies_to_add:
                        await context.add_cookies(cookies_to_add)
                except Exception as e:
                    logging.warning(f"⚠️ Cookie sync failed: {e}")

            # Find existing page or create new
            page = None
            for p_obj in context.pages:
                if "elevenlabs.io" in p_obj.url:
                    page = p_obj
                    logging.info("✨ ELEVENLABS: Found existing tab. Using it!")
                    break
            
            if not page:
                page = await context.new_page()

            try:
                logging.info("🎙️ ELEVENLABS: Loading site...")
                await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(6) # Wait for redirects/checks
                
                # Check 
                if "sign-in" in page.url or "login" in page.url:
                    logging.warning("🚨 ELEVENLABS: Still on Login page. Trying one hard refresh...")
                    await page.reload()
                    await asyncio.sleep(5)
                    if "sign-in" in page.url or "login" in page.url:
                        logging.error("❌ ELEVENLABS AUTH FAILED. Please login manually in the window.")
                        await asyncio.sleep(30) # Let user see
                        return None

                # Production
                logging.info(f"🎙️ ELEVENLABS: Selecting voice '{voice_name}'...")
                picker = page.locator("[data-testid='voice-picker-button'], button:has-text('Voice')").first
                await picker.wait_for(state="visible", timeout=15000)
                await picker.click()
                await page.locator("input[placeholder*='Search']").first.fill(voice_name)
                await asyncio.sleep(2)
                
                # Dynamic voice click
                voice_opt = page.locator(f"div[role='option']:has-text('{voice_name}'), button:has-text('{voice_name}')").first
                await voice_opt.click(force=True)
                
                logging.info("🎙️ ELEVENLABS: Filling text...")
                area = page.locator("textarea, [contenteditable='true']").first
                await area.focus()
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await area.fill(text)
                await asyncio.sleep(1)
                
                logging.info("🎙️ ELEVENLABS: Clicking Generate...")
                await page.locator("button:has-text('Generate')").first.click()
                
                # Wait & Download
                final_path = os.path.join(self.output_dir, f"{filename}.mp3")
                logging.info("⏳ ELEVENLABS: Waiting for MP3...")
                
                async with page.expect_download(timeout=90000) as download_info:
                    await asyncio.sleep(15) # Processing time
                    try:
                        # Try to click download from History
                        history = page.locator("button:has-text('History')").first
                        await history.click()
                        await asyncio.sleep(2)
                        await page.locator("button[aria-label='Download']").first.click()
                    except:
                        # Main area download
                        await page.locator("button[aria-label='Download']").first.click()
                
                download = await download_info.value
                await download.save_as(final_path)
                logging.info(f"✅ ELEVENLABS: Saved to {final_path}")
                return final_path

            except Exception as e:
                logging.error(f"❌ ELEVENLABS ERROR: {e}")
                return None
            finally:
                if not is_cdp: await browser.close()

elevenlabs_stealth = ElevenLabsStealth()
