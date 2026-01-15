import logging
import sys
import os

# Добавляем корень проекта в пути
sys.path.append(os.getcwd())

from src.shared.utils.portfolio_tracker import portfolio_tracker
from src.features.trade_executor.trader import traders, refresh_traders
from src.app.config import config

logging.basicConfig(level=logging.INFO, format='%(message)s')

def reset_system():
    print("\n" + "="*50)
    print("🚀 A.S.T.R.A. SYSTEM RESET TOOL")
    print("="*50)
    
    # 1. Получаем актуальный баланс
    print("📡 Подключение к биржам...")
    refresh_traders()
    
    total_bal = 0
    for eid, t in traders.items():
        bal = t.get_balance()
        print(f"💰 Баланс на {eid.upper()}: ${bal}")
        total_bal += bal
    
    if total_bal == 0:
        print("❌ ОШИБКА: Баланс 0. Проверьте ключи API перед сбросом!")
        return

    # 2. Сброс истории
    print(f"\n📝 Обнуление статистики...")
    success = portfolio_tracker.reset_history(total_bal)
    
    if success:
        print(f"✅ УСПЕХ: Вся статистика очищена.")
        print(f"📈 Новая точка отсчета: ${total_bal}")
        print(f"🛡️ Equity Guardian разблокирован.")
    else:
        print("❌ Ошибка при записи файла истории.")

    print("="*50)
    print("Теперь перезапустите бота: sudo systemctl restart astra")
    print("="*50 + "\n")

if __name__ == "__main__":
    reset_system()
