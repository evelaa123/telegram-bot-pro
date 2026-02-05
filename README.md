# Telegram AI Assistant Bot

Полнофункциональный Telegram-бот с интеграцией AI API (OpenAI, CometAPI, GigaChat) и веб-админкой для мониторинга.

## Возможности

### Бот
- **Текстовые запросы**: qwen-3-max через CometAPI с потоковым выводом
- **Генерация изображений**: DALL-E 3 / Qwen через CometAPI
- **Генерация видео**: Sora 2 / Sora 2 Pro с асинхронной обработкой
- **Распознавание голоса**: Whisper через CometAPI
- **Генерация презентаций**: GigaChat + PPTX экспорт
- **Работа с документами**: PDF, Word, Excel, PowerPoint, изображения
- **Личный ассистент**: Ежедневник, напоминания, будильник
- **Inline-режим**: Быстрые ответы в любом чате
- **Проверка подписки**: Доступ только для подписчиков канала
- **Премиум подписка**: 300 руб/мес с расширенными лимитами

### Админ-панель
- Дашборд со статистикой
- **Мониторинг API затрат** (новое!)
- Управление пользователями
- Мониторинг очереди задач
- Настройка лимитов и параметров

## Технологический стек

- **Backend**: Python 3.11+, aiogram 3.x, FastAPI
- **Database**: PostgreSQL, Redis
- **Task Queue**: arq (async Redis queue)
- **Frontend**: React 18, Ant Design, TypeScript
- **Infrastructure**: Docker, Docker Compose
- **AI APIs**: CometAPI, GigaChat, OpenAI

---

## Установка

### Требования

- **Python**: 3.11 или выше
- **Docker**: Docker Desktop (Windows/Mac) или Docker Engine (Linux)
- **Git**: Для клонирования репозитория
- **Node.js**: 18+ (для админ-панели)

### Получение API ключей

Перед установкой получите необходимые API ключи:

1. **Telegram Bot Token**:
   - Откройте @BotFather в Telegram
   - Отправьте `/newbot` и следуйте инструкциям
   - Сохраните полученный токен

2. **CometAPI Key** (для текста/изображений):
   - Зарегистрируйтесь на https://api.cometapi.com
   - Создайте API ключ в консоли (начинается с `sk-`)
   - Документация: https://apidoc.cometapi.com/

3. **GigaChat API** (для презентаций):
   - Зарегистрируйтесь на https://developers.sber.ru/
   - Получите Client ID и Client Secret
   - Scope: `GIGACHAT_API_PERS` (для физлиц)

4. **OpenAI API Key** (опционально, для видео Sora):
   - https://platform.openai.com/api-keys

---

## Вариант 1: Быстрый старт (Разработка)

### Шаг 1: Клонирование репозитория

```bash
git clone https://github.com/evelaa123/telegram-bot-pro.git
cd telegram-bot-pro
```

### Шаг 2: Создание файла конфигурации

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**Linux/Mac:**
```bash
cp .env.example .env
```

### Шаг 3: Настройка переменных окружения

Откройте файл `.env` в текстовом редакторе и заполните:

```env
# === ОБЯЗАТЕЛЬНЫЕ ПАРАМЕТРЫ ===

# Telegram Bot (получить у @BotFather)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHANNEL_ID=-1001234567890
TELEGRAM_CHANNEL_USERNAME=@your_channel

# CometAPI (основной провайдер)
COMETAPI_API_KEY=sk-your-cometapi-key
COMETAPI_BASE_URL=https://api.cometapi.com/v1

# GigaChat (для презентаций)
GIGACHAT_CLIENT_ID=your-client-id
GIGACHAT_CLIENT_SECRET=your-client-secret
GIGACHAT_SCOPE=GIGACHAT_API_PERS

# OpenAI (для видео Sora, опционально)
OPENAI_API_KEY=sk-your-openai-api-key

# Безопасность (ИЗМЕНИТЕ!)
ADMIN_SECRET_KEY=your-super-secret-key-change-in-production

# === ОПЦИОНАЛЬНЫЕ ПАРАМЕТРЫ ===

# База данных (по умолчанию для Docker)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_ai_bot
REDIS_URL=redis://localhost:6379/0

# Лимиты по умолчанию (бесплатная подписка)
DEFAULT_TEXT_LIMIT=10
DEFAULT_IMAGE_LIMIT=5
DEFAULT_VIDEO_LIMIT=5
DEFAULT_VOICE_LIMIT=5
DEFAULT_DOCUMENT_LIMIT=10
DEFAULT_PRESENTATION_LIMIT=3

# Премиум лимиты
PREMIUM_TEXT_LIMIT=100
PREMIUM_IMAGE_LIMIT=50
PREMIUM_VIDEO_LIMIT=20
PREMIUM_VOICE_LIMIT=50
PREMIUM_DOCUMENT_LIMIT=50
PREMIUM_PRESENTATION_LIMIT=20

# Подписка
SUBSCRIPTION_PRICE_RUB=300
```

### Шаг 4: Запуск баз данных

```bash
docker-compose -f docker-compose.dev.yml up -d
```

Проверьте, что контейнеры запущены:
```bash
docker ps
```

Должны быть видны: `postgres` и `redis`

### Шаг 5: Установка Python зависимостей

**Рекомендуется использовать виртуальное окружение:**

```bash
# Создание виртуального окружения
python -m venv venv

# Активация (Windows)
venv\Scripts\activate

# Активация (Linux/Mac)
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

### Шаг 6: Инициализация базы данных

```bash
# Применение миграций
alembic upgrade head
```

### Шаг 7: Запуск компонентов

Откройте **3 отдельных терминала**:

**Терминал 1 - Бот:**
```bash
python main.py
```

**Терминал 2 - API (админ-панель):**
```bash
python run_api.py
```

**Терминал 3 - Worker (видео):**
```bash
python run_worker.py
```

### Шаг 8: Запуск админ-панели (опционально)

```bash
cd admin-frontend
npm install
npm run dev
```

### Доступ к админке

- **URL**: http://localhost:5173
- **Логин**: admin
- **Пароль**: admin123

---

## Вариант 2: Production (Docker Compose)

### Шаг 1: Подготовка

```bash
git clone https://github.com/evelaa123/telegram-bot-pro.git
cd telegram-bot-pro
cp .env.example .env
```

### Шаг 2: Настройка .env

Настройте `.env` как описано выше, но измените:

```env
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/telegram_ai_bot
REDIS_URL=redis://redis:6379/0
```

### Шаг 3: Запуск

```bash
# Сборка и запуск всех сервисов
docker-compose up -d --build

# Просмотр логов
docker-compose logs -f
```

### Шаг 4: Проверка

```bash
# Статус сервисов
docker-compose ps

# Логи конкретного сервиса
docker-compose logs -f bot
docker-compose logs -f api
docker-compose logs -f worker
```

### Доступные сервисы

| Сервис | URL | Описание |
|--------|-----|----------|
| Bot | - | Telegram polling |
| API | http://localhost:8000 | REST API |
| Admin Panel | http://localhost:3000 | Веб-интерфейс |
| PostgreSQL | localhost:5432 | База данных |
| Redis | localhost:6379 | Кэш и очереди |

---

## Настройка Telegram бота

### В @BotFather

1. Отправьте `/mybots` и выберите вашего бота
2. **Bot Settings** → **Inline Mode** → включите
3. **Bot Settings** → **Inline Feedback** → 100%

### Добавление бота в канал

1. Добавьте бота в администраторы канала
2. Дайте права на чтение сообщений
3. Получите ID канала (можно через @getidsbot)

---

## Структура проекта

```
telegram-ai-bot/
├── bot/                    # Telegram бот
│   ├── handlers/           # Обработчики сообщений
│   │   ├── start.py        # /start, /help
│   │   ├── text.py         # Текстовые сообщения
│   │   ├── image.py        # Генерация изображений
│   │   ├── video.py        # Генерация видео
│   │   ├── voice.py        # Голосовые сообщения
│   │   ├── document.py     # Документы
│   │   ├── presentation.py # Презентации
│   │   ├── assistant.py    # Ежедневник, напоминания
│   │   └── settings.py     # Настройки пользователя
│   ├── keyboards/          # Клавиатуры
│   ├── middlewares/        # Middleware
│   ├── services/           # Бизнес-логика
│   │   ├── ai_service.py   # Единый фасад AI
│   │   ├── cometapi_service.py  # CometAPI
│   │   ├── gigachat_service.py  # GigaChat
│   │   ├── openai_service.py    # OpenAI
│   │   ├── presentation_service.py # Презентации
│   │   ├── usage_tracking_service.py # Трекинг
│   │   └── subscription_service.py  # Подписки
│   └── utils/              # Утилиты
├── api/                    # FastAPI админ-панель
│   ├── routers/            # API роутеры
│   │   ├── auth.py         # Аутентификация
│   │   ├── users.py        # Пользователи
│   │   ├── stats.py        # Статистика + API usage
│   │   ├── settings.py     # Настройки
│   │   └── tasks.py        # Задачи
│   ├── schemas/            # Pydantic схемы
│   └── services/           # Сервисы
├── worker/                 # Воркер для видео
├── database/               # БД
│   ├── models.py           # SQLAlchemy модели
│   ├── connection.py       # Подключение
│   └── migrations/         # Alembic миграции
├── admin-frontend/         # React админка
│   └── src/
│       ├── pages/
│       │   ├── DashboardPage.tsx
│       │   ├── ApiUsagePage.tsx   # Мониторинг API
│       │   ├── UsersPage.tsx
│       │   └── SettingsPage.tsx
│       ├── components/
│       └── services/
├── config/                 # Конфигурация
│   └── settings.py         # Pydantic settings
├── docker-compose.yml      # Production
├── docker-compose.dev.yml  # Development
├── requirements.txt        # Python зависимости
├── main.py                 # Точка входа бота
├── run_api.py              # Запуск API
└── run_worker.py           # Запуск воркера
```

---

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Запуск бота |
| `/help` | Справка |
| `/new` | Новый диалог (очистка контекста) |
| `/limits` | Показать лимиты |
| `/settings` | Настройки |

### Режимы работы (через меню)

- **Текст** - Общение с AI
- **Изображения** - Генерация картинок
- **Видео** - Генерация видео
- **Документы** - Анализ документов
- **Презентации** - Создание презентаций
- **Ежедневник** - Личные записи
- **Напоминания** - Напоминания и будильник

---

## API Endpoints

### Статистика и мониторинг

```
GET /api/stats/dashboard        # Общая статистика
GET /api/stats/api-usage        # Мониторинг API затрат
GET /api/stats/api-usage/daily  # Дневная разбивка
GET /api/stats/api-usage/monthly # Месячная сводка
GET /api/stats/api-usage/alerts  # Алерты бюджета
```

### Пользователи

```
GET    /api/users                    # Список
GET    /api/users/{telegram_id}      # Детали
PATCH  /api/users/{telegram_id}      # Обновление
PUT    /api/users/{telegram_id}/limits # Лимиты
POST   /api/users/{telegram_id}/block  # Блокировка
```

### Настройки

```
GET /api/settings         # Все настройки
PUT /api/settings/limits  # Лимиты
PUT /api/settings/bot     # Настройки бота
```

---

## Решение проблем

### Бот не отвечает

1. Проверьте токен бота в `.env`
2. Проверьте логи: `docker-compose logs bot`
3. Убедитесь, что Redis запущен

### Ошибки базы данных

```bash
# Пересоздание базы
docker-compose down -v
docker-compose up -d
alembic upgrade head
```

### API не отвечает

1. Проверьте ключи API в `.env`
2. Проверьте баланс на CometAPI/GigaChat
3. Смотрите логи: `docker-compose logs api`

### Админка не загружается

```bash
cd admin-frontend
rm -rf node_modules
npm install
npm run dev
```

---

## Разработка

### Запуск тестов

```bash
pytest tests/
```

### Линтинг

```bash
mypy .
```

### Миграции БД

```bash
# Создание новой миграции
alembic revision --autogenerate -m "Description"

# Применение миграций
alembic upgrade head

# Откат
alembic downgrade -1
```

---

## Лицензия

MIT License
