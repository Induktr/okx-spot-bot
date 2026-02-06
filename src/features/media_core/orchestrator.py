import logging
import asyncio
import os
from src.features.media_core.profit_scout import profit_scout
from src.features.media_core.script_writer import script_writer
from src.shared.providers.audio_provider import audio_provider
from src.shared.providers.audio_provider import audio_provider
from src.shared.providers.video_generator import video_generator
from src.shared.providers.video_editor import video_editor
from src.shared.providers.social_publisher import social_publisher
from src.shared.providers.chart_provider import chart_provider

class MediaCoreOrchestrator:
    """
    Orchestrates the viral media creation pipeline using FREE tools.
    Finds wins -> Writes scripts -> Generates free audio -> Finds free background -> ASSEMBLES -> PUBLISHES.
    """
    async def process_new_wins(self):
        logging.info("📢 MEDIA CORE: Scanning for viral-worthy trades...")
        wins = await profit_scout.find_big_wins()
        
        if not wins:
            logging.info("📢 MEDIA CORE: No new major wins found.")
            return

        for win in wins[:3]:
            logging.info(f"🔥 MEDIA CORE: Processing viral content for {win['symbol']}...")
            
            # ROI > 50% -> FULL VIDEO (All Platforms)
            if win['roi'] >= 50.0:
                await self._handle_video_marketing(win)
            # ROI 15-50% -> IMAGE + AI TEXT (Telegram Only)
            elif win['roi'] >= 15.0:
                await self._handle_text_marketing(win)

    async def _handle_video_marketing(self, win):
        """Processes full video pipeline with Trend Scouting."""
        # 1. SCOUT: Find what's viral right now
        from src.features.media_core.trend_scout import trend_scout
        active_trends = await trend_scout.find_top_trends()
        
        # 2. DIRECTOR: AI picks the best trend and writes a script + style directive
        director_cut = script_writer.select_trend_and_write_script(win, active_trends)
        
        script = director_cut.get('script', '')
        style = director_cut.get('visual_style', 'DEFAULT')
        format_type = director_cut.get('format_type', 'DEFAULT')
        trend_name = director_cut.get('name', 'Trading')
        
        logging.info(f"🎬 DIRECTOR: Selected Trend '{trend_name}' with style '{style}' and format '{format_type}'")

        # 3. PRODUCTION: Generate assets based on directive
        audio_path = await audio_provider.generate_speech(script, f"audio_{win['id']}")
        
        # New: Download trending background music automatically
        from src.shared.providers.audio_downloader import audio_downloader
        song_query = director_cut.get('trending_song', 'trending phonk')
        bg_music_path = audio_downloader.download_trending_track(song_query)
        
        # Smart Background Search (High-Retention TikTok Aesthetics)
        # We prioritize "Old Money", "Tech", and "Luxury" vibes which are safe and viral.
        search_query = "luxury city night" # Default safe option
        
        if "Glitch" in trend_name: 
            search_query = "digital data abstract"
        elif "Luxury" in trend_name or "Money" in trend_name: 
            search_query = "luxury lifestyle money"
        elif "Minimal" in trend_name: 
            search_query = "calm ocean waves vertical"
        elif "Motivation" in trend_name:
            search_query = "gym workout vertical"
        else:
            # Randomize acceptable high-quality backgrounds to avoid repetition
            import random
            safe_hashtags = ["skyscraper night", "modern office view", "bitcoin visualization", "luxury car driving night", "cinematic technology"]
            search_query = random.choice(safe_hashtags)
            
        # --- REAL-TIME DATA CAPTURE (PROOF OF WORK) ---
        # We record long enough to cover the entire voiceover
        # Using a safe 45s default ensures we have more than enough footage for even long scripts
        chart_clip = await chart_provider.capture_chart_clip(
            win['symbol'], 
            duration=45,
            visual_analysis=win.get('visual_analysis')
        )
        
        # Logic: If we have a chart clip, we ALWAYS use it as primary centered content.
        if chart_clip:
            bg_video_path = chart_clip
            logging.info("📈 MEDIA CORE: Using real-time TradingView capture as primary centered content.")
        # --- CONTENT STRATEGY: PURE PROOF-OF-WORK ---
        # We disable split-screen and secondary filler content (Pexels) entirely.
        # The chart is now the absolute and only focus.
        format_type = "CENTERED_CHART"
        secondary_video_path = None
        bg_video_path = chart_clip
        
        if not bg_video_path:
            logging.warning("⚠️ No chart clip captured, using premium fallback.")
            # Fallback to a static high-end AI background if chart fails
            bg_video_path = "src/shared/data/media_assets/ai_premium_bg.png"
        
        # Generate Dynamic Overlay (Style Match)
        overlay_path = video_generator.generate_marketing_media(
            win, 
            style_directive=style,
            heading=director_cut.get('card_heading'),
            status=director_cut.get('card_status')
        )
        
        # --- ENVIRONMENT BACKGROUND GENERATION (AI FRESHNESS) ---
        from src.shared.providers.ai_image_provider import ai_image_provider
        env_bg_path = ai_image_provider.generate_background(theme_query=search_query)
        
        if not env_bg_path:
            logging.warning("⚠️ AI Image Gen failed, falling back to local library.")
            ai_libs_dir = "src/shared/data/media_assets/ai_bgs"
            if os.path.exists(ai_libs_dir):
                import random as rnd
                bgs = [os.path.join(ai_libs_dir, f) for f in os.listdir(ai_libs_dir) if f.endswith('.png')]
                env_bg_path = rnd.choice(bgs) if bgs else "src/shared/data/media_assets/ai_premium_bg.png"
            else:
                env_bg_path = "src/shared/data/media_assets/ai_premium_bg.png"
            
        # Pexels is disabled. Fallback is handled by the AI libs dir logic above.

        # 4. ASSEMBLY
        try:
            final_video = video_editor.assemble_final_video(
                 primary_content_path=bg_video_path, 
                 audio_path=audio_path, 
                 overlay_path=overlay_path, 
                 win_id=win['id'], 
                 style=style, 
                 bg_music_path=bg_music_path, 
                 format_type=format_type,
                 secondary_video_path=secondary_video_path,
                 script_text=script,
                 env_bg_path=env_bg_path
            )
        except Exception as assembly_err:
            logging.error(f"❌ ASSEMBLY ERROR for {win['symbol']}: {assembly_err}")
            return
        
        if final_video:
            try:
                # --- AI-DRIVEN VIRAL METADATA ---
                viral_title = director_cut.get('viral_title', f"A.S.T.R.A. Profit: {win['roi']}%")
                ai_desc = director_cut.get('video_description', '')
                hashtags = director_cut.get('hashtags', "#crypto #ai #trading")
                
                # Use dedicated AI description if available, else fallback to script-based
                base_desc = ai_desc if ai_desc else script
                viral_description = f"{viral_title}\n\n{base_desc}\n\n{hashtags}"
                
                logging.info(f"📢 PUBLISHING: Viral video with AI Title: {viral_title}")
                await social_publisher.publish_everywhere(final_video, viral_title, viral_description)
            except Exception as publish_err:
                logging.error(f"❌ PUBLISHING ERROR for {win['symbol']}: {publish_err}")

    async def _handle_text_marketing(self, win):
        """Processes AI text + Image report for Telegram."""
        # Используем Gemini для перефразирования отчета
        report_text = script_writer.generate_rephrased_report(win)
        # Генерируем только картинку (PnL Card)
        image_path = video_generator.generate_marketing_media(win, "Report Only")
        
        logging.info(f"📱 MEDIA CORE: Sending text report for {win['symbol']} to Telegram...")
        await social_publisher.post_image_to_telegram(image_path, report_text)

    async def run_forever(self, interval_hours=12):
        """Runs every 12 hours (approx 1-2 videos per day)."""
        while True:
            await self.process_new_wins()
            await asyncio.sleep(interval_hours * 3600)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    orchestrator = MediaCoreOrchestrator()
    asyncio.run(orchestrator.run_forever())
