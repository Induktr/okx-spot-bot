
import json
import os

ACCOUNTS_FILE = "src/data/hedra_accounts.json"

def save_account(email, password, cookies=None):
    if not os.path.exists("src/data"):
        os.makedirs("src/data")
    
    cookie_path = None
    if cookies:
        cookie_dir = "data/cookies"
        if not os.path.exists(cookie_dir):
            os.makedirs(cookie_dir)
        
        # Clean email for safe filename
        safe_email = email.replace("@", "_").replace(".", "_")
        cookie_path = os.path.join(cookie_dir, f"{safe_email}.json")
        with open(cookie_path, 'w') as f:
            json.dump(cookies, f, indent=4)
        print(f"🍪 Cookies saved for {email} -> {cookie_path}")

    # --- Save to local hedra_accounts.json ---
    accounts = []
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, 'r') as f:
                accounts = json.load(f)
        except:
            accounts = []
            
    accounts.append({
        "email": email,
        "password": password,
        "credits": 300,
        "status": "ready",
        "cookies_file": cookie_path
    })
    
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f, indent=4)
    print(f"✅ Account {email} saved to {ACCOUNTS_FILE}")

    # --- Sync with data/api_vault.json ---
    vault_path = "data/api_vault.json"
    if os.path.exists(vault_path):
        try:
            with open(vault_path, 'r') as f:
                vault = json.load(f)
            
            if "hedra" not in vault:
                vault["hedra"] = []
            
            vault["hedra"].append({
                "email": email,
                "password": password,
                "status": "active",
                "remaining_credits": 300,
                "cookies_file": cookie_path
            })
            
            with open(vault_path, 'w') as f:
                json.dump(vault, f, indent=4)
            print(f"📦 Synced {email} to api_vault.json")
        except Exception as e:
            print(f"⚠️ Failed to sync with vault: {e}")

def get_unused_account():
    if not os.path.exists(ACCOUNTS_FILE):
        return None
        
    with open(ACCOUNTS_FILE, 'r') as f:
        accounts = json.load(f)
        
    for acc in accounts:
        if acc.get("status") == "ready" and acc.get("credits", 0) > 0:
            return acc
    return None
