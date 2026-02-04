# Telegram AI Assistant Bot

Полнофункциональный Telegram-бот с интеграцией OpenAI API (GPT-4o, DALL-E 3, Whisper, Sora) и веб-админкой.

## Возможности

### Бот
- **Текстовые запросы**: GPT-4o / GPT-4o-mini с потоковым выводом
- **Генерация изображений**: DALL-E 3 с выбором размера и стиля
- **Генерация видео**: Sora 2 / Sora 2 Pro с асинхронной обработкой
- **Распознавание голоса**: Whisper с авто-обработкой
- **Работа с документами**: PDF, Word, Excel, PowerPoint, изображения
- **Inline-режим**: Быстрые ответы в любом чате
- **Проверка подписки**: Доступ только для подписчиков канала
- **Система лимитов**: Ежедневные лимиты с настройкой

### Админ-панель
- Дашборд со статистикой
- Управление пользователями
- Мониторинг очереди задач
- Настройка лимитов и параметров

## Технологический стек

- **Backend**: Python 3.11+, aiogram 3.x, FastAPI
- **Database**: PostgreSQL, Redis
- **Task Queue**: arq (async Redis queue)
- **Frontend**: React 18, Ant Design, TypeScript
- **Infrastructure**: Docker, Docker Compose

## Быстрый старт (Windows)

### Требования
- Docker Desktop для Windows
- Git

### Установка

1. **Клонируйте репозиторий**:
```bash
git clone <repository-url>
cd telegram-ai-bot
```

2. **Создайте файл .env**:
```bash
copy .env.example .env
```

3. **Настройте переменные окружения** в файле `.env`:
```env
# Обязательно измените!
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHANNEL_ID=-1001234567890
TELEGRAM_CHANNEL_USERNAME=@your_channel
OPENAI_API_KEY=sk-your-openai-api-key
ADMIN_SECRET_KEY=your-super-secret-key-change-in-production
```

4. **Запустите базы данных** (PostgreSQL и Redis):
```bash
docker-compose -f docker-compose.dev.yml up -d
```

5. **Установите Python зависимости**:
```bash
pip install -r requirements.txt
```

6. **Запустите бота**:
```bash
python main.py
```

7. **В отдельном терминале запустите API**:
```bash
python run_api.py
```

8. **В отдельном терминале запустите worker** (для видео):
```bash
python run_worker.py
```

9. **Для админки** (опционально):
```bash
cd admin-frontend
npm install
npm run dev
```

### Доступ к админке
- URL: http://localhost:3000 (или http://localhost:5173 для vite dev)
- Login: admin
- Password: admin123

## Полное развертывание (Docker)

```bash
# Создайте .env файл и настройте переменные
copy .env.example .env

# Запустите все сервисы
docker-compose up -d

# Просмотр логов
docker-compose logs -f bot
docker-compose logs -f api
docker-compose logs -f worker
```

### Доступные сервисы:
- **Bot**: Telegram polling
- **API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Структура проекта

```
telegram-ai-bot/
├── bot/                    # Telegram бот
│   ├── handlers/           # Обработчики сообщений
│   ├── keyboards/          # Клавиатуры
│   ├── middlewares/        # Middleware
│   ├── services/           # Сервисы (OpenAI, users, limits)
│   └── utils/              # Утилиты
├── api/                    # FastAPI админ-панель
│   ├── routers/            # API роутеры
│   ├── schemas/            # Pydantic схемы
│   └── services/           # Сервисы аутентификации
├── worker/                 # Воркер для видео генерации
├── database/               # Модели и подключение к БД
├── admin-frontend/         # React админка
│   ├── src/
│   │   ├── components/     # React компоненты
│   │   ├── pages/          # Страницы
│   │   ├── services/       # API клиент
│   │   └── store/          # Zustand store
├── config/                 # Конфигурация
├── nginx/                  # Nginx конфиг
├── docker-compose.yml      # Docker Compose
├── Dockerfile              # Docker образ
├── requirements.txt        # Python зависимости
├── main.py                 # Точка входа бота
├── run_api.py              # Запуск API
└── run_worker.py           # Запуск воркера
```

## Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather | required |
| `TELEGRAM_CHANNEL_ID` | ID канала для проверки подписки | required |
| `TELEGRAM_CHANNEL_USERNAME` | Username канала (@channel) | required |
| `OPENAI_API_KEY` | API ключ OpenAI | required |
| `DATABASE_URL` | URL подключения PostgreSQL | postgresql+asyncpg://... |
| `REDIS_URL` | URL подключения Redis | redis://localhost:6379/0 |
| `ADMIN_SECRET_KEY` | Секрет для JWT токенов | required |
| `DEFAULT_TEXT_LIMIT` | Лимит текстовых запросов | 50 |
| `DEFAULT_IMAGE_LIMIT` | Лимит изображений | 10 |
| `DEFAULT_VIDEO_LIMIT` | Лимит видео | 3 |
| `DEFAULT_VOICE_LIMIT` | Лимит голосовых | 20 |
| `DEFAULT_DOCUMENT_LIMIT` | Лимит документов | 10 |

### Настройка бота в @BotFather

1. Создайте бота через @BotFather
2. Включите Inline Mode: /setinline
3. Добавьте бота в администраторы канала

## API Endpoints

### Аутентификация
- `POST /api/auth/login` - Вход
- `POST /api/auth/refresh` - Обновление токена
- `GET /api/auth/me` - Текущий админ

### Пользователи
- `GET /api/users` - Список пользователей
- `GET /api/users/{telegram_id}` - Информация о пользователе
- `PATCH /api/users/{telegram_id}` - Обновление пользователя
- `PUT /api/users/{telegram_id}/limits` - Установка лимитов
- `POST /api/users/{telegram_id}/block` - Блокировка
- `POST /api/users/{telegram_id}/message` - Отправка сообщения

### Статистика
- `GET /api/stats/dashboard` - Дашборд
- `GET /api/stats/daily` - Дневная статистика
- `GET /api/stats/recent` - Последние запросы

### Настройки
- `GET /api/settings` - Все настройки
- `PUT /api/settings/limits` - Обновление лимитов
- `PUT /api/settings/bot` - Настройки бота

### Задачи
- `GET /api/tasks/queue/stats` - Статистика очереди
- `GET /api/tasks/queue` - Активные задачи
- `DELETE /api/tasks/queue/{task_id}` - Отмена задачи

## Команды бота

- `/start` - Запуск бота
- `/help` - Справка
- `/new` - Новый диалог (очистка контекста)
- `/image` - Режим генерации изображений
- `/video` - Режим генерации видео
- `/limits` - Показать лимиты
- `/settings` - Настройки

## Разработка

### Запуск тестов
```bash
pytest tests/
```

### Линтинг
```bash
mypy .
```

### Миграции БД (при изменении моделей)
```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

## Лицензия

MIT License
