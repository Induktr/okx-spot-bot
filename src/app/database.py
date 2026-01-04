import sqlite3
import hashlib
import secrets
from datetime import datetime
from pathlib import Path

DATABASE_PATH = Path("data/users.db")

def init_database():
    """Initialize the database with required tables."""
    DATABASE_PATH.parent.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Subscriptions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            wallet_address TEXT,
            status TEXT NOT NULL DEFAULT 'LITE',
            expiry_timestamp REAL DEFAULT 0,
            refund_pending INTEGER DEFAULT 0,
            transaction_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # User Settings table (API keys and trading config)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            okx_api_key TEXT,
            okx_secret TEXT,
            okx_password TEXT,
            binance_api_key TEXT,
            binance_secret TEXT,
            bybit_api_key TEXT,
            bybit_secret TEXT,
            active_exchanges TEXT DEFAULT '[]',
            trade_amount REAL DEFAULT 20.0,
            max_leverage INTEGER DEFAULT 10,
            symbols TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("[OK] Database initialized successfully!")

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(email: str, password: str, role: str = 'user') -> int:
    """Create a new user and return user_id."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    password_hash = hash_password(password)
    
    try:
        cursor.execute(
            "INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)",
            (email, password_hash, role)
        )
        user_id = cursor.lastrowid
        
        # Create initial LITE subscription for the user
        cursor.execute(
            "INSERT INTO subscriptions (user_id, status) VALUES (?, 'LITE')",
            (user_id,)
        )
        
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None  # Email already exists
    finally:
        conn.close()

def verify_user(email: str, password: str) -> dict | None:
    """Verify user credentials and return user data."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    password_hash = hash_password(password)
    
    cursor.execute(
        "SELECT id, email, role FROM users WHERE email = ? AND password_hash = ?",
        (email, password_hash)
    )
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {"id": user[0], "email": user[1], "role": user[2]}
    return None

def get_user_by_id(user_id: int) -> dict | None:
    """Get user data by ID."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, email, role FROM users WHERE id = ?",
        (user_id,)
    )
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {"id": user[0], "email": user[1], "role": user[2]}
    return None

def get_user_subscription(user_id: int) -> dict | None:
    """Get active subscription for a user."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT id, wallet_address, status, expiry_timestamp, refund_pending, transaction_hash
           FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1""",
        (user_id,)
    )
    
    sub = cursor.fetchone()
    conn.close()
    
    if sub:
        return {
            "id": sub[0],
            "wallet_address": sub[1],
            "status": sub[2],
            "expiry_timestamp": sub[3],
            "refund_pending": bool(sub[4]),
            "transaction_hash": sub[5]
        }
    return None

def update_subscription(user_id: int, **kwargs) -> bool:
    """Update subscription fields for a user."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Build dynamic UPDATE query
    fields = []
    values = []
    for key, value in kwargs.items():
        if key in ['wallet_address', 'status', 'expiry_timestamp', 'refund_pending', 'transaction_hash']:
            fields.append(f"{key} = ?")
            values.append(value)
    
    if not fields:
        return False
    
    values.append(user_id)
    query = f"UPDATE subscriptions SET {', '.join(fields)} WHERE user_id = ?"
    
    cursor.execute(query, values)
    conn.commit()
    conn.close()
    return True

def get_all_users_with_subscriptions() -> list:
    """Get all users with their subscription status (for admin panel)."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT u.id, u.email, u.role, s.wallet_address, s.status, s.expiry_timestamp, s.refund_pending
        FROM users u
        LEFT JOIN subscriptions s ON u.id = s.user_id
        ORDER BY u.created_at DESC
    """)
    
    users = cursor.fetchall()
    conn.close()
    
    result = []
    for user in users:
        result.append({
            "id": user[0],
            "email": user[1],
            "role": user[2],
            "wallet_address": user[3],
            "status": user[4] or "LITE",
            "expiry_timestamp": user[5] or 0,
            "refund_pending": bool(user[6])
        })
    
    return result

def get_user_settings(user_id: int) -> dict | None:
    """Get trading settings for a user."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT okx_api_key, okx_secret, okx_password, binance_api_key, binance_secret,
                  bybit_api_key, bybit_secret, active_exchanges, trade_amount, max_leverage, symbols
           FROM user_settings WHERE user_id = ?""",
        (user_id,)
    )
    
    settings = cursor.fetchone()
    conn.close()
    
    if settings:
        import json
        return {
            "okx_api_key": settings[0] or "",
            "okx_secret": settings[1] or "",
            "okx_password": settings[2] or "",
            "binance_api_key": settings[3] or "",
            "binance_secret": settings[4] or "",
            "bybit_api_key": settings[5] or "",
            "bybit_secret": settings[6] or "",
            "active_exchanges": json.loads(settings[7]) if settings[7] else [],
            "trade_amount": settings[8] or 20.0,
            "max_leverage": settings[9] or 10,
            "symbols": json.loads(settings[10]) if settings[10] else []
        }
    return None

def update_user_settings(user_id: int, **kwargs) -> bool:
    """Update or create user settings."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if settings exist
    cursor.execute("SELECT id FROM user_settings WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone()
    
    import json
    
    # Convert lists to JSON strings
    if 'active_exchanges' in kwargs and isinstance(kwargs['active_exchanges'], list):
        kwargs['active_exchanges'] = json.dumps(kwargs['active_exchanges'])
    if 'symbols' in kwargs and isinstance(kwargs['symbols'], list):
        kwargs['symbols'] = json.dumps(kwargs['symbols'])
    
    if exists:
        # Update existing settings
        fields = []
        values = []
        for key, value in kwargs.items():
            if key in ['okx_api_key', 'okx_secret', 'okx_password', 'binance_api_key', 
                      'binance_secret', 'bybit_api_key', 'bybit_secret', 'active_exchanges',
                      'trade_amount', 'max_leverage', 'symbols']:
                fields.append(f"{key} = ?")
                values.append(value)
        
        if fields:
            values.append(user_id)
            query = f"UPDATE user_settings SET {', '.join(fields)} WHERE user_id = ?"
            cursor.execute(query, values)
    else:
        # Create new settings
        cursor.execute(
            """INSERT INTO user_settings (user_id, okx_api_key, okx_secret, okx_password,
                                         binance_api_key, binance_secret, bybit_api_key, bybit_secret,
                                         active_exchanges, trade_amount, max_leverage, symbols)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id,
             kwargs.get('okx_api_key', ''),
             kwargs.get('okx_secret', ''),
             kwargs.get('okx_password', ''),
             kwargs.get('binance_api_key', ''),
             kwargs.get('binance_secret', ''),
             kwargs.get('bybit_api_key', ''),
             kwargs.get('bybit_secret', ''),
             kwargs.get('active_exchanges', '[]'),
             kwargs.get('trade_amount', 20.0),
             kwargs.get('max_leverage', 10),
             kwargs.get('symbols', '[]'))
        )
    
    conn.commit()
    conn.close()
    return True

if __name__ == "__main__":
    # Initialize database
    init_database()
    
    # Create admin user (only run once)
    admin_id = create_user("admin@astra.ai", "admin_secure_password_123", role="admin")
    if admin_id:
        print(f"[OK] Admin user created with ID: {admin_id}")
    else:
        print("[WARNING] Admin user already exists.")
