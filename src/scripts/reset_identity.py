
import os
import shutil
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def reset_identity():
    profile_path = os.path.join(os.getcwd(), "data", "chrome_debug_profile")
    if os.path.exists(profile_path):
        logging.info(f"🧹 Clearing browser profile at {profile_path}...")
        try:
            # We use a trick: delete everything except the folder itself to keep it 'ready'
            for filename in os.listdir(profile_path):
                file_path = os.path.join(profile_path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    logging.warning(f"Could not delete {file_path}: {e}")
            logging.info("✨ Identity reset complete. You are now a 'new user'.")
        except Exception as e:
            logging.error(f"❌ Failed to clear profile: {e}")
    else:
        logging.info("ℹ️ Profile path not found, nothing to clear.")

if __name__ == "__main__":
    reset_identity()
