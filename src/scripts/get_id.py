
import telebot
import os
import sys
import time

# Добавляем путь, чтобы скрипт видел конфиг
sys.path.append(os.getcwd())
try:
    from src.app.config import config
except ImportError:
    print("❌ Запустите скрипт из корня проекта: python src/scripts/get_id.py")
    sys.exit(1)

def get_id_v3():
    token = config.TELEGRAM_TOKEN
    if not token or ":" not in token:
        print("❌ ОШИБКА: TELEGRAM_TOKEN в .env пустой или неверный!")
        return

    bot = telebot.TeleBot(token)
    print("\n" + "🔍" * 15)
    print(" ПРОВЕРКА ОБНОВЛЕНИЙ...")
    print("🔍" * 15)
    
    print("\n1. Бот запущен. Ожидаю активности...")
    print("2. Прямо СЕЙЧАС отправьте любое сообщение в канал.")
    print("3. Также попробуйте УДАЛИТЬ бота из канала и ДОБАВИТЬ СНОВА.")
    print("-" * 30)

    # Принудительная проверка последних обновлений
    try:
        updates = bot.get_updates(timeout=10)
        if updates:
            for u in updates:
                chat = None
                if u.message: chat = u.message.chat
                elif u.channel_post: chat = u.channel_post.chat
                elif u.my_chat_member: chat = u.my_chat_member.chat
                
                if chat:
                    print(f"\n✨ ЧАТ НАЙДЕН!")
                    print(f"Тип: {chat.type}")
                    print(f"Название: {chat.title}")
                    print(f"CHAT ID: {chat.id}")
                    print(f"✅ Скопируйте это в .env: TELEGRAM_CHAT_ID={chat.id}")
                    return

        # Если ничего не нашли, запускаем слушателя
        @bot.channel_post_handler(func=lambda m: True)
        def handle_post(m):
            print(f"\n✅ ПОЙМАЛИ ИЗ КАНАЛА!")
            print(f"ID: {m.chat.id}")
            os._exit(0)

        @bot.my_chat_member_handler(func=lambda m: True)
        def handle_add(m):
            print(f"\n✅ ПОЙМАЛИ ДОБАВЛЕНИЕ!")
            print(f"ID: {m.chat.id}")
            os._exit(0)

        print("...слушаю эфир (нажмите Ctrl+C для выхода)...")
        bot.polling(non_stop=True)

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    get_id_v3()
