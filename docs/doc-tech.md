# Техническая Документация A.S.T.R.A.

### 1. Архитектура: Модульный Монолит

Проект разделен на независимые классы для удобства поддержки и замены компонентов.

```text
astra/
├── core/
│   ├── config.py       # Загрузка .env
│   └── token_guard.py  # Лимитер запросов к API
├── sensors/
│   └── news_aggregator.py # RSS парсер и фильтр
├── brain/
│   └── ai_client.py    # Обертка над Gemini API
├── hands/
│   └── trader.py       # Обертка над CCXT (OKX)
├── scribe/
│   └── logger.py       # Генератор Markdown отчетов
└── main.py             # Планировщик (Scheduler loop)

2. Ключевые Компоненты
TokenGuard (Защитник)
Задача: Считать количество запросов к Gemini.
Логика: Использует паттерн Leaky Bucket или простой счетчик с обнулением каждую минуту. Если лимит исчерпан — принудительная пауза (sleep) или отмена цикла.
NewsAggregator (Сенсор)
Библиотеки: feedparser, beautifulsoup4 (опционально для очистки HTML).
Оптимизация: Собирает только заголовки (title) и краткое описание (summary). Полный текст статей игнорируется для экономии токенов ИИ.
AIClient (Мозг)
Модель: gemini-1.5-flash (выбрана за скорость и дешевизну/бесплатность).
Настройки: temperature=0.2 (нам нужен холодный аналитик, а не поэт).
Scribe (Писарь)
Задача: Вести "Судовой журнал".
Формат: Дописывает (append) события в файл дня. Не перезаписывает файл при перезапуске бота.

---

#### **Файл 4: `docs/DocLogic.md` (Когнитивная Модель)**

```markdown
# Логика Принятия Решений и Промпт-Инжиниринг

### 1. Системный Промпт (The Core Directive)

Это "личность", которую мы загружаем в ИИ перед каждым анализом.

> **Role:** You are ASTRA, a conservative crypto risk manager.
> **Task:** Analyze the provided news headlines for the last 6 hours.
> **Output:** Return ONLY a JSON object. No markdown formatting, no intro text.
> **JSON Structure:**
> ```json
> {
>   "market_sentiment": "Bearish/Neutral/Bullish",
>   "score": 1-10,
>   "decision": "BUY/SELL/WAIT",
>   "reasoning": "Brief explanation (max 20 words)"
> }
> ```
> **Rules:**
> 1. Ignore marketing hype.
> 2. Focus on regulatory news and macroeconomics.
> 3. If unsure, output "WAIT".

### 2. Матрица Решений

Как код интерпретирует ответ ИИ:

| Score (ИИ) | Решение ИИ | Действие Бота (Python) |
| :--- | :--- | :--- |
| 1-3 | SELL | Открыть SHORT (или закрыть LONG) |
| 4-6 | WAIT | Ничего не делать. Логировать анализ. |
| 7-10 | BUY | Открыть LONG (или закрыть SHORT) |

### 3. Цикл Кайдзен (Обучение)

Раз в неделю (Этап 4 Roadmap) ты, как оператор Астры, читаешь `.md` отчеты.
*   Если ИИ купил на хаях — ты корректируешь **Системный Промпт** (например, добавляешь правило: "Будь скептичнее к новостям о листингах").
*   Так система эволюционирует.