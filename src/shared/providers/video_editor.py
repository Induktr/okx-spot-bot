import logging
import os
import random
import PIL.Image
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, CompositeAudioClip
import moviepy.video.fx.all as vfx
import math

# FIX: Monkeypatch for Pillow 10+ compatibility with MoviePy
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

class VideoEditor:
    """
    Advanced VideoEditor (Format Voyager).
    Supports multiple viral formats: SPLIT_SCREEN, POV_PHONE, HYPE_GLITCH, MINIMAL_STORY.
    """
    def __init__(self):
        self.output_dir = "src/data/marketing_outputs"
        self.sound_dir = "data/assets/sounds"
        os.makedirs(self.output_dir, exist_ok=True)

    def assemble_final_video(self, bg_video_path, audio_path, overlay_path, win_id, style="DEFAULT", bg_music_path=None, format_type="DEFAULT"):
        """
        Assembles video based on a specific Viral Format Type.
        """
        if not bg_video_path or not audio_path:
            return None

        output_path = os.path.join(self.output_dir, f"viral_{format_type}_{win_id}.mp4")

        try:
            logging.info(f"🎞️ VIDEO EDITOR: Crafting [{format_type}] format for win #{win_id}...")
            
            # Load assets
            video_clip = VideoFileClip(bg_video_path)
            voice_clip = AudioFileClip(audio_path)
            duration = voice_clip.duration
            
            # Loop/Trim video
            if video_clip.duration < duration:
                video_clip = vfx.loop(video_clip, duration=duration)
            else:
                video_clip = video_clip.subclip(0, duration)
            
            # --- UNIQUENESS ENGINE (Bypass Duplication Filters) ---
            import random
            if random.random() > 0.6: # 40% chance to flip
                video_clip = vfx.mirror_x(video_clip)
            
            # Tiny random zoom (1.03x) to change all pixel coordinates
            video_clip = video_clip.resize(1.03)
            # Gentle brightness variation (0.98x - 1.02x)
            video_clip = (video_clip.fx(vfx.colorx, random.uniform(0.98, 1.02)))
            
            # Audio Mixing (Prioritizing Voice Clarity)
            voice_vol = voice_clip.volumex(2.5) # Boost voice even more
            if bg_music_path and os.path.exists(bg_music_path):
                # Background music should be barely audible ambience
                bg_music = AudioFileClip(bg_music_path).set_duration(duration).volumex(0.01)
                final_audio = CompositeAudioClip([voice_vol, bg_music])
            else:
                final_audio = voice_vol
            
            video_clip = video_clip.set_audio(final_audio)

            # --- VIRAL FORMAT LOGIC ---
            final_clips = [video_clip]

            if format_type == "SPLIT_SCREEN":
                # Top: Secondary video (e.g., luxury), Bottom: Main background (or vice versa)
                # For simplicity, we just crop and stack
                v_h = video_clip.h
                top_part = video_clip.crop(y1=0, y2=v_h/2).set_position(("center", "top"))
                # We reuse the same video but offset for split effect (simulated)
                bottom_part = video_clip.crop(y1=v_h/2, y2=v_h).set_position(("center", "bottom"))
                final_clips = [top_part, bottom_part]

            elif format_type == "POV_PHONE":
                # Adds a subtle phone-frame effect or just different zoom
                video_clip = video_clip.resize(lambda t: 1 + 0.05*t) # Slow zoom-in
                final_clips = [video_clip]

            elif format_type == "HYPE_GLITCH":
                # Apply glitch effects at intervals
                video_clip = video_clip.fx(vfx.mirror_x) if random.choice([True, False]) else video_clip
                final_clips = [video_clip]

            # 4. Add Overlay with Animated Appearance
            if overlay_path and os.path.exists(overlay_path):
                overlay = ImageClip(overlay_path).set_duration(duration)
                
                # Dynamic Scaling based on format
                h_factor = 0.7 if format_type != "SPLIT_SCREEN" else 0.4
                # 1. Base resize to fit the screen (70% of height)
                h_factor = 0.7 if format_type != "SPLIT_SCREEN" else 0.4
                overlay = overlay.resize(height=video_clip.h * h_factor)
                
                # 2. Advanced Animation Engine (Safe FX Mode)
                # Pulse / Breath effect (Sinusoidal scale)
                def breath_effect(t):
                    # Gentle oscillation between 0.98 and 1.02
                    return 1.0 + 0.02 * math.cos(t * 2.0)

                # Apply FX Chain
                overlay = (overlay.set_start(0.5)  # Start after 0.5s for better pacing
                          .fx(vfx.fadein, 1.0)     # Smooth fade in for 1s
                          .fx(vfx.fadeout, 1.0)    # Smooth fade out for 1s at the end
                          .fx(vfx.resize, breath_effect) # Dynamic breathing
                          .set_position(("center", "center")))

                final_clips.append(overlay)

            # Assemble and Write
            result = CompositeVideoClip(final_clips)
            result.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
            
            return output_path
            
        except Exception as e:
            logging.error(f"❌ Video Editor Error: {e}")
            return None

video_editor = VideoEditor()
