import logging
import os
import asyncio
import random
import json
from playwright.async_api import async_playwright

async def human_type(page, text):
    for char in text:
        await page.keyboard.type(char, delay=random.randint(50, 150))

class HedraAutomation:
    """
    Automates Hedra Talking Head generation via browser.
    FOCUSED VERSION: Only deals with the prompt input.
    """
    def __init__(self):
        self.url = "https://www.hedra.com/app/home"
        self.output_dir = os.path.abspath("data/outputs")
        os.makedirs(self.output_dir, exist_ok=True)

    async def generate_video(self, image_path, audio_path, email, password, cookies_file=None):
        async with async_playwright() as p:
            try:
                logging.info(f"🎭 HEDRA: Connecting to Chrome...")
                browser = await p.chromium.connect_over_cdp("http://localhost:9222")
                context = browser.contexts[0]
                
                # --- LOAD COOKIES IF AVAILABLE ---
                if cookies_file and os.path.exists(cookies_file):
                    logging.info(f"🍪 Loading session cookies from {cookies_file}...")
                    try:
                        with open(cookies_file, 'r') as f:
                            cookies = json.load(f)
                        await context.add_cookies(cookies)
                    except Exception as e:
                        logging.warning(f"⚠️ Failed to load cookies: {e}")

                page = await context.new_page()
                
                # 1. Clear state: Go to home
                logging.info(f"🎭 HEDRA: Opening Home...")
                await page.goto(self.url, wait_until="domcontentloaded")
                await asyncio.sleep(10)

                # 2. Login check - Skip if cookies worked (Home page should be visible)
                current_url = page.url
                if "login" in current_url or "sign-in" in current_url:
                    logging.info("🎭 HEDRA: Session not active. Performing login...")
                    await page.locator("input[type='email']").first.fill(email)
                    await page.locator("button:has-text('Continue'), button[type='submit']").first.click()
                    await asyncio.sleep(2)
                    await page.locator("input[type='password']").first.fill(password)
                    await page.locator("button:has-text('Continue'), button[type='submit']").first.click()
                    await asyncio.sleep(12)
                else:
                    logging.info("✅ HEDRA: Session active via cookies!")

                # 3. THE PROMPT CHALLENGE
                logging.info("🎭 HEDRA: Starting Prompt discovery...")
                
                # We'll try to find the container first, then the textarea/div inside it
                # The container often has "Describe your idea" as text or placeholder
                
                # Attempt 1: Get by placeholder text directly (Playwright built-in)
                try:
                    field = page.get_by_placeholder("Describe your idea", exact=False).first
                    if await field.is_visible():
                        logging.info("✨ HEDRA: Found prompt via get_by_placeholder!")
                        await field.click()
                        await asyncio.sleep(1)
                        await human_type(page, "Create a talking video from my character")
                        await asyncio.sleep(1)
                        
                        arrow_btn = page.locator("button:has(svg path[d*='M12 19V5']), button:has(svg path[d*='M5 12h14']), .up-arrow-button").first
                        await arrow_btn.click()
                        logging.info("🚀 HEDRA: Prompt submitted!")
                        await asyncio.sleep(10)
                        return "STAGE_PROMPT_DONE"
                except: pass

                # Attempt 2: BROAD SEARCH
                logging.info("🔍 HEDRA: Placeholder failed, trying broad search...")
                all_inputs = await page.locator("textarea, div[contenteditable='true'], [role='textbox']").all()
                for inp in all_inputs:
                    text = await inp.get_attribute("placeholder") or await inp.inner_text()
                    if text and ("Describe" in text or "idea" in text):
                        logging.info("✨ HEDRA: Found via broad search!")
                        await inp.click()
                        await human_type(page, "Create a talking video")
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(10)
                        return "STAGE_PROMPT_DONE"

                # Attempt 3: JS Direct Focus (force focus on anything that looks like an input)
                logging.info("💣 HEDRA: Resorting to JS Force-Focus...")
                await page.evaluate("""() => {
                    const el = Array.from(document.querySelectorAll('textarea, div[contenteditable="true"]'))
                                    .find(e => e.innerText.includes('Describe') || e.placeholder?.includes('Describe'));
                    if (el) { el.focus(); el.click(); }
                }""")
                await asyncio.sleep(1)
                await page.keyboard.type("Create a talking video", delay=100)
                await page.keyboard.press("Enter")
                
                logging.info("🏁 HEDRA: Prompt stage finished. Check browser to see result.")
                await asyncio.sleep(5)
                return "STAGE_PROMPT_DONE"

            except Exception as e:
                logging.error(f"❌ HEDRA FATAL: {e}")
                return None

hedra_automation = HedraAutomation()
