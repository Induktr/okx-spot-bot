---
description: Deployment guide for AWS EC2 (Ubuntu)
---

# Инструкция по деплою A.S.T.R.A. v1.0 на AWS

### 1. Подготовка AWS EC2
- **Instance Type**: минимум `t3.micro` (или `t3.small` для лучшей стабильности).
- **OS**: Ubuntu 22.04 LTS.
- **Security Groups**: 
  - Разрешить **SSH** (порт 22).
  - Разрешить **Custom TCP** (порт 5000) — это для твоего Дашборда.

### 2. Настройка сервера (в терминале AWS)
```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем Python и менеджер процессов
sudo apt install python3-pip python3-venv pm2 -y
```

### 3. Перенос кода
Самый простой способ — через Git (если есть репозиторий) или SCP.
```bash
git clone <твой_репозиторий>
cd A.S.T.R.A. v1.0
```

### 4. Установка окружения
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Запуск в фоновом режиме (через PM2)
Чтобы бот не выключался после закрытия терминала:
```bash
pm2 start main.py --name "astra-bot" --interpreter ./venv/bin/python3
```

### 6. Доступ к дашборду
Заходи через браузер по адресу: `http://<IP_ТВОЕГО_СЕРВЕРА>:5000`
