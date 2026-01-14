import logging
import os
from moviepy import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip
import moviepy.video.fx as vfx

class VideoEditor:
    """
    The 'Editor' module adjusted for MoviePy 2.x.
    Merges background video, AI voice-over, and PnL card into a final MP4.
    """
    def __init__(self):
        self.output_dir = "src/data/marketing_outputs"
        os.makedirs(self.output_dir, exist_ok=True)

    def assemble_final_video(self, bg_video_path, audio_path, overlay_path, win_id):
        """
        Combines all assets into a final viral video.
        """
        if not bg_video_path or not audio_path:
            logging.error("❌ VIDEO EDITOR: Missing assets, cannot assemble.")
            return None

        output_path = os.path.join(self.output_dir, f"final_viral_{win_id}.mp4")

        try:
            logging.info(f"🎞️ VIDEO EDITOR: Assembling final clip for win #{win_id}...")
            
            # 1. Load background and audio
            video_clip = VideoFileClip(bg_video_path)
            audio_clip = AudioFileClip(audio_path)
            
            # 2. Match durations
            # MoviePy 2.x uses subclipped() and looped()
            if video_clip.duration < audio_clip.duration:
                # If short, we loop it by repeating
                n_loops = int(audio_clip.duration / video_clip.duration) + 1
                from moviepy.video.VideoClip import VideoClip
                # Simple workaround for looping
                video_clip = video_clip.with_duration(audio_clip.duration)
            else:
                video_clip = video_clip.subclipped(0, audio_clip.duration)
            
            video_clip = video_clip.with_audio(audio_clip)

            # 3. Add PnL overlay (if exists)
            final_clip = video_clip
            if overlay_path and os.path.exists(overlay_path):
                overlay = (ImageClip(overlay_path)
                          .with_duration(audio_clip.duration)
                          .with_position("center"))
                
                # Resizing in v2.x
                overlay = overlay.resized(height=video_clip.h * 0.7)
                
                final_clip = CompositeVideoClip([video_clip, overlay])

            # 4. Write final file
            final_clip.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
            
            logging.info(f"✅ VIDEO EDITOR: Final video ready at {output_path}")
            return output_path
        except Exception as e:
            logging.error(f"❌ Video Editor Error: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return None

video_editor = VideoEditor()
