import asyncio
import ccxt.async_support as ccxt

async def test():
    ex = ccxt.mexc()
    markets = await ex.load_markets()
    for s in ex.symbols:
        if 'BTC' in s:
            print(f"Знайдено символ: {s}")
    await ex.close()

asyncio.run(test())