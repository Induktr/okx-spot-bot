---
description: Полное руководство по деплою A.S.T.R.A. v1.5 (Media Core + Trading) на AWS EC2
---

# Мануал по переносу A.S.T.R.A. v1.5 на AWS (Ubuntu Free Tier)

Этот план рассчитан на использование бесплатного `t2.micro` или `t3.micro` (Free Tier).

## 1. Подготовка Инстанса (AWS Console)
1.  **Launch Instance**:
    *   **OS**: Ubuntu Server 22.04 LTS (HVM), SSD Volume Type.
    *   **Architecture**: x86_64.
    *   **Instance Type**: `t3.micro` (рекомендуется) или `t2.micro`.
    *   **Key Pair**: Создай новый `.pem` ключ (назови, например, `astra-key.pem`) и скачай его.
2.  **Network Settings (Security Groups)**:
    *   Создай новую группу.
    *   **Inbound Rules (Входящие)**:
        *   `SSD` (Port 22): Source `My IP` (для безопасности) или `Anywhere`.
        *   `Custom TCP` (Port 5000): Source `Anywhere` (0.0.0.0/0) — **ДЛЯ ДАШБОРДА**.
3.  **Storage**: Увеличь до **25-30 GB** (бесплатно дают до 30GB, а для видео/логов место нужно).

---

## 2. Подключение к серверу
В Windows терминале (PowerShell), находясь в папке с ключом:
```powershell
# Устанавливаем права на ключ (для Linux/Mac это chmod 400, для Windows иногда нужно через свойства файла, но OpenSSH в Windows 10+ обычно справляется)
ssh -i "path/to/key.pem" ubuntu@<PUBLIC_IP_ADDRESS>
```

---

## 3. Настройка Системного Окружения (Внутри сервера)
Media Core требует `ffmpeg` для обработки видео.

```bash
# 1. Обновляем пакеты
sudo apt update && sudo apt upgrade -y

# 2. Ставим Python, Pip, Venv и FFmpeg (Критично для ТikTok видео!)
sudo apt install python3-pip python3-venv ffmpeg -y

# 3. (Опционально) Ставим PM2 для удобного управления процессами
sudo apt install nodejs npm -y
sudo npm install pm2 -g
```

---

## 4. Перенос Файлов
Т.к. мы добавили `.env` и `data/` в `.gitignore`, просто `git clone` **недостаточно**.

### Вариант А: Git Clone (Код) + Ручное создание секретов (Безопасно)
1.  Сделай коммит и пуш своего кода в **Private** репозиторий GitHub.
2.  На сервере:
    ```bash
    git clone https://<YOUR_TOKEN>@github.com/<USER>/<REPO>.git astra_bot
    cd astra_bot
    ```
3.  **Создай .env файл вручную**:
    ```bash
    nano .env
    # (Вставь содержимое своего локального .env файла сюда)
    # Нажми Ctrl+O (Enter) для сохранения, Ctrl+X для выхода
    ```
4.  **Создай папку для ключей (если используешь json)**:
    ```bash
    mkdir -p data
    nano data/settings.json
    # (Копируй содержимое settings.json)
    ```

### 4.5 ПЕРЕНОС СЕССИИ (Критично для TikTok/Instagram)
Т.к. на сервере нет экрана (GUI), вы не сможете нажать кнопку "Войти" в браузере.
1.  **Локально на Windows**: Запустите бота, выберите TikTok, выполните вход в открывшемся окне.
2.  **Проверьте**: В папке `data/` должен появиться файл `tiktok_cookies.json` (и `ig_settings.json` для Instagram).
3.  **Перенесите файлы на сервер** (из локального PowerShell):
    ```powershell
    scp -i "hunter-key.pem" data/tiktok_cookies.json ubuntu@<IP_AWS>:/home/ubuntu/astra_bot/data/
    scp -i "hunter-key.pem" data/ig_settings.json ubuntu@<IP_AWS>:/home/ubuntu/astra_bot/data/
    ```

### Вариант Б: SCP (Копирование файлов напрямую с Windows)
Если лень возиться с гитом, копируем папку (кроме venv и мусора):
В **локальном PowerShell** (не в SSH):
```powershell
# Пример копирования всей папки проекта (потребует времени)
scp -i "key.pem" -r "c:\Users\USER\Documents\projects\ai-bots\A.S.T.R.A v1.5" ubuntu@<IP>:/home/ubuntu/astra_bot
```
*Минус: скопируется всё подряд, лучше исключить `venv`.*

---

## 5. Установка зависимостей Python
На сервере (в папке проекта):

```bash
# 1. Создаем виртуальное окружение
python3 -m venv venv

# 2. Активируем
source venv/bin/activate

# 3. Обновляем pip
pip install --upgrade pip

# 4. Ставим зависимости
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 5. Установка браузеров (для TikTok)
# Это обязательно для работы Playwright на сервере
playwright install chromium
sudo playwright install-deps
```

---

## 6. Финальная настройка прав
Для работы с медиа (сохранение видео, логов):
```bash
# Создаем нужные директории если их нет
mkdir -p src/data/media_assets src/data/marketing_outputs output logs

# Даем права на запись (на всякий случай)
chmod -R 755 src/data output logs
```

---

## 7. Запуск (Production Mode)

### Способ с PM2 (Рекомендуется, авто-перезапуск при падении)
```bash
# Запуск из папки проекта, используя python из venv
pm2 start main.py --name "astra-core" --interpreter ./venv/bin/python3

# Просмотр логов
pm2 logs astra-core

# Сохранение списка процессов для автозапуска после перезагрузки сервера
pm2 save
pm2 startup
```

### Проверка работы
1.  Открой в браузере: `http://<IP_АДРЕСА_AWS>:5000`
2.  Если дашборд открылся — поздравляю, мы в эфире! 🚀

---

## Полезные команды
- `pm2 status` — статус бота.
- `pm2 restart astra-core` — перезапуск (после изменения кода).
- `htop` — мониторинг нагрузки CPU/RAM (следи, чтобы t3.micro не захлебнулся при рендере видео).
