import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.features.media_core.script_writer import script_writer
from src.shared.providers.audio_provider import audio_provider
from src.shared.providers.pexels_provider import pexels_provider
from src.shared.providers.video_generator import video_generator
from src.shared.providers.video_editor import video_editor
from src.shared.providers.social_publisher import social_publisher

async def force_test_push():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logging.info("🚀 FORCE PUSH: Initiating manual viral marketing cycle...")
    
    from src.app.config import config
    logging.info(f"DEBUG: YOUTUBE_CLIENT_ID={config.YOUTUBE_CLIENT_ID[:10]}...")
    logging.info(f"DEBUG: YOUTUBE_REFRESH_TOKEN={config.YOUTUBE_REFRESH_TOKEN[:10]}...")
    win_data = {
        "id": "manual_test_999",
        "symbol": "BTC/USDT",
        "pnl": 12543.20, # Estimated PnL
        "roi": 35.32,
        "exchange": "OKX",
        "timestamp": "2026-01-14T22:56:00"
    }

    logging.info(f"🔥 Step 1: Generating Script for {win_data['symbol']} (+{win_data['roi']}%)")
    try:
        script = script_writer.generate_viral_script(win_data)
    except Exception as e:
        logging.warning(f"Gemini failed, using fallback script: {e}")
        script = f"A.S.T.R.A. just hit it big! {win_data['roi']}% profit on {win_data['symbol']}. The future of trading is here. Check out induktr.com for the full setup!"
    
    print(f"\n--- SCRIPT ---\n{script}\n--------------\n")

    logging.info("🎙️ Step 2: Generating FREE AI Voice-over...")
    audio_path = await audio_provider.generate_speech(script, "force_test_audio")
    
    logging.info("📹 Step 3: Fetching Background from Pexels...")
    bg_video_path = pexels_provider.get_random_background(query="crypto trading city")
    
    logging.info("🖼️ Step 4: Creating PnL Overlay Card...")
    overlay_path = video_generator.generate_marketing_media(win_data, script)
    
    logging.info("🎞️ Step 5: Assembling Final Video (MoviePy)...")
    final_video = video_editor.assemble_final_video(
        bg_video_path, audio_path, overlay_path, "force_test"
    )

    if final_video:
        logging.info(f"✅ Step 6: Final Video Ready at {final_video}")
        logging.info("📺 Step 7: Publishing to YouTube Shorts...")
        
        title = f"A.S.T.R.A. AI BREAKOUT: +{win_data['roi']}% on {win_data['symbol']}! #shorts"
        description = f"The A.S.T.R.A. Trading System just hit a massive target.\n\n{script}\n\n#trading #ai #crypto #shorts #induktr"
        
        results = await social_publisher.publish_everywhere(final_video, title, description)
        
        logging.info(f"✨ MISSION COMPLETE: {results}")
    else:
        logging.error("❌ Assembly failed. Check assets.")

if __name__ == "__main__":
    asyncio.run(force_test_push())
