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
        """Processes full video pipeline."""
        script = script_writer.generate_viral_script(win)
        audio_path = await audio_provider.generate_speech(script, f"audio_{win['id']}")
        bg_video_path = pexels_provider.get_random_background(query="cyberpunk trading")
        overlay_path = video_generator.generate_marketing_media(win, script)
        
        final_video = video_editor.assemble_final_video(
            bg_video_path, audio_path, overlay_path, win['id']
        )
        
        if final_video:
            title = f"A.S.T.R.A. AI Profit: {win['roi']}% on {win['symbol']}"
            description = f"{script}\n\n#trading #ai #crypto #astra"
            await social_publisher.publish_everywhere(final_video, title, description)

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
