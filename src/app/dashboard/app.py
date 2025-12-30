from flask import Flask, render_template, jsonify, request, send_file
import os
import sys
import logging

# Add project root to path so we can import shared utils
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.shared.utils.report_parser import report_parser
from src.features.trade_executor.trader import trader, traders, refresh_traders
from src.app.config import config
from src.shared.utils.portfolio_tracker import portfolio_tracker

app = Flask(__name__)

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    entries = report_parser.parse_latest()
    
    total_balance = 0
    all_positions = []
    all_history = []
    exchange_balances = {}
    
    # Aggregate from all active exchanges
    for eid, t in traders.items():
        bal = t.get_balance()
        total_balance += bal
        exchange_balances[eid.upper()] = bal
        
        all_positions.extend(t.get_positions())
        # Fetch latest 20 trades per exchange and tag them
        history = t.get_history(limit=20)
        for trade in history:
            trade['exchange'] = eid.upper()
        all_history.extend(history)
    
    # Sort history by timestamp (newest first)
    all_history.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

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
        "analytics": portfolio_tracker.get_analytics(live_balance=total_balance, trade_history=all_history)
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
