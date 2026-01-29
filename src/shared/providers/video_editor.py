import logging
import os
import random
import PIL.Image, PIL.ImageDraw, PIL.ImageFont
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, CompositeAudioClip
import moviepy.video.fx.all as vfx
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
        self.output_dir = "src/data/marketing_outputs"
        self.sound_dir = "data/assets/sounds"
        os.makedirs(self.output_dir, exist_ok=True)
        # Default font paths for Windows/Linux
        self.font_paths = [
            "C:/Windows/Fonts/impact.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
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
        
        # Create transparent canvas
        img = PIL.Image.new('RGBA', (width, 200), (0, 0, 0, 0))
        draw = PIL.ImageDraw.Draw(img)
        font = self._get_font(font_size)
        
        # Calculate Y start for centering lines
        line_height = font_size + 10
        total_h = len(lines) * line_height
        y = (200 - total_h) // 2
        
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
            
        # Convert to MoviePy ImageClip
        temp_img_path = f"data/temp_subtitle_{random.randint(0,9999)}.png"
        img.save(temp_img_path)
        clip = ImageClip(temp_img_path).set_duration(duration)
        # We don't delete temp file immediately as MoviePy might need it during render
        return clip

    def assemble_final_video(self, bg_video_path, audio_path, overlay_path, win_id, style="DEFAULT", bg_music_path=None, format_type="DEFAULT", secondary_video_path=None, script_text=""):
        """
        Assembles video with Retention Engine:
        1. Dynamic Subtitles (Hormozi style)
        2. Delayed PnL Reveal (Curiosity Gap)
        3. CTA End Card (Conversion)
        """
        if not bg_video_path or not audio_path:
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
            
            # 1. Assets Setup
            video_clip = VideoFileClip(bg_video_path)
            voice_clip = AudioFileClip(audio_path)
            target_duration = voice_clip.duration
            
            # 2. Transformations
            if random.random() > 0.4: video_clip = vfx.mirror_x(video_clip)
            speed_factor = random.uniform(0.99, 1.01)
            video_clip = video_clip.fx(vfx.speedx, speed_factor)
            video_clip = video_clip.resize(random.uniform(1.02, 1.08))
            video_clip = (video_clip.fx(vfx.colorx, random.uniform(0.97, 1.03)))
            
            if video_clip.duration < target_duration:
                video_clip = vfx.loop(video_clip, duration=target_duration + 0.1)
            video_clip = video_clip.subclip(0, target_duration)
            
            # 3. Audio Mix
            voice_vol = voice_clip.volumex(2.5) 
            if bg_music_path and os.path.exists(bg_music_path):
                bg_music = AudioFileClip(bg_music_path).set_duration(target_duration).volumex(random.uniform(0.015, 0.04))
                final_audio = CompositeAudioClip([voice_vol, bg_music])
            else:
                final_audio = voice_vol
            video_clip = video_clip.set_audio(final_audio)

            final_clips = [video_clip]

            # 4. Split Screen logic
            if format_type == "SPLIT_SCREEN" and secondary_video_path and os.path.exists(secondary_video_path):
                sec_clip = VideoFileClip(secondary_video_path)
                if sec_clip.duration < target_duration: sec_clip = vfx.loop(sec_clip, duration=target_duration + 0.1)
                sec_clip = sec_clip.subclip(0, target_duration)
                target_w, target_h = 720, 1280
                top_part = video_clip.resize(width=target_w).crop(width=target_w, height=target_h/2, x_center=target_w/2, y_center=video_clip.h/2)
                bot_part = sec_clip.resize(width=target_w).crop(width=target_w, height=target_h/2, x_center=target_w/2, y_center=sec_clip.h/2)
                video_clip = CompositeVideoClip([top_part.set_position("top"), bot_part.set_position("bottom")], size=(target_w, target_h))
                final_clips = [video_clip]

            # 5. RETENTION: Dynamic Subtitles
            if script_text:
                logging.info("📝 VIDEO EDITOR: Generating Retention Subtitles...")
                # Split by punctuation or newlines
                phrases = [p.strip() for p in script_text.replace(".", ".|").replace("!", "!|").replace("?", "?|").split("|") if len(p.strip()) > 5]
                if phrases:
                    chunk_dur = target_duration / len(phrases)
                    for i, phrase in enumerate(phrases):
                        sub_clip = self._generate_text_clip(phrase.upper(), chunk_dur, width=video_clip.w)
                        sub_clip = sub_clip.set_start(i * chunk_dur).set_position(('center', video_clip.h * 0.7))
                        final_clips.append(sub_clip)

            # 6. RETENTION: Delayed PnL Reveal
            if overlay_path and os.path.exists(overlay_path):
                logging.info("🖼️ VIDEO EDITOR: Adding Delayed PnL Overlay...")
                overlay = ImageClip(overlay_path)
                h_factor = 0.55 if format_type != "SPLIT_SCREEN" else 0.35
                overlay = overlay.resize(height=video_clip.h * h_factor)
                
                # Appearance delay (Hook first, then proof)
                reveal_time = 2.5 if target_duration > 5 else 1.0
                overlay = (overlay.set_start(reveal_time)
                           .set_duration(target_duration - reveal_time)
                           .fx(vfx.fadein, 0.5))
                
                pos_y = (video_clip.h - overlay.h) // 2
                final_clips.append(overlay.set_position(('center', pos_y)))

            # 7. RETENTION: CTA Final Card
            cta_text = "DASHBOARD LINK IN BIO 🚀"
            cta_dur = 2.5
            if target_duration > 4:
                cta_clip = self._generate_text_clip(cta_text, cta_dur, width=video_clip.w, font_size=50, color=(0, 255, 0))
                cta_clip = cta_clip.set_start(target_duration - cta_dur).set_position(('center', video_clip.h * 0.15))
                final_clips.append(cta_clip)

            # 8. Render
            result = CompositeVideoClip(final_clips)
            final_fps = random.choice([24, 25, 30])
            result.write_videofile(output_path, fps=final_fps, codec="libx264", audio_codec="aac", 
                                   logger=None, preset="ultrafast", threads=4)
            
            # 9. Cleanup temp subtitle images
            try:
                for f in os.listdir("data"):
                    if f.startswith("temp_subtitle_"): os.remove(os.path.join("data", f))
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
