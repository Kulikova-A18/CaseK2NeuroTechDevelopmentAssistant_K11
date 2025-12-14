
## Описание основных компонентов:

### 1. **SystemConstants**
Класс содержит все константы системы: роли, статусы задач, приоритеты, пути к файлам и т.д.

### 2. **Pydantic модели (UserBase, TaskBase, AuthRequest и др.)**
- Обеспечивают валидацию входящих данных
- Автоматически проверяют типы данных и ограничения
- Преобразуют данные в Python объекты

### 3. **ConfigManager**
- Загружает конфигурацию из YAML файла
- Заменяет переменные окружения `${VAR}` на реальные значения
- Предоставляет доступ к настройкам через метод `get()`
- Если `security.enabled: false`, все пользователи получают права администратора

### 4. **CSVDataManager**
- Потокобезопасная работа с CSV файлами
- Поддерживает CRUD операции
- Валидирует данные по схеме

### 5. **CacheManager**
- Использует Redis для кэширования
- При недоступности Redis переходит на in-memory кэш
- Генерирует ключи кэша на основе параметров

### 6. **AuthManager**
- Управляет аутентификацией через JWT токены
- Проверяет права пользователей
- Если безопасность отключена, все пользователи получают полные права

### 7. **Декораторы**
- `@require_auth` - проверяет валидность токена
- `@require_permission` - проверяет конкретное право
- `@validate_request` - валидирует JSON тело запроса с помощью Pydantic

### 8. **API эндпоинты**
- `/api/telegram/auth` - аутентификация
- `/api/tasks` - получение и создание задач
- `/api/tasks/<id>` - обновление задачи
- `/api/export/tasks.csv` - экспорт в CSV
- `/api/llm/analyze/tasks` - демо-анализ LLM
- `/api/users` - создание пользователей
- `/api/health` - проверка здоровья системы

### 9. **WebSocket обработчики**
- Реальное обновление Kanban доски
- Подписка на каналы (tasks, events)
- Автоматические уведомления при изменениях

## Инструкция по запуску:

1. **Установите зависимости:**
```bash
pip install -r requirements.txt
```

2. **Запустите Redis (опционально, для кэширования):**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Mac
brew install redis
brew services start redis
```

3. **Запустите сервер:**
```bash
python app.py
```

4. **Протестируйте API:**
```bash
# Проверка здоровья
curl http://localhost:5000/api/health

# Аутентификация
curl -X POST http://localhost:5000/api/telegram/auth \
  -H "Content-Type: application/json" \
  -d '{"telegram_username": "@developer_alex"}'

# Получение задач (используйте токен из предыдущего запроса)
curl -X GET http://localhost:5000/api/tasks \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

Система готова к использованию! При `security.enabled: false` все пользователи имеют полные права администратора.

# .env

удалить 00000 в  TELEGRAM_BOT_TOKEN

```
# .env
# Переменные окружения для системы управления задачами

# Секретный ключ для JWT токенов
JWT_SECRET=your-super-secret-jwt-key-change-in-production

# Токен Telegram бота (HTTP API)
TELEGRAM_BOT_TOKEN=000008521671675:AAGHlyyyx59TWb3RBVD-l6hAlnP0kHg03lU00000

# Ключ OpenAI API (не используется в демо-режиме)
OPENAI_API_KEY=your-openai-api-key-here

# Настройки Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Настройки базы данных (если будет использоваться SQL)
DATABASE_URL=sqlite:///./data/task_system.db

```
