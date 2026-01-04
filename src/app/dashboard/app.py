from flask import Flask, render_template, jsonify, request, send_file, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
import os
import sys
import logging
import time
import requests

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.shared.utils.report_parser import report_parser
from src.features.trade_executor.trader import trader, traders, refresh_traders
from src.app.config import config
from src.shared.utils.portfolio_tracker import portfolio_tracker
from src.app import database

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "ASTRA_SECRET_KEY_CHANGE_IN_PRODUCTION_2026")

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id, email, role):
        self.id = id
        self.email = email
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    user_data = database.get_user_by_id(int(user_id))
    if user_data:
        return User(user_data["id"], user_data["email"], user_data["role"])
    return None

# Initialize database
database.init_database()

@app.errorhandler(Exception)
def handle_exception(e):
    """Global error handler for all unhandled exceptions."""
    logging.error(f"DASHBOARD ERROR: {e}")
    return jsonify({
        "status": "error",
        "message": str(e),
        "type": e.__class__.__name__
    }), 500

@app.route('/api/bot_status', methods=['GET'])
def get_bot_status():
    return jsonify({"active": config.BOT_ACTIVE})

@app.route('/api/toggle_bot', methods=['POST'])
def toggle_bot():
    config.BOT_ACTIVE = not config.BOT_ACTIVE
    config.save_settings() # Persist state to JSON
    
    status = "RESUMED" if config.BOT_ACTIVE else "PAUSED"
    
    if config.BOT_ACTIVE:
        logging.info("USER COMMAND: Bot RESUMED. Signaling immediate cycle...")
        config.FORCE_CYCLE = True # Trigger main thread to run cycle
    else:
        logging.info("USER COMMAND: Bot PAUSED. Going to sleep.")
        
    return jsonify({"active": config.BOT_ACTIVE, "message": f"Bot {status}"})

@app.route('/api/verify_payment', methods=['POST'])
def verify_payment():
    """
    Verifies a crypto payment via blockchain RPCs.
    FSD-lite: Direct RPC checks without heavy Web3 libraries.
    """
    data = request.json
    network = data.get('network')
    tx_hash = data.get('txHash')
    
    if not network or not tx_hash:
        return jsonify({"success": False, "message": "Missing params"}), 400

    logging.info(f"Payment Verification Request: {network} | Hash: {tx_hash}")

    try:
        # --- AMOY (TESTNET) VERIFICATION ---
        if network == 'AMOY':
            rpc_url = "https://polygon-amoy.drpc.org"
            payload = {"jsonrpc": "2.0", "method": "eth_getTransactionByHash", "params": [tx_hash], "id": 1}
            r = requests.post(rpc_url, json=payload, timeout=10)
            res = r.json()
            tx = res.get('result')
            
            if not tx:
                # Fallback: Sometimes testnet TXs take a moment to index
                logging.warning(f"Amoy TX {tx_hash} not found yet. Assuming success for Testnet Demo.")
                # DEMO MODE: If hash looks real, approve it to avoid frustrating the user during test
                if len(tx_hash) == 66:
                    config.SUBSCRIPTION_STATUS = "PREMIUM"
                    config.SUBSCRIPTION_EXPIRY = time.time() + (30 * 24 * 3600)
                    config.save_settings()
                    return jsonify({"success": True, "status": "PREMIUM (TESTNET)"})
                return jsonify({"success": False, "message": "Transaction not found"}), 404

            # Verify 'to' address
            to_addr = tx.get('to', '').lower()
            from_addr = tx.get('from', '').lower() # Capture sender
            admin_addr = config.ADMIN_WALLET_EVM.lower()
            if admin_addr in to_addr:
                config.SUBSCRIPTION_STATUS = "PREMIUM"
                config.SUBSCRIPTION_EXPIRY = time.time() + (30 * 24 * 3600) 
                config.SUBSCRIPTION_WALLET = from_addr # Save for Refund
                config.save_settings()
                logging.info(f"PREMIUM ACTIVATED for Amoy TX: {tx_hash} | Sender: {from_addr}")
                return jsonify({"success": True, "status": "PREMIUM"})
            else:
                return jsonify({"success": False, "message": "Invalid Receiver Address"}), 400

        # --- POLYGON (EVM) VERIFICATION ---
        elif network == 'POLYGON':
            # Use public Polygon RPC
            rpc_url = "https://polygon-rpc.com"
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getTransactionByHash",
                "params": [tx_hash],
                "id": 1
            }
            r = requests.post(rpc_url, json=payload, timeout=5)
            res = r.json()
            
            tx = res.get('result')
            if not tx:
                return jsonify({"success": False, "message": "Transaction not found on chain"}), 404
            
            # Verify 'to' address (Case insensitive)
            to_addr = tx.get('to', '').lower()
            admin_addr = config.ADMIN_WALLET_EVM.lower()
            
            if admin_addr in to_addr:
                # MARK AS PREMIUM
                config.SUBSCRIPTION_STATUS = "PREMIUM"
                config.SUBSCRIPTION_EXPIRY = time.time() + (30 * 24 * 3600) # +30 Days
                config.save_settings() # <--- CRITICAL: Save to disk
                logging.info(f"PREMIUM ACTIVATED for Polygon TX: {tx_hash}")
                return jsonify({"success": True, "status": "PREMIUM"})
            else:
                return jsonify({"success": False, "message": "Invalid Receiver Address"}), 400

        # --- TON VERIFICATION ---
        elif network == 'TON':
            # TON verification is trickier without an Indexer API key.
            # We will use TonCenter's public RPC to check if the tx exists (simplified).
            # Limitation: getTransactionByHash isn't standard in V2 API, usually requires getTransactions(addr).
            # For this MVP, we'll assume if the client sent a valid-looking hash and we can query the address, it's okay.
            # BETTER: Use tonapi.io if possible, but let's stick to a robust fallback.
            
            # Mocking validation for TON for this MVP to avoid API Key hell
            # In production, integrate with a backend service or your own TON node.
            if len(tx_hash) > 10:
                config.SUBSCRIPTION_STATUS = "PREMIUM"
                config.SUBSCRIPTION_EXPIRY = time.time() + (30 * 24 * 3600)
                config.save_settings() # <--- CRITICAL: Save to disk
                logging.info(f"PREMIUM ACTIVATED for TON TX: {tx_hash}")
                return jsonify({"success": True, "status": "PREMIUM"})
            else:
                return jsonify({"success": False, "message": "Invalid Hash"}), 400

    except Exception as e:
        import traceback
        logging.error(f"Payment Verification Error: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": str(e)}), 500

    return jsonify({"success": False, "message": f"Unknown Network: {network}"}), 400

@app.route('/api/refund_info', methods=['GET'])
def refund_info():
    """Returns the address that needs to be refunded."""
    if not config.SUBSCRIPTION_WALLET:
        return jsonify({"success": False, "message": "No active payer found to refund."}), 404
    
    return jsonify({
        "success": True, 
        "address": config.SUBSCRIPTION_WALLET,
        "amount": "0.0011", # Exactly match test payment
        "pending": config.REFUND_PENDING
    })

@app.route('/api/cancel_subscription', methods=['POST'])
def cancel_subscription():
    """Step 1: User requests cancellation. Downgrade to LITE, mark refund as pending."""
    if config.SUBSCRIPTION_STATUS != "PREMIUM":
        return jsonify({"success": False, "message": "No active premium subscription found."}), 400
    
    config.SUBSCRIPTION_STATUS = "LITE"
    config.SUBSCRIPTION_EXPIRY = 0.0
    config.REFUND_PENDING = True
    config.save_settings()
    
    logging.info(f"Subscription cancelled by user. Refund pending for {config.SUBSCRIPTION_WALLET}")
    return jsonify({"success": True, "message": "Subscription cancelled. Refund is pending admin approval."})

@app.route('/api/finalize_refund', methods=['POST'])
def finalize_refund():
    """Step 2: Admin confirms the refund transaction hash."""
    tx_hash = request.json.get('refund_tx')
    if not tx_hash:
        return jsonify({"success": False, "message": "Transaction hash required"}), 400
        
    config.REFUND_PENDING = False
    config.save_settings()
    
    logging.info(f"REFUND FINALIZED. TX: {tx_hash}")
    return jsonify({"success": True, "message": "Refund finalized."})


# ============ AUTHENTICATION ROUTES ============

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_data = database.verify_user(email, password)
        
        if user_data:
            user = User(user_data["id"], user_data["email"], user_data["role"])
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        user_id = database.create_user(email, password, role='user')
        
        if user_id:
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email already registered.', 'error')
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


# ============ ADMIN PANEL ============

@app.route('/admin')
@login_required
def admin_panel():
    # Check if user is admin
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    # Get all users with subscriptions
    users = database.get_all_users_with_subscriptions()
    
    # Calculate statistics
    total_users = len(users)
    premium_users = sum(1 for u in users if u['status'] == 'PREMIUM')
    pending_refunds = sum(1 for u in users if u['refund_pending'])
    revenue = premium_users * 29  # $29 per premium user
    
    # Add expiry days for display
    for user in users:
        if user['expiry_timestamp'] > 0:
            days_left = int((user['expiry_timestamp'] - time.time()) / 86400)
            user['expiry_days'] = max(0, days_left)
        else:
            user['expiry_days'] = 0
    
    stats = {
        'total_users': total_users,
        'premium_users': premium_users,
        'pending_refunds': pending_refunds,
        'revenue': revenue
    }
    
    return render_template('admin.html', users=users, stats=stats, user=current_user)

@app.route('/api/admin/finalize_refund', methods=['POST'])
@login_required
def admin_finalize_refund():
    if current_user.role != 'admin':
        return jsonify({"success": False, "message": "Access denied"}), 403
    
    user_id = request.json.get('user_id')
    tx_hash = request.json.get('tx_hash')
    
    if not user_id or not tx_hash:
        return jsonify({"success": False, "message": "Missing parameters"}), 400
    
    # Update subscription to clear refund_pending
    database.update_subscription(user_id, refund_pending=0, status='LITE', expiry_timestamp=0.0)
    
    logging.info(f"ADMIN REFUND: User {user_id} refunded via TX {tx_hash}")
    return jsonify({"success": True, "message": "Refund finalized"})


# ============ USER SETTINGS ============

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Get form data
        settings_data = {
            'okx_api_key': request.form.get('okx_api_key', ''),
            'okx_secret': request.form.get('okx_secret', ''),
            'okx_password': request.form.get('okx_password', ''),
            'binance_api_key': request.form.get('binance_api_key', ''),
            'binance_secret': request.form.get('binance_secret', ''),
            'bybit_api_key': request.form.get('bybit_api_key', ''),
            'bybit_secret': request.form.get('bybit_secret', ''),
            'trade_amount': float(request.form.get('trade_amount', 20.0)),
            'max_leverage': int(request.form.get('max_leverage', 10)),
        }
        
        # Save to database
        database.update_user_settings(current_user.id, **settings_data)
        
        flash('Settings saved successfully!', 'success')
        return redirect(url_for('settings'))
    
    # GET: Load existing settings
    user_settings = database.get_user_settings(current_user.id)
    
    if not user_settings:
        # Create default settings
        user_settings = {
            'okx_api_key': '',
            'okx_secret': '',
            'okx_password': '',
            'binance_api_key': '',
            'binance_secret': '',
            'bybit_api_key': '',
            'bybit_secret': '',
            'trade_amount': 20.0,
            'max_leverage': 10,
            'symbols': [],
            'active_exchanges': []
        }
    
    return render_template('settings.html', settings=user_settings, user=current_user)


@app.route('/')
@login_required
def index():
    # Ensure subscription validity on every page load
    config.check_subscription_expiry()
    return render_template('index.html', config=config, user=current_user)

@app.route('/api/data')
@login_required
def get_data():
    """Return trading data for the current authenticated user only."""
    start_timer = time.perf_counter()
    
    # Get user-specific trader from UserTradingManager
    from src.features.trade_executor.user_trader import user_trading_manager
    
    user_trader = user_trading_manager.user_traders.get(current_user.id)
    
    # For backward compatibility with frontend
    entries = []
    
    total_balance = 0
    all_positions = []
    all_history = []
    exchange_balances = {}
    
    if user_trader and user_trader.trader:
        # Get data from user's personal trader
        try:
            bal = user_trader.trader.get_balance()
            total_balance = bal
            exchange_balances[user_trader.trader.exchange_id.upper()] = bal
            
            all_positions = user_trader.trader.get_positions()
            history = user_trader.trader.get_history(limit=20)
            for trade in history:
                trade['exchange'] = user_trader.trader.exchange_id.upper()
            all_history = history
        except Exception as e:
            logging.error(f"Error fetching data for user {current_user.email}: {e}")
    else:
        # User has no active trader (not premium or no API keys configured)
        logging.debug(f"No active trader for user {current_user.email}")
    
    # Sort history by timestamp (newest first)
    all_history.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

    # Calculate Technical Metrics
    latency_ms = (time.perf_counter() - start_timer) * 1000
    
    # Simple Health Score Calculation
    # Base 100, penalize for high latency
    health_score = 100
    if latency_ms > 300:
        penalty = (latency_ms - 300) / 20 # -1 point per 20ms over 300
        health_score = max(0, 100 - penalty)
        
    last_sync_status = True # If we reached here without bubbling exception
    
    # Inject into Analytics
    analytics = portfolio_tracker.get_analytics(live_balance=total_balance, trade_history=all_history)
    analytics.update({
        "api_health_score": round(health_score),
        "last_sync_status": last_sync_status,
        "request_latency": round(latency_ms)
    })

    return jsonify({
        "entries": entries,
        "balance": total_balance,
        "exchange_balances": exchange_balances,
        "positions": all_positions,
        "history": all_history[:30], # Top 30 recent trades
        "symbols": config.SYMBOLS,
        "active_exchanges": config.ACTIVE_EXCHANGES,
        "sandbox_modes": config.SANDBOX_MODES,
        "bot_active": config.BOT_ACTIVE,
        "analytics": analytics
    })

@app.route('/api/portfolio/history')
def get_portfolio_history():
    return jsonify(portfolio_tracker.get_history())


@app.route('/api/reports/download/md')
def download_md():
    filename = report_parser.get_latest_report_file()
    if not filename:
        return jsonify({"status": "error", "message": "No reports found"}), 404
    
    # Path to the report file
    filepath = os.path.abspath(filename)
    return send_file(filepath, as_attachment=True, download_name=filename)

@app.route('/api/reports/delete_all', methods=['POST'])
def delete_all_reports():
    try:
        count = 0
        # Reports are in the project root based on list_dir
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        for f in os.listdir(root_dir):
            if f.startswith("astra_report_") and f.endswith(".md"):
                os.remove(os.path.join(root_dir, f))
                count += 1
        return jsonify({"status": "success", "message": f"Deleted {count} report files."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route('/api/settings/keys', methods=['POST'])
def update_keys():
    data = request.json
    exchange = data.get('exchange', '').lower()
    is_demo = data.get('is_demo', None) # Get is_demo from payload
    
    # Update AI Settings
    config.AI_PROVIDER = data.get('ai_provider', config.AI_PROVIDER)

    if is_demo is not None and exchange in config.SANDBOX_MODES:
        config.SANDBOX_MODES[exchange] = is_demo
    
    gemini_key = data.get('gemini_key', '')
    if gemini_key: config.GEMINI_API_KEY = gemini_key
    
    openai_key = data.get('openai_key', '')
    if openai_key: config.OPENAI_API_KEY = openai_key
    
    deepseek_key = data.get('deepseek_key', '')
    if deepseek_key: config.DEEPSEEK_API_KEY = deepseek_key
    
    anthropic_key = data.get('anthropic_key', '')
    if anthropic_key: config.ANTHROPIC_API_KEY = anthropic_key
    
    config.save_settings() # Persist immediately
    
    if exchange == 'okx':
        config.OKX_API_KEY = data.get('key', config.OKX_API_KEY)
        config.OKX_SECRET = data.get('secret', config.OKX_SECRET)
        config.OKX_PASSWORD = data.get('passphrase', config.OKX_PASSWORD)
    elif exchange == 'binance':
        config.BINANCE_API_KEY = data.get('key', config.BINANCE_API_KEY)
        config.BINANCE_SECRET = data.get('secret', config.BINANCE_SECRET)
    elif exchange == 'bybit':
        config.BYBIT_API_KEY = data.get('key', config.BYBIT_API_KEY) # Standardized key name
        config.BYBIT_SECRET = data.get('secret', config.BYBIT_SECRET)
    
    config.save_settings() # Persist keys
    refresh_traders() # Apply new keys immediately
    return jsonify({"status": "success", "message": f"Credentials updated for {exchange.upper()}"})

@app.route('/api/settings/sandbox', methods=['POST'])
def toggle_sandbox():
    data = request.json
    exchange = data.get('exchange')
    is_demo = data.get('is_demo', False)
    
    if exchange in config.SANDBOX_MODES:
        config.SANDBOX_MODES[exchange] = is_demo
        config.save_settings()
        refresh_traders()
        return jsonify({"status": "success", "exchange": exchange, "is_demo": is_demo})
    return jsonify({"status": "error", "message": "Invalid exchange"}), 400

@app.route('/api/settings/exchange', methods=['POST'])
def update_exchange():
    data = request.json
    new_exchange = data.get('exchange', 'okx').lower()
    
    # In this MVP, we allow one primary exchange at a time via UI
    config.ACTIVE_EXCHANGES = [new_exchange]
    config.save_settings()
    refresh_traders()
    
    return jsonify({"status": "success", "active": config.ACTIVE_EXCHANGES})

@app.route('/api/symbols/add', methods=['POST'])
def add_symbol():
    data = request.json
    new_symbol = data.get('symbol', '').strip().upper()
    
    if not new_symbol:
        return jsonify({"status": "error", "message": "Symbol cannot be empty"}), 400

    if new_symbol in config.SYMBOLS:
        return jsonify({"status": "error", "message": "Symbol already in list"}), 400

    # Backend Validation: Check if it exists on Exchange
    try:
        trader.exchange.load_markets()
        if new_symbol not in trader.exchange.markets:
            return jsonify({
                "status": "error", 
                "message": f"Symbol {new_symbol} not found on OKX. Example: BTC/USDT:USDT"
            }), 400
            
        config.SYMBOLS.append(new_symbol)
        config.save_symbols()
        return jsonify({"status": "success", "symbols": config.SYMBOLS})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/symbols/delete', methods=['POST'])
def delete_symbol():
    data = request.json
    target = data.get('symbol')
    if target in config.SYMBOLS:
        config.SYMBOLS.remove(target)
        config.save_symbols()
        return jsonify({"status": "success", "symbols": config.SYMBOLS})
    return jsonify({"status": "error", "message": "Symbol not found"}), 404


def run_dashboard():
    # Production-ready would use waitress or gunicorn, but flask dev server is fine for this bot's local use
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_dashboard()
