# Подробная инструкция по установке на Windows

## Требования

### Обязательное ПО

1. **Python 3.11+**
   - Скачайте с [python.org](https://www.python.org/downloads/)
   - При установке обязательно отметьте "Add Python to PATH"
   - Проверка: `python --version`

2. **Docker Desktop для Windows**
   - Скачайте с [docker.com](https://www.docker.com/products/docker-desktop)
   - Требуется WSL2 (Windows Subsystem for Linux 2)
   - После установки перезагрузите компьютер
   - Проверка: `docker --version`

3. **Git**
   - Скачайте с [git-scm.com](https://git-scm.com/download/win)
   - Проверка: `git --version`

4. **Node.js 18+** (для админ-панели)
   - Скачайте с [nodejs.org](https://nodejs.org/)
   - Выберите LTS версию
   - Проверка: `node --version` и `npm --version`

### Получение API ключей

1. **Telegram Bot Token**
   - Откройте [@BotFather](https://t.me/BotFather) в Telegram
   - Отправьте `/newbot`
   - Следуйте инструкциям
   - Сохраните полученный токен

2. **OpenAI API Key**
   - Зарегистрируйтесь на [platform.openai.com](https://platform.openai.com/)
   - Перейдите в API Keys
   - Создайте новый ключ
   - Пополните баланс (минимум $5)

3. **Channel ID**
   - Создайте канал в Telegram (если нет)
   - Добавьте бота в администраторы канала
   - Перешлите любое сообщение из канала боту [@userinfobot](https://t.me/userinfobot)
   - Скопируйте ID (отрицательное число вроде -1001234567890)

## Пошаговая установка

### Шаг 1: Клонирование проекта

```cmd
cd C:\Projects
git clone <repository-url> telegram-ai-bot
cd telegram-ai-bot
```

### Шаг 2: Настройка .env файла

```cmd
copy .env.example .env
notepad .env
```

Заполните обязательные поля:

```env
# Telegram
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHANNEL_ID=-1001234567890
TELEGRAM_CHANNEL_USERNAME=@your_channel

# OpenAI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxx

# Security
ADMIN_SECRET_KEY=your-super-secret-key-at-least-32-characters
```

### Шаг 3: Запуск баз данных

```cmd
docker-compose -f docker-compose.dev.yml up -d
```

Проверьте, что контейнеры запустились:
```cmd
docker ps
```

Должны быть: `telegram_ai_postgres` и `telegram_ai_redis`

### Шаг 4: Создание виртуального окружения

```cmd
python -m venv venv
venv\Scripts\activate
```

### Шаг 5: Установка зависимостей

```cmd
pip install -r requirements.txt
```

### Шаг 6: Инициализация базы данных

```cmd
python scripts/init_db.py
```

### Шаг 7: Запуск бота

**Терминал 1 - Бот:**
```cmd
cd C:\Projects\telegram-ai-bot
venv\Scripts\activate
python main.py
```

**Терминал 2 - API:**
```cmd
cd C:\Projects\telegram-ai-bot
venv\Scripts\activate
python run_api.py
```

**Терминал 3 - Worker (для видео):**
```cmd
cd C:\Projects\telegram-ai-bot
venv\Scripts\activate
python run_worker.py
```

### Шаг 8: Запуск админ-панели (опционально)

**Терминал 4:**
```cmd
cd C:\Projects\telegram-ai-bot\admin-frontend
npm install
npm run dev
```

Откройте http://localhost:5173 в браузере.

## Проверка работоспособности

1. **Откройте бота** в Telegram
2. **Отправьте /start**
3. **Если просит подписку** - подпишитесь на канал и нажмите "Я подписался"
4. **Попробуйте** отправить текстовое сообщение

## Возможные проблемы

### Docker не запускается
- Убедитесь, что Docker Desktop запущен
- Проверьте WSL2: `wsl --status`
- Перезагрузите Docker Desktop

### Ошибка "Module not found"
- Убедитесь, что виртуальное окружение активировано
- Переустановите зависимости: `pip install -r requirements.txt`

### Ошибка подключения к PostgreSQL
- Проверьте контейнеры: `docker ps`
- Проверьте логи: `docker logs telegram_ai_postgres`

### Ошибка "Telegram API: Bad Request"
- Проверьте правильность токена бота
- Проверьте, что ID канала указан с минусом

### Бот не отвечает
- Проверьте логи в терминале с ботом
- Убедитесь, что OpenAI API key действителен
- Проверьте баланс OpenAI

## Быстрые команды

### Остановка всех сервисов
```cmd
docker-compose -f docker-compose.dev.yml down
```

### Просмотр логов PostgreSQL
```cmd
docker logs -f telegram_ai_postgres
```

### Просмотр логов Redis
```cmd
docker logs -f telegram_ai_redis
```

### Сброс баз данных (осторожно!)
```cmd
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d
python scripts/init_db.py
```

## Полезные советы

1. **Используйте Windows Terminal** для удобной работы с несколькими терминалами
2. **Создайте ярлыки** для частых команд
3. **Настройте автозапуск Docker Desktop** через Windows Settings
4. **Используйте VS Code** с расширениями Python и Docker

## Структура терминалов для разработки

| Терминал | Команда | Назначение |
|----------|---------|------------|
| 1 | `python main.py` | Telegram бот |
| 2 | `python run_api.py` | FastAPI сервер |
| 3 | `python run_worker.py` | Worker для видео |
| 4 | `npm run dev` | Admin frontend |

## Следующие шаги

1. Настройте Inline Mode в @BotFather (`/setinline`)
2. Добавьте описание бота (`/setdescription`)
3. Настройте команды (`/setcommands`)
4. Создайте первого админа в админ-панели
