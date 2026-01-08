import logging
import telebot
from src.app.config import config

class TelegramProvider:
    """
    Feature 5: Telegram Command Center & Signal Hub.
    Now powered by pyTelegramBotAPI for robust command handling.
    """
    def __init__(self):
        self.token = config.TELEGRAM_TOKEN
        self.chat_id = str(config.TELEGRAM_CHAT_ID)
        self.bot = None
        if self.token:
            try:
                self.bot = telebot.TeleBot(self.token, parse_mode='Markdown')
            except Exception as e:
                logging.error(f"Failed to initialize Telegram Bot: {e}")

    def send_message(self, text, parse_mode="Markdown"):
        if not self.bot or not self.chat_id or not config.TG_SIGNALS_ACTIVE:
            return
            
        try:
            return self.bot.send_message(self.chat_id, text, parse_mode=parse_mode)
        except Exception as e:
            logging.error(f"Telegram Send Error: {e}")
            return None

    def send_emergency_alert(self, event_type, details):
        """Feature 6: Black Swan Alerting."""
        msg = (
            f"🚨 *BLACK SWAN ALERT: {event_type}*\n\n"
            f"⚠️ *DETAILS:* {details}\n"
            f"🛡️ *ACTION:* System entering defensive mode / executing emergency liquidation."
        )
        return self.send_message(msg)

    def send_trade_signal(self, symbol, side, reasoning, score):
        """Feature 5: High-fidelity trade signals (Initial AI Analysis)."""
        emoji = "🔍" if side == "WAIT" else ("🚀" if side == "BUY" else "🔻")
        msg = (
            f"{emoji} *AI SIGNAL: {side} {symbol}*\n\n"
            f"📊 *SCORE:* `{score}/10`\n"
            f"🧠 *REASONING:* _{reasoning}_\n\n"
            f"⚡ _Execution starting..._"
        )
        return self.send_message(msg)

    def send_execution_report(self, symbol, side, results, analytics):
        """Feature 5: Detailed trade execution results with portfolio stats."""
        emoji = "✅" if any("SUCCESS" in r.upper() for r in results) else "⚠️"
        side_emoji = "🟢 LONG" if side == "BUY" else "🔴 SHORT"
        if side == "CLOSE": side_emoji = "⚪ CLOSE"
        
        results_str = "\n".join([f"• {r}" for r in results])
        balance = analytics.get('current_balance', 0)
        profit = analytics.get('total_profit', 0)
        roi = analytics.get('roi_pct', 0)
        p_emoji = "📈" if profit >= 0 else "📉"

        msg = (
            f"{emoji} *TRADE EXECUTED: {symbol}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📝 *ACTION:* `{side_emoji}`\n"
            f"🏦 *EXCHANGES:*\n{results_str}\n\n"
            f"💰 *PORTFOLIO SNAPSHOT:*\n"
            f"💵 *BALANCE:* `${balance:.2f}`\n"
            f"{p_emoji} *PROFIT:* `${profit:+.2f}` (`{roi:+.2f}%`)\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🤖 _A.S.T.R.A. v1.5 Autonomous Core_"
        )
        return self.send_message(msg)

    def setup_commands(self, traders_map, portfolio_tracker):
        """Registers the command handlers."""
        if not self.bot: return

        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            if str(message.chat.id) != self.chat_id: return
            self.bot.reply_to(message, "🛸 *A.S.T.R.A. Command Center Online*\n\n• `/pos` - View active positions\n• `/bal` - Check balance & ROI\n• `/stats` - Detailed analytics\n• `/ping` - Connection test")

        @self.bot.message_handler(commands=['ping'])
        def handle_ping(message):
            if str(message.chat.id) != self.chat_id: return
            self.bot.send_message(message.chat.id, "🏓 *Pong!* System is responsive.")

        @self.bot.message_handler(commands=['pos'])
        def handle_pos(message):
            if str(message.chat.id) != self.chat_id: return
            all_pos = []
            for eid, t in traders_map.items():
                positions = t.get_positions()
                for p in positions:
                    side = p.get('side', 'N/A').upper()
                    emoji = "🟢" if side == "LONG" else "🔴"
                    pnl = float(p.get('unrealizedPnl', 0) or 0)
                    all_pos.append(f"{emoji} *{p['symbol']}*\n   Type: `{side}` | PnL: `{pnl:+.2f} USDT`")
            
            msg = "📊 *CURRENT POSITIONS:*\n\n" + "\n\n".join(all_pos) if all_pos else "🌕 *No active positions.*"
            self.bot.send_message(message.chat.id, msg)

        @self.bot.message_handler(commands=['bal'])
        def handle_bal(message):
            if str(message.chat.id) != self.chat_id: return
            a = portfolio_tracker.get_analytics()
            p_emoji = "📈" if a.get('total_profit', 0) >= 0 else "📉"
            msg = (
                f"💰 *ACCOUNT BALANCE*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"💵 *TOTAL:* `${a.get('current_balance', 0):.2f} USDT`\n"
                f"{p_emoji} *PROFIT:* `${a.get('total_profit', 0):+.2f}` (`{a.get('roi_pct', 0):.2f}%`)\n"
            )
            self.bot.send_message(message.chat.id, msg)

        @self.bot.message_handler(commands=['stats'])
        def handle_stats(message):
            if str(message.chat.id) != self.chat_id: return
            a = portfolio_tracker.get_analytics()
            msg = (
                f"📊 *PERFORMANCE METRICS*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🔥 *PROFIT FACTOR:* `{a.get('profit_factor', 0)}`\n"
                f"🎯 *WIN RATE:* `{a.get('win_rate', 0)}%`\n"
                f"📉 *MAX DRAWDOWN:* `-{a.get('max_drawdown_pct', 0)}%`\n"
                f"🛡️ *KELLY:* `{a.get('kelly_criterion', 0)}%` Size\n"
                f"⚡ *EFFICIENCY:* `{a.get('profit_efficiency', 0)}/hr`"
            )
            self.bot.send_message(message.chat.id, msg)

    def start_polling(self):
        """Enters an infinite polling loop."""
        if self.bot:
            logging.info("Telegram Polling Started...")
            self.bot.infinity_polling()

# Singleton
telegram_bot = TelegramProvider()
