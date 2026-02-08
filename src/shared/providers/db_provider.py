import sqlite3
import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

class DatabaseProvider:
    """
    Core Engine Infrastructure (Idea 3).
    Centralized database to replace flat JSON files for memory, portfolio, and settings.
    Ready for transition to TimescaleDB/PostgreSQL.
    """
    def __init__(self, db_name: str = "src/shared/data/astra_core.db"):
        self.db_name = db_name
        self._ensure_db_dir()
        self._init_tables()
        logging.info(f"🗄️ DATABASE: Provider initialized. Storage: {db_name}")

    def _ensure_db_dir(self):
        os.makedirs(os.path.dirname(self.db_name), exist_ok=True)

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def _init_tables(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Portfolio Snapshots (Real-time Equity Curve)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    balance REAL NOT NULL,
                    mode TEXT NOT NULL -- 'REAL' or 'DEMO'
                )
            ''')
            
            # 2. AI Memory Bank (Analysis History)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT NOT NULL,
                    score REAL,
                    action TEXT,
                    reasoning TEXT,
                    market_context TEXT
                )
            ''')
            
            # 3. System Logs (High Performance Persistence)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level TEXT,
                    message TEXT
                )
            ''')

            # 4. Active Trades (Target State for Reconciliation)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS active_trades (
                    symbol TEXT PRIMARY KEY,
                    side TEXT NOT NULL,
                    size REAL NOT NULL,
                    entry_price REAL,
                    leverage INTEGER,
                    hurst REAL DEFAULT 0.5,
                    fisher REAL DEFAULT 0.0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # --- MIGRATION: ADD QUANTUM COLUMNS IF MISSING (Idea 5) ---
            try:
                cursor.execute("ALTER TABLE active_trades ADD COLUMN hurst REAL DEFAULT 0.5")
                cursor.execute("ALTER TABLE active_trades ADD COLUMN fisher REAL DEFAULT 0.0")
            except sqlite3.OperationalError:
                pass # Already exists
            
            conn.commit()

    # --- Portfolio Methods ---
    def record_balance(self, balance: float, mode: str = "REAL"):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO portfolio_history (balance, mode) VALUES (?, ?)",
                    (balance, mode)
                )
        except Exception as e:
            logging.error(f"❌ DB ERROR (record_balance): {e}")

    def get_portfolio_history(self, mode: str = "REAL", limit: int = 1000) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT timestamp, balance FROM portfolio_history WHERE mode = ? ORDER BY timestamp DESC LIMIT ?",
                    (mode, limit)
                )
                rows = cursor.fetchall()
                # Return in chronological order
                return [{"timestamp": str(r["timestamp"]), "balance": float(r["balance"])} for r in reversed(rows)]
        except Exception as e:
            logging.error(f"❌ DB ERROR (get_history): {e}")
            return []

    def clear_portfolio_history(self, mode: str = "REAL"):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "DELETE FROM portfolio_history WHERE mode = ?",
                    (mode,)
                )
                conn.commit()
            logging.info(f"🗄️ DATABASE: Cleared portfolio history for mode: {mode}")
            return True
        except Exception as e:
            logging.error(f"❌ DB ERROR (clear_history): {e}")
            return False

    # --- Memory Methods ---
    def store_analysis(self, symbol: str, analysis: Dict[str, Any], market_context: str):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO ai_memory (symbol, score, action, reasoning, market_context) VALUES (?, ?, ?, ?, ?)",
                    (
                        symbol, 
                        analysis.get("sentiment_score"), 
                        analysis.get("action"), 
                        analysis.get("reasoning"), 
                        market_context[:1000]
                    )
                )
        except Exception as e:
            logging.error(f"❌ DB ERROR (store_analysis): {e}")

    def get_memory_history(self, symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM ai_memory WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?",
                    (symbol, limit)
                )
                rows = cursor.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            logging.error(f"❌ DB ERROR (get_memory): {e}")
            return []

    # --- Active Trade Methods (Idea 3 - Reconciliation) ---
    def update_active_trade(self, symbol: str, side: str, size: float, price: float, leverage: int, hurst: float = 0.5, fisher: float = 0.0):
        """Upserts an active trade into the target state table with Quantum Trace."""
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    INSERT INTO active_trades (symbol, side, size, entry_price, leverage, hurst, fisher, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(symbol) DO UPDATE SET
                        side=excluded.side,
                        size=excluded.size,
                        entry_price=excluded.entry_price,
                        leverage=excluded.leverage,
                        hurst=excluded.hurst,
                        fisher=excluded.fisher,
                        timestamp=CURRENT_TIMESTAMP
                ''', (symbol, side.upper(), size, price, leverage, hurst, fisher))
        except Exception as e:
            logging.error(f"❌ DB ERROR (update_active_trade): {e}")

    def close_active_trade(self, symbol: str):
        """Removes a trade from the target state table."""
        try:
            with self.get_connection() as conn:
                conn.execute("DELETE FROM active_trades WHERE symbol = ?", (symbol,))
        except Exception as e:
            logging.error(f"❌ DB ERROR (close_active_trade): {e}")

    def get_active_trades(self) -> Dict[str, Dict[str, Any]]:
        """Returns all active trades from the database for reconciliation."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT * FROM active_trades")
                rows = cursor.fetchall()
                return {r["symbol"]: dict(r) for r in rows}
        except Exception as e:
            logging.error(f"❌ DB ERROR (get_active_trades): {e}")
            return {}

# Global DB Instance
db_engine = DatabaseProvider()
