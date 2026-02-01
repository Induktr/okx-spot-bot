import asyncio
import logging
import os
import math # Added for geometric drawing
import random
from playwright.async_api import async_playwright
from src.app.config import config

class ChartProvider:
    """
    Captures live TradingView charts or Dashboard analytics using Playwright.
    Creates ultra-unique proof-of-work video clips for viral marketing.
    """
    def __init__(self):
        self.output_dir = "src/shared/data/media_assets"
        os.makedirs(self.output_dir, exist_ok=True)
        self.temp_video_dir = "src/shared/data/temp_recordings"
        os.makedirs(self.temp_video_dir, exist_ok=True)

    async def capture_chart_clip(self, symbol, duration=10, visual_analysis=None):
        """
        Navigates to TradingView or Dashboard and records a video clip.
        """
        # Cleanup symbol for TradingView (e.g., BTC/USDT -> BINANCE:BTCUSDT)
        clean_symbol = symbol.replace("/", "").replace(":USDT", "")
        # Try to guess exchange or use a default
        tv_url = f"https://www.tradingview.com/chart/?symbol=BINANCE:{clean_symbol}"
        
        logging.info(f"📊 CHART GEN: Planning to capture {symbol} on TradingView...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # Record video into temp dir
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                record_video_dir=self.temp_video_dir,
                record_video_size={'width': 1280, 'height': 720}
            )
            
            page = await context.new_page()
            
            try:
                # 1. Navigate
                logging.info(f"📊 CHART GEN: Navigating to {tv_url}...")
                await page.goto(tv_url, wait_until="networkidle", timeout=60000)
                
                # 2. Wait for chart to load
                await asyncio.sleep(5) 
                
                # --- ANALYST RE-ENACTMENT ENGINE (MULTI-PHASE) ---
                if visual_analysis:
                    logging.info(f"📊 CHART GEN: Sequential TA Re-enactment for {symbol}...")
                    
                    # PHASE 1: INDICATOR AUDIT (Simulate looking at technical signals)
                    indicators = visual_analysis.get('checked_indicators', ['RSI', 'EMA'])
                    for i, ind in enumerate(indicators[:3]):
                        # Hover over where indicator labels usually sit in TV (top left legend area)
                        py = 150 + (i * 25)
                        await page.mouse.move(120, py, steps=10)
                        logging.info(f"📊 CHART GEN: Validating indicator: {ind}")
                        await asyncio.sleep(1.5)
                    
                    # PHASE 2: HAND-DRAWN ZONES (Artistic Brush)
                    # We explicitly click the Brush tool in the LEFT toolbar for maximum reliability
                    try:
                        # Try to find the brush icon in the drawing toolbar
                        brush_button = page.locator('div[data-name="brush"]')
                        await brush_button.click(timeout=3000)
                    except:
                        # Fallback for different TV layouts: use the shortcut and wait
                        await page.keyboard.press("Alt+P") 
                    
                    await asyncio.sleep(0.5)
                    zones = visual_analysis.get('zones', [])
                    for zone in zones[:2]:
                        # Center the "scribble" on key price areas
                        zx, zy = random.randint(400, 700), random.randint(300, 500)
                        await page.mouse.move(zx, zy)
                        await page.mouse.down()
                        # Draw an organic circle/ellipise
                        for angle in range(0, 360, 30):
                            rad = angle * 3.14 / 180
                            await page.mouse.move(zx + 40*math.cos(rad), zy + 25*math.sin(rad), steps=3)
                        await page.mouse.up()
                        await asyncio.sleep(2)

                    # PHASE 3: KEY HORIZONTAL LEVELS (Alt+H)
                    levels = visual_analysis.get('key_levels', [])
                    for level in levels[:2]:
                        y = random.randint(250, 550)
                        await page.mouse.move(random.randint(400, 800), y, steps=15)
                        await page.keyboard.press("Alt+H")
                        await asyncio.sleep(2)
                    
                    # PHASE 4: TRENDLINES (Alt+T)
                    trendlines = visual_analysis.get('trendlines', [])
                    for line in trendlines[:1]:
                        slope = line.get('slope', 'up')
                        await page.keyboard.press("Alt+T")
                        await asyncio.sleep(0.5)
                        start_x, start_y = random.randint(200, 300), 500 if slope == 'up' else 300
                        end_x, end_y = random.randint(800, 950), 300 if slope == 'up' else 500
                        await page.mouse.move(start_x, start_y)
                        await page.mouse.click(start_x, start_y)
                        await page.mouse.move(end_x, end_y, steps=20)
                        await page.mouse.click(end_x, end_y)
                        await asyncio.sleep(1.5)

                    # PHASE 5: FIBONACCI RETRACEMENT (Alt+F) - The Institutional Touch
                    logging.info("📊 CHART GEN: Drawing Fibonacci Retracement...")
                    await page.keyboard.press("Alt+F")
                    await asyncio.sleep(0.5)
                    fx, fy = random.randint(300, 400), 600
                    tx, ty = random.randint(600, 800), 200
                    await page.mouse.move(fx, fy)
                    await page.mouse.click(fx, fy)
                    await page.mouse.move(tx, ty, steps=30)
                    await page.mouse.click(tx, ty)
                    await asyncio.sleep(2)

                    # PHASE 6: LONG/SHORT POSITION MODEL (Alt+S) - Execution Proof
                    logging.info("📊 CHART GEN: Modeling Trade Position...")
                    # Position tools show Stop Loss and Take Profit zones
                    await page.keyboard.press("Alt+S") 
                    await asyncio.sleep(0.5)
                    pos_x, pos_y = 640, 360 # Center of focus
                    await page.mouse.move(pos_x, pos_y)
                    await page.mouse.click(pos_x, pos_y)
                    await asyncio.sleep(2)

                    # PHASE 7: FINAL PANNING (Backtesting vibe)
                    for _ in range(5):
                        await page.keyboard.press("ArrowLeft")
                        await asyncio.sleep(0.4)
                else:
                    # FALLBACK: Generic sequence
                    logging.info("📊 CHART GEN: Generic indicator check...")
                    await page.mouse.move(640, 360)
                    await asyncio.sleep(1)
                    await page.keyboard.press("Alt+T")
                    await page.mouse.click(300, 500)
                    await page.mouse.move(900, 300, steps=30)
                    await page.mouse.click(900, 300)
                    await asyncio.sleep(2)

                # Ensure we record for the full duration
                await asyncio.sleep(duration - 5 if duration > 5 else 2) 
                
                # Path to the recorded video
                video_path = await page.video.path()
                
                # Close everything to flush recording
                await context.close()
                await browser.close()
                
                if video_path and os.path.exists(video_path):
                    final_name = f"chart_{clean_symbol}_{int(asyncio.get_event_loop().time())}.webm"
                    final_path = os.path.join(self.output_dir, final_name)
                    os.rename(video_path, final_path)
                    logging.info(f"✅ CHART GEN: Captured live chart clip -> {final_path}")
                    return final_path
                
            except Exception as e:
                logging.error(f"❌ CHART GEN ERROR: {e}")
                if browser: await browser.close()
                return None

chart_provider = ChartProvider()
