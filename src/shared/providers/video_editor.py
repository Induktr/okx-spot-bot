import logging
import os
import random
import PIL.Image, PIL.ImageDraw, PIL.ImageFont
try:
    from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, CompositeAudioClip
    import moviepy.video.fx.all as vfx
except ImportError:
    # MoviePy 2.x compatibility
    from moviepy import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, CompositeAudioClip
    import moviepy.video.fx as vfx
import math
import textwrap

# FIX: Monkeypatch for Pillow 10+ compatibility with MoviePy
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

class VideoEditor:
    """
    Advanced VideoEditor (Format Voyager).
    Supports multiple viral formats: SPLIT_SCREEN, POV_PHONE, HYPE_GLITCH, MINIMAL_STORY.
    Includes RETENTION ENGINE: Dynamic Subtitles & Scheduled Overlays.
    """
    def __init__(self):
        self.output_dir = "src/shared/data/marketing_outputs"
        self.sound_dir = "src/shared/data/assets/sounds"
        os.makedirs(self.output_dir, exist_ok=True)
        # Default font paths for Windows/Linux
        self.font_paths = [
            "C:/Windows/Fonts/impact.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/timesbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
        ]

    def _get_font(self, size):
        for path in self.font_paths:
            if os.path.exists(path):
                try:
                    return PIL.ImageFont.truetype(path, size)
                except: continue
        return PIL.ImageFont.load_default()

    def _generate_text_clip(self, text, duration, width=720, height=1280, font_size=60, color=(255, 255, 0), stroke_color=(0,0,0), stroke_width=4):
        """Generates a text ImageClip using Pillow (no ImageMagick needed)."""
        # Multi-line wrap
        lines = textwrap.wrap(text, width=15) # Short lines for TikTok
        
        # Create transparent canvas with dynamic height
        line_height = font_size + 15
        total_h = len(lines) * line_height + 40 # Added padding
        img = PIL.Image.new('RGBA', (width, total_h), (0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(img)
        font = self._get_font(font_size)
        
        y = 20 # Start with padding
        
        for line in lines:
            # Get text bounding box for centering
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            x = (width - text_w) // 2
            
            # Draw stroke/shadow
            for off in range(-stroke_width, stroke_width + 1):
                draw.text((x + off, y), line, font=font, fill=stroke_color)
                draw.text((x, y + off), line, font=font, fill=stroke_color)
            
            # Draw main text
            draw.text((x, y), line, font=font, fill=color)
            y += line_height
            
        temp_img_path = f"src/shared/data/temp_subtitle_{random.randint(0,9999)}.png"
        img.save(temp_img_path)
        clip = ImageClip(temp_img_path).set_duration(duration)
        # We don't delete temp file immediately as MoviePy might need it during render
        return clip

    async def generate_animated_image_clip(self, image_path, duration, target_w=720, target_h=1280):
        """Creates a cinematic pan/zoom effect from a static image."""
        if not os.path.exists(image_path): return None
        clip = ImageClip(image_path).set_duration(duration)
        
        # Resize to cover with some margin for zoom
        clip = clip.resize(width=target_w * 1.3) 
        
        # Ken Burns: Slow Zoom + Slight Pan
        # We use a lambda for size and position to animate
        def zoom(t):
            return 1.0 + 0.05 * (t / duration) # 5% zoom over duration
        
        clip = clip.fx(vfx.resize, zoom)
        clip = clip.set_position(lambda t: ('center', -50 + 50 * (t / duration))) # Slow pan down
        
        # Crop to target resolution
        from moviepy.video.VideoClip import ColorClip
        canvas = ColorClip(size=(target_w, target_h), color=(0,0,0)).set_duration(duration)
        final_bg = CompositeVideoClip([canvas, clip.set_position("center")], size=(target_w, target_h))
        return final_bg

    def assemble_final_video(self, primary_content_path, audio_path, overlay_path, win_id, style="DEFAULT", bg_music_path=None, format_type="DEFAULT", secondary_video_path=None, script_text="", env_bg_path=None):
        """
        Assembles video with Dual-Layer Aesthetic:
        1. Environment Background (AI Image or Stock Video)
        2. Primary Content (TradingView or Pexels) - Centered
        3. Dynamic Subtitles & Overlays
        """
        if not primary_content_path or not audio_path:
            return None

        # --- NATURAL FILENAME GENERATOR ---
        import datetime
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        rand_id = random.randint(1000, 9999)
        
        patterns = [
            f"VID_{timestamp_str}.mp4",
            f"IMG_{rand_id}.mp4",
            f"Project_{now.strftime('%m%d')}_{rand_id}.mp4",
            f"Export_{timestamp_str}.mp4"
        ]
        natural_name = random.choice(patterns)
        output_path = os.path.join(self.output_dir, natural_name)

        try:
            logging.info(f"🎞️ VIDEO EDITOR: Crafting [{format_type}] retention video for win #{win_id}...")
            
            # 1. Assets Setup & Phase 1 Transformations
            video_clip = VideoFileClip(primary_content_path)
            
            # --- LOADING SCREEN BYPASS ---
            if "chart_" in primary_content_path and video_clip.duration > 8:
                logging.info("✂️ VIDEO EDITOR: Trimming 8s loading screen from chart clip.")
                video_clip = video_clip.subclip(8)
                
            voice_clip = AudioFileClip(audio_path)
            target_duration = voice_clip.duration
            
            # Duration Sync
            if video_clip.duration < target_duration:
                video_clip = vfx.loop(video_clip, duration=target_duration + 0.1)
            video_clip = video_clip.subclip(0, target_duration)
            
            # Subtle randomization (No mirroring for charts)
            video_clip = (video_clip.fx(vfx.colorx, random.uniform(0.98, 1.02)))

            # 3. Canvas Setup (9:16 Vertical)
            target_w, target_h = 720, 1280
            
            # --- LAYER 1: Environment Background ---
            # Use provided env_bg or fallback to a black canvas
            if env_bg_path and os.path.exists(env_bg_path):
                if env_bg_path.endswith(('.png', '.jpg', '.jpeg')):
                    canvas_clip = ImageClip(env_bg_path).set_duration(target_duration).resize(height=target_h)
                    if canvas_clip.w < target_w: canvas_clip = canvas_clip.resize(width=target_w)
                    # Add breathing motion (Ken Burns)
                    canvas_clip = canvas_clip.set_position("center").fx(vfx.resize, lambda t: 1.0 + 0.05*(t/target_duration))
                    canvas_clip = CompositeVideoClip([canvas_clip], size=(target_w, target_h))
                else:
                    canvas_clip = VideoFileClip(env_bg_path)
                    if canvas_clip.duration < target_duration: canvas_clip = vfx.loop(canvas_clip, duration=target_duration + 0.5)
                    canvas_clip = canvas_clip.subclip(0, target_duration).resize(height=target_h)
                    if canvas_clip.w < target_w: canvas_clip = canvas_clip.resize(width=target_w)
                    canvas_clip = canvas_clip.set_position("center")
            else:
                # Default black canvas
                background_canvas = PIL.Image.new('RGB', (target_w, target_h), (0, 0, 0))
                bg_p = "src/shared/data/temp_canvas.png"
                background_canvas.save(bg_p)
                canvas_clip = ImageClip(bg_p).set_duration(target_duration)
            
            # --- LAYER 2: Primary Content Scaling ---
            # Centering & Scaling the already processed video_clip
            video_clip = video_clip.resize(width=target_w)
            if video_clip.h > target_h: video_clip = video_clip.resize(height=target_h)
            video_clip = video_clip.set_position(("center", "center"))
            
            # Audio
            voice_vol = voice_clip.volumex(2.5) 
            if bg_music_path and os.path.exists(bg_music_path):
                bg_music = AudioFileClip(bg_music_path).set_duration(target_duration).volumex(random.uniform(0.015, 0.04))
                final_audio = CompositeAudioClip([voice_vol, bg_music])
            else:
                final_audio = voice_vol
            
            # Assemble base
            main_layer = CompositeVideoClip([canvas_clip, video_clip], size=(target_w, target_h)).set_audio(final_audio)
            final_clips = [main_layer]

            # 4. Content Layering (Pure Centered Format)
            # Split screen and filler videos have been decommissioned for institutional clarity.
            video_clip = video_clip.set_audio(final_audio)
            final_clips = [main_layer]
            # 5. RETENTION: Dynamic Subtitles
            if script_text:
                logging.info("📝 VIDEO EDITOR: Generating Retention Subtitles...")
                # Improved splitting: split by punctuation AND length
                import re
                raw_phrases = re.split(r'[.!?\n]+', script_text)
                phrases = []
                for p in raw_phrases:
                    p = p.strip()
                    if not p: continue
                    # Further split long sentences by word count if needed (max 5-6 words per chunk)
                    words = p.split()
                    for i in range(0, len(words), 6):
                        chunk = " ".join(words[i:i+6])
                        if chunk: phrases.append(chunk)

                if phrases:
                    chunk_dur = target_duration / len(phrases)
                    for i, phrase in enumerate(phrases):
                        sub_clip = self._generate_text_clip(phrase.upper(), chunk_dur, width=target_w)
                        # Position higher to avoid TikTok lower-third UI (Description/Music)
                        sub_clip = sub_clip.set_start(i * chunk_dur).set_position(('center', int(target_h * 0.82) - sub_clip.h//2))
                        final_clips.append(sub_clip)

            # 6. RETENTION: Delayed PnL Reveal
            if overlay_path and os.path.exists(overlay_path):
                logging.info("🖼️ VIDEO EDITOR: Adding HIGH-VISIBILITY PnL Overlay...")
                overlay = ImageClip(overlay_path)
                # Reduced size to avoid chart overlap while keeping it large
                h_factor = 0.33 if format_type != "SPLIT_SCREEN" else 0.25
                overlay = overlay.resize(height=target_h * h_factor)
                
                # Appearance delay
                reveal_time = 2.5 if target_duration > 5 else 1.0
                overlay = (overlay.set_start(reveal_time)
                           .set_duration(target_duration - reveal_time)
                           .fx(vfx.fadein, 0.5))
                
                # Moving it to the absolute top to avoid ANY chart overlap
                pos_y = int(target_h * 0.01) 
                final_clips.append(overlay.set_position(('center', pos_y)))
            # 7. RETENTION: CTA Final Card
            cta_text = "DASHBOARD LINK IN BIO 🚀"
            cta_dur = 2.5
            if target_duration > 4:
                cta_clip = self._generate_text_clip(cta_text, cta_dur, width=target_w, font_size=50, color=(0, 255, 0))
                # Move CTA to the bottom area to avoid overlap with PnL
                cta_clip = cta_clip.set_start(target_duration - cta_dur).set_position(('center', target_h * 0.90))
                final_clips.append(cta_clip)
            # 8. Render
            result = CompositeVideoClip(final_clips)
            final_fps = random.choice([24, 25, 30])
            result.write_videofile(output_path, fps=final_fps, codec="libx264", audio_codec="aac", 
                                   logger=None, preset="ultrafast", threads=4)
            
            # 9. Cleanup temp subtitle images
            try:
                data_dir = "src/shared/data"
                for f in os.listdir(data_dir):
                    if f.startswith("temp_subtitle_"): os.remove(os.path.join(data_dir, f))
            except: pass

            # 10. Metadata Strip
            import subprocess
            try:
                ffmpeg_bin = "ffmpeg"
                try:
                    import moviepy.config as mp_cfg
                    ffmpeg_bin = mp_cfg.get_setting("FFMPEG_BINARY")
                except: pass
                
                temp_path = output_path.replace(".mp4", "_ghost.mp4")
                subprocess.run([ffmpeg_bin, '-y', '-i', output_path, '-map_metadata', '-1', '-c', 'copy', temp_path], check=True, capture_output=True)
                os.replace(temp_path, output_path)
                logging.info(f"👻 VIDEO EDITOR: Metadata stripped for {output_path}")
            except Exception as e:
                logging.warning(f"⚠️ Metadata strip failed: {e}")

            return output_path
            
        except Exception as e:
            logging.error(f"❌ Video Editor Error: {e}")
            return None

video_editor = VideoEditor()
