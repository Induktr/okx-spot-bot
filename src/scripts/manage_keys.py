import json
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

ADMIN_KEYS_PATH = "src/shared/data/admin_keys.json"

def load_keys():
    if not os.path.exists(ADMIN_KEYS_PATH):
        return []
    try:
        with open(ADMIN_KEYS_PATH, "r") as f:
            return json.load(f)
    except:
        return []

def save_keys(keys):
    os.makedirs(os.path.dirname(ADMIN_KEYS_PATH), exist_ok=True)
    with open(ADMIN_KEYS_PATH, "w") as f:
        json.dump(keys, f, indent=4)

def add_key(new_key):
    keys = load_keys()
    if new_key not in keys:
        keys.append(new_key)
        save_keys(keys)
        print(f"✅ Key added. Total keys: {len(keys)}")
    else:
        print("⚠️ Key already exists.")

def list_keys():
    keys = load_keys()
    print("\n--- GOOGLE GEMINI KEY POOL ---")
    for i, key in enumerate(keys):
        masked = key[:8] + "..." + key[-4:] if len(key) > 12 else key
        print(f"{i+1}. {masked}")
    print(f"Total: {len(keys)} nodes.\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python manage_keys.py list")
        print("  python manage_keys.py add <key>")
    else:
        cmd = sys.argv[1].lower()
        if cmd == "list":
            list_keys()
        elif cmd == "add" and len(sys.argv) > 2:
            add_key(sys.argv[2])
        else:
            print("Unknown command.")
