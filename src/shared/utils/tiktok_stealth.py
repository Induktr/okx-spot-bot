import logging
import os
import asyncio
import time
import subprocess
import random
from DrissionPage import ChromiumPage, ChromiumOptions

def run_stealth_upload_sync(video_path, caption, cookie_path, headless=False, proxy=None, skip_warmup=False):
    """
    TIKTOK GHOST PROTOCOL v1.5 (PROD)
    Advanced Human-Mimetic Automation for TikTok Studio.
    """
    logging.info("🎬 GHOST: Initializing stealth session...")
    
    user_data_dir = os.path.abspath("src/shared/data/sessions/profile_induktr_astra")
    
    # 1. CLEANUP PREVIOUS SESSIONS
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe', '/T'], capture_output=True)
            time.sleep(2)
    except: pass

    # 2. BROWSER ENGINE CONFIG
    co = ChromiumOptions()
    co.set_user_data_path(user_data_dir)
    if proxy: co.set_argument(f'--proxy-server={proxy}')
    if headless: co.headless(True)
    co.set_argument('--disable-gpu')
    co.set_argument('--start-maximized')
    co.set_argument('--disable-blink-features=AutomationControlled')

    page = None
    try:
        logging.info("🚀 GHOST: Spawning browser agent...")
        page = ChromiumPage(co)
        
        def human_delay(min_s=1, max_s=3):
            time.sleep(random.uniform(min_s, max_s))

        def kill_popups():
            targets = ['Увімкнути', 'Ввімкнути', 'Зрозуміло', 'Got it', 'Allow', 'Close', 'Закрити']
            for t in targets:
                try:
                    btn = page.ele(f'@@tag:button@@text():{t}', timeout=0.2) or \
                          page.ele(f'xpath://button[contains(., "{t}")]', timeout=0.1)
                    if btn and btn.states.is_displayed:
                        logging.info(f"✨ GHOST: Dismissing popup ({t})")
                        btn.click(by_js=True)
                        time.sleep(1)
                except: pass

        # --- ACCESS ---
        page.get("https://www.tiktok.com/tiktokstudio/upload?lang=en")
        human_delay(10, 15)

        # --- UPLOAD ---
        logging.info("📤 GHOST: Injecting video file...")
        file_input = page.ele('tag:input@type=file')
        if not file_input: return "ERROR: Upload field missing"
        file_input.input(os.path.abspath(video_path))
        time.sleep(15)

        # --- CAPTION ENGINE ---
        logging.info("🖋️ GHOST: Crafting caption with human rhythm...")
        page.scroll.to_top()
        time.sleep(2)
        caption_box = page.ele('xpath://div[@contenteditable="true"]') or \
                      page.ele('.notranslate[contenteditable="true"]')
        
        if caption_box:
            caption_box.click()
            human_delay(1.5, 2.5)
            # Purge technical filename
            page.actions.key_down('CONTROL').type('a').key_up('CONTROL')
            time.sleep(0.5)
            page.actions.key_down('BACKSPACE').key_up('BACKSPACE')
            human_delay(1, 2)
            
            for i, char in enumerate(caption):
                caption_box.input(char)
                if i > 0 and i % random.randint(25, 35) == 0:
                    time.sleep(random.uniform(1.5, 3.0)) # Reflective pause
                else:
                    time.sleep(random.uniform(0.05, 0.15))
            logging.info("✅ GHOST: Caption entry successfully simulated.")
        
        time.sleep(25) # Give server time to breathe
        kill_popups()

        # --- DEEP DOM SCROLL (PROVEN TECH) ---
        logging.info("🖱️ GHOST: Descending through DOM layers...")
        deep_scroll_js = """
        (function() {
            const step = 300;
            const elements = document.querySelectorAll('*');
            for (const el of elements) {
                const style = window.getComputedStyle(el);
                if (el.scrollHeight > el.clientHeight && 
                    (style.overflowY === 'auto' || style.overflowY === 'scroll' || el.tagName === 'MAIN')) {
                    el.scrollBy({ top: step, behavior: 'smooth' });
                }
            }
        })();
        """
        for i in range(5):
            page.run_js(deep_scroll_js)
            time.sleep(random.uniform(1.2, 2.0))
            kill_popups()
            # Immediate stop if button visual
            btn = page.ele('xpath://button[@data-e2e="post-button"]', timeout=0.1)
            if btn: break

        # --- EXECUTION: DOUBLE CONFIRMATION ---
        logging.info("✅ GHOST: Executing publish sequence...")
        
        post_btn = page.ele('xpath://button[@data-e2e="post-button"]') or \
                   page.ele('xpath://button[contains(., "Опублікувати")]') or \
                   page.ele('xpath://button[contains(., "Post")]')

        if post_btn:
            try: post_btn.scroll.to_see()
            except: pass
            time.sleep(2)
            
            # Final verification of active state
            for attempt in range(15):
                kill_popups()
                if 'disabled' not in post_btn.attrs:
                    logging.info("🚀 GHOST: Weapon system active. Posting...")
                    break
                time.sleep(4)
            
            human_delay(3, 6) # Final "Human" hesitation
            post_btn.click(by_js=True)
            
            # Modal Confirmation Handler
            time.sleep(5)
            for _ in range(5):
                confirm = page.ele('xpath://div[contains(@class, "modal")]//button[contains(., "Post")]') or \
                          page.ele('xpath://div[contains(@class, "modal")]//button[contains(., "Опублікувати")]')
                if confirm and confirm.states.is_displayed:
                    logging.info("🚀 GHOST: Confirming secondary modal...")
                    confirm.click(by_js=True)
                    time.sleep(10)
                    return "SUCCESS"
                time.sleep(2)
            
            return "SUCCESS"
        else:
            return "ERROR: Final targeting failed."

    except Exception as e:
        logging.error(f"❌ GHOST CRITICAL: {e}")
        return f"ERROR: {e}"
    finally:
        if page:
            try: page.quit()
            except: pass

async def tiktok_stealth_upload(video_path, caption, cookie_path, headless=False, proxy=None, skip_warmup=False):
    return await asyncio.to_thread(run_stealth_upload_sync, video_path, caption, cookie_path, headless, proxy, skip_warmup)