import os
import time
import asyncio
import ccxt.async_support as ccxt
from dotenv import load_dotenv

class MEXCClient:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('MEXC_API_KEY')
        self.api_secret = os.getenv('MEXC_SECRET_KEY')

        if not self.api_key or not self.api_secret:
            raise ValueError("Error: API keys not found in .env file")

        self.exchange = ccxt.mexc({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'timeout': 2000,
            'options': {'defaultType': 'swap'},
            'enableRateLimit': True
        })

    async def prepare(self):
        await self.exchange.load_markets()

    async def open_long(self, symbol: str, quantity_in_coins: float):
        try:
            market_info = self.exchange.market(symbol)
            contract_size = market_info['info']['contractSize']
            num_contracts = int(quantity_in_coins / float(contract_size))

            try:
                await self.exchange.set_leverage(10, symbol, {'openType': 1, 'positionType': 1})
            except: pass

            params = {
                'side': 1,
                'openType': 1,
                'type': 5,
                'leverage': 10,
                'positionSide': 'LONG'
            }

            order = await self.exchange.create_order(
                symbol=symbol,
                type='market',
                side='buy',
                amount=num_contracts,
                params=params
            )
            print(f"✅ SUCCESS! Long ID: {order['id']}")
            return order
        except Exception as e:
            print(f"❌ API Error: {str(e)}")

    async def open_short(self, symbol: str, quantity_in_coins: float):
        try:
            market_info = self.exchange.market(symbol)
            contract_size = market_info['info']['contractSize']
            num_contracts = int(quantity_in_coins / float(contract_size))
    
            try:
                await self.exchange.set_leverage(10, symbol, {'openType': 1, 'positionType': 1})
            except: pass

            params = {
                'side': 2,
                'openType': 1,
                'type': 5,
                'leverage': 10,
                'positionSide': 'SHORT'
            }

            order = await self.exchange.create_order(
                symbol=symbol,
                type='market',
                side='sell',
                amount=num_contracts,
                params=params
            )
            print(f"✅ SUCCESS! Short ID: {order['id']}")
            return order
        except Exception as e:
            print(f"❌ API Error: {str(e)}")

    async def close_position(self, symbol: str):
        try:
            positions = await self.exchange.fetch_positions([symbol])
            active_pos = next((p for p in positions if float(p['contracts']) > 0), None)

            if not active_pos:
                print(f"❌ No active position for {symbol}")
                return

            side = active_pos['side']
            amount = int(active_pos['contracts'])

            close_side_code = 4 if side == 'LONG' else 3
            
            params = {
                'side': close_side_code, 
                'openType': 1,
                'type': 5,
                'positionSide': side
            }

            order = await self.exchange.create_order(
                symbol=symbol,
                type='market',
                side='sell' if side == 'LONG' else 'buy',
                amount=amount,
                params=params
            )
            print(f"✅ FLASH CLOSED! {side} position for {symbol} closed.")
        except Exception as e:
            print(f"❌ Close Error: {str(e)}")