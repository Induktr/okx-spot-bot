# Спецификация Ошибок

Бот перехватывает исключения библиотеки `ccxt` и выводит человекочитаемые сообщения.

| Тип Исключения | Причина | Действие Бота | Сообщение пользователю |
| :--- | :--- | :--- | :--- |
| `NetworkError` | Обрыв связи, DNS ошибка, Таймаут | **Retry** (3 попытки) | `Connection lost. Retrying in 2s...` |
| `ExchangeNotAvailable` | Биржа на техобслуживании | **Retry** (3 попытки) | `Exchange busy. Retrying...` |
| `AuthenticationError` | Неверные API ключи в `.env` | **Stop** | `ERROR: Invalid API Keys. Check .env file.` |
| `InsufficientFunds` | Не хватает USDT для маржи | **Stop** | `ERROR: Not enough balance.` |
| `BadSymbol` | Указана несуществующая пара | **Stop** | `ERROR: Symbol not found.` |
| `ArgumentsError` | Не передан `--amount` для ордера | **Stop** | (Стандартный вывод argparse) |