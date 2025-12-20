import os
import ccxt.async_support as ccxt
from dotenv import load_dotenv
import time

load_dotenv()

class MEXCClient:
    def __init__(self):
        self.api_key = os.getenv('MEXC_API_KEY')
        self.api_secret = os.getenv('MEXC_SECRET_KEY')

        if not self.api_key or not self.api_secret:
            raise ValueError("Error: MEXC_API_KEY and MEXC_SECRET_KEY not found in .env file")

        self.exchange = ccxt.mexc({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'timeout': 30000,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',
            },
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        })

    async def prepare(self):
        print("🔄 Завантаження ринків (підготовка)...")
        await self.exchange.load_markets()
        print("✅ Ринки завантажені.")

    async def open_long(self, symbol: str, quote_amount: float):
        """Opens a long position (market buy order)."""
        start_time = time.time()
        try:
            if (time.time() - start_time) > 2:
                print("❌ Помилка: Перевищено ліміт часу (2 сек) перед відправкою!")
                return

            sl = symbol.upper()

            # Add Market Check
            market = self.exchange.market(symbol)
            print(f"📊 Market limits for {symbol}: {market['limits']}")

            # Ensure it's a futures or swap market (often used for perpetual futures)
            if market['type'] not in ['future', 'swap']:
                print(f"❌ Error: {symbol} is not a futures or swap contract. Market type is {market['type']}.")
                return

            # Fetch ticker to get current price for calculating base amount
            ticker = await self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            print(f"📈 Current price of {symbol}: {current_price}")

            # Calculate base amount from the provided quote_amount (e.g., 5 USDT)
            if current_price == 0:
                print("❌ Error: Current price is zero, cannot calculate trade amount.")
                return

            base_amount = quote_amount / current_price
            print(f"💰 User requested to trade {quote_amount} (quote currency). Calculated base amount: {base_amount} {market['base']}.")

            # Amount Precision
            formatted_base_amount = self.exchange.amount_to_precision(symbol, base_amount)
            print(f"💎 Original base amount: {base_amount}, Formatted base amount: {formatted_base_amount}")

            if formatted_base_amount is None:
                print("❌ Error: Could not format amount to precision.")
                return

            try:
                # Set leverage for isolated margin, long position
                await self.exchange.set_leverage(10, symbol, params={'openType': 1, 'positionType': 1})
                print(f"⚙️ Плече x10 встановлено для {symbol}")
            except Exception as e:
                print(f"⚠️ Could not set leverage to 10 for {symbol}, proceeding (e.g. already set): {e}")

            order = await self.exchange.create_order(
                symbol=symbol,
                type='market',
                side='buy',
                amount=float(formatted_base_amount),
                price=None,
                params={
                    'positionSide': 'LONG'
                }
            )

            order_id = order.get('id')
            status = order.get('status')

            execution_time = time.time() - start_time
            print(f"✅ SUCCESS! Ордер {order['id']} виконано за {execution_time:.2f} сек.")

            print(f"\nSuccess! Purchase order completed!")
            print(f"Order ID: {order_id}")
            print(f"Status: {status}")
            print(f"Couple: {sl}")
            print(f"Quantity (cost in quote currency): {quote_amount}\n") # Display quote amount as quantity

        except ccxt.AuthenticationError:
            print("Authorization error. Check the keys in .env")
        except ccxt.InsufficientFunds:
            print("Insufficient funds for the operation.")
        except ccxt.BadSymbol:
            print("Trading pair not found. Please use the BASE/QUOTE format.")
        except ccxt.NetworkError:
            print("Network error. Check your connection.")
        except Exception as e:
            print(f"Error opening position: {str(e)}")

    async def open_short(self, symbol: str, quote_amount: float):
        """Opens a short position (market sell order)."""
        start_time = time.time()
        try:
            sl = symbol.upper()

            market = self.exchange.market(symbol)
            print(f"📊 Market limits for {symbol}: {market['limits']}")

            if market['type'] not in ['future', 'swap']:
                print(f"❌ Error: {symbol} is not a futures or swap contract. Market type is {market['type']}.")
                return

            ticker = await self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            print(f"📈 Current price of {symbol}: {current_price}")
            if current_price == 0:
                print("❌ Error: Current price is zero, cannot calculate trade amount.")
                return

            base_amount = quote_amount / current_price
            print(f"💰 User requested to trade {quote_amount} (quote currency). Calculated base amount: {base_amount} {market['base']}.")

            formatted_base_amount = self.exchange.amount_to_precision(symbol, base_amount)
            print(f"💎 Original base amount: {base_amount}, Formatted base amount: {formatted_base_amount}")

            if formatted_base_amount is None:
                print("❌ Error: Could not format amount to precision.")
                return

            try:
                await self.exchange.set_leverage(10, symbol, params={'openType': 1, 'positionType': 2})
                print(f"⚙️ Плече x10 встановлено для {symbol}")
            except Exception as e:
                print(f"⚠️ Could not set leverage to 10 for {symbol}, proceeding (e.g. already set): {e}")
            print(f"DEBUG: Creating order: symbol={symbol}, type=market, side=sell, amount={formatted_base_amount}, params={{'positionSide': 'SHORT'}}")
            order = await self.exchange.create_order(
                symbol=symbol,
                type='market',
                side='sell',
                amount=float(formatted_base_amount),
                price=None,
                params={
                    'positionSide': 'SHORT'
                }
            )

            order_id = order.get('id')
            status = order.get('status')

            execution_time = time.time() - start_time
            print(f"✅ SUCCESS! Ордер {order['id']} виконано за {execution_time:.2f} сек.")

            print(f"\nSuccess! The sell order has been executed!")
            print(f"Order ID: {order_id}")
            print(f"Status: {status}")
            print(f"Couple: {sl}")
            print(f"Quantity (cost in quote currency): {quote_amount}\n")

        except ccxt.AuthenticationError:
            print("Authorization error. Check the keys in .env")
        except ccxt.InsufficientFunds:
            print("Insufficient funds for the operation.")
        except ccxt.BadSymbol:
            print("Trading pair not found. Please use the BASE/QUOTE format.")
        except ccxt.NetworkError:
            print("Network error. Check your connection.")
        except Exception as e:
            print(f"Error opening position: {str(e)}")

    async def close_position(self, symbol: str):
        """Closes an existing position by creating an opposite market order."""
        try:
            positions = await self.exchange.fetch_positions([symbol])

            target_position = None
            for pos in positions:
                if pos['symbol'] == symbol and pos['contracts'] is not None and float(pos['contracts']) > 0:
                    target_position = pos
                    break

            if not target_position:
                print(f"❌ No open positions found for {symbol}")
                return

            side = target_position['side']
            amount = float(target_position['contracts'])

            market = self.exchange.market(symbol)
            print(f"📊 Market limits for {symbol}: {market['limits']}")

            if market['type'] not in ['future', 'swap']:
                print(f"❌ Error: {symbol} is not a futures or swap contract. Market type is {market['type']}.")
                return

            formatted_amount = self.exchange.amount_to_precision(symbol, amount)
            print(f"💎 Original contracts: {amount}, Formatted contracts: {formatted_amount}")

            if formatted_amount is None:
                print("❌ Error: Could not format amount to precision.")
                return

            action_side = 'sell' if side == 'long' else 'buy'
            position_side = 'LONG' if side == 'long' else 'SHORT'

            print(f"📉 Closing {side.upper() if side else 'UNKNOWN'} position: {action_side.upper()} {formatted_amount} {symbol}...")

            order = await self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=action_side,
                amount=float(formatted_amount),
                params={
                    'reduceOnly': True,
                    'positionSide': position_side
                }
            )

            print(f"✅ Position closed! Order ID: {order['id']}")

        except ccxt.AuthenticationError:
            print("Authorization error. Check the keys in .env")
        except ccxt.InsufficientFunds:
            print("Insufficient funds for the operation.")
        except ccxt.BadSymbol:
            print("Trading pair not found. Please use the BASE/QUOTE format.")
        except ccxt.NetworkError:
            print("Network error. Check your connection.")
        except Exception as e:
            print(f"Error closing position: {str(e)}")
