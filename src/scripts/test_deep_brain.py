import asyncio
import logging
import sys
import os

# Добавляем корневой путь, чтобы импорты работали
sys.path.append(os.getcwd())

from src.features.sentiment_analyzer.ai_client import ai_client
from src.features.trade_executor.trader import Trader
from src.app.config import config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def test_ai_decision_quality():
    print("\n" + "="*50)
    print("🧠 TESTING ASTRA BRAIN: DECISION & SYMBOL LOGIC")
    print("="*50)

    # 1. Симулируем данные для анализа
    headlines = "[BREAKING] Solana (SOL) network activity hits all-time high. Major institution announces $500M fund for SOL ecosystem. Bullish trend confirmed by key analysts."
    snapshot = "Asset: SOL/USDT | Price: 98.45 | RSI: 54.2 | Trend: Bullish | Volatility: Medium"
    balance = 1000.0

    print("\n--- STEP 1: Requesting AI Analysis ---")
    decision = ai_client.analyze_news(headlines, balance, snapshot, market_mood="Greed")
    
    print(f"AI Response: {decision}")

    # Проверка обязательных полей
    required_fields = ['action', 'target_symbol', 'tp_percent', 'sl_percent', 'sentiment_score']
    missing = [f for f in required_fields if f not in decision]
    
    if not missing:
        print("✅ AI OUTPUT VALID: All mandatory fields present.")
    else:
        print(f"❌ AI OUTPUT INVALID: Missing fields: {missing}")

    # 2. Проверка Трейдера (Символьная логика)
    print("\n--- STEP 2: Testing Symbol Normalization ---")
    try:
        # Инициализируем трейдера (в песочнице, чтобы не тратить деньги)
        trader = Trader(exchange_id='okx')
        
        raw_symbol = decision.get('target_symbol', 'SOL/USDT')
        print(f"Raw Symbol from AI: {raw_symbol}")
        
        # Симулируем выполнение ордера (только до момента проверки символа)
        # Мы используем execute_order, но он может упасть на балансе, 
        # поэтому проверим именно логику внутри trader.py
        
        # Попробуем нормализовать вручную через его логику
        search_term = raw_symbol.split('/')[0].upper()
        print(f"Search term extracted: {search_term}")
        
        # Проверим, находит ли он монету в загруженных рынках
        found = False
        for m_id in trader.exchange.markets:
            if search_term in m_id.upper() and (':USDT' in m_id or '-SWAP' in m_id):
                print(f"✅ Deep Normalization SUCCESS: {raw_symbol} -> {m_id}")
                found = True
                break
        
        if not found:
             print(f"⚠️ Warning: {search_term} not found in first 10 markets: {list(trader.exchange.markets.keys())[:10]}")

    except Exception as e:
        print(f"❌ Trader Test Error: {e}")

    print("\n" + "="*50)
    print("🏁 TEST COMPLETE")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(test_ai_decision_quality())
