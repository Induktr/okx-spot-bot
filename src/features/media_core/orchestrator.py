import logging
import asyncio
from src.features.media_core.profit_scout import profit_scout
from src.features.media_core.script_writer import script_writer
from src.shared.providers.audio_provider import audio_provider
from src.shared.providers.pexels_provider import pexels_provider
from src.shared.providers.video_generator import video_generator
from src.shared.providers.video_editor import video_editor
from src.shared.providers.social_publisher import social_publisher

class MediaCoreOrchestrator:
    """
    Orchestrates the viral media creation pipeline using FREE tools.
    Finds wins -> Writes scripts -> Generates free audio -> Finds free background -> ASSEMBLES -> PUBLISHES.
    """
    async def process_new_wins(self):
        logging.info("📢 MEDIA CORE: Scanning for viral-worthy trades...")
        wins = profit_scout.find_big_wins()
        
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
            
        bg_video_path = pexels_provider.get_random_background(query=search_query)
        
        # --- SPLIT SCREEN (SATURATION) LOGIC ---
        # Forcevariety if AI is too conservative
        if format_type == 'DEFAULT' and random.random() > 0.5:
            format_type = random.choice(['SPLIT_SCREEN', 'POV_PHONE'])
            
        secondary_video_path = None
        if format_type == "SPLIT_SCREEN":
            logging.info("📢 MEDIA CORE: Fetching secondary satisfying content for SPLIT_SCREEN saturation...")
            satisfying_queries = ["satisfying sand", "hydraulic press", "relaxation aesthetic", "space nebula vertical", "jellyfish slow motion"]
            secondary_video_path = pexels_provider.get_random_background(query=random.choice(satisfying_queries))
        
        # Generate Dynamic Overlay (Style Match)
        overlay_path = video_generator.generate_marketing_media(
            win, 
            style_directive=style,
            heading=director_cut.get('card_heading'),
            status=director_cut.get('card_status')
        )
        
        # 4. ASSEMBLY
        try:
            final_video = video_editor.assemble_final_video(
                 bg_video_path, audio_path, overlay_path, win['id'], 
                 style=style, bg_music_path=bg_music_path, 
                 format_type=format_type,
                 secondary_video_path=secondary_video_path,
                 script_text=script
            )
        except Exception as assembly_err:
            logging.error(f"❌ ASSEMBLY ERROR for {win['symbol']}: {assembly_err}")
            return
        
        if final_video:
            try:
                # --- AI-DRIVEN VIRAL METADATA ---
                viral_title = director_cut.get('viral_title', f"A.S.T.R.A. Profit: {win['roi']}%")
                hashtags = director_cut.get('hashtags', "#crypto #ai #trading")
                
                # Combine into high-conversion description
                viral_description = f"{viral_title}\n\n{script}\n\n{hashtags}"
                
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
