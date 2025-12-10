# Сервер управления задачами, документами и событиями с поддержкой Telegram-бота

Этот проект представляет собой легковесный сервер на Flask, который:

- Хранит данные в CSV-файлах (без использования СУБД)
- Поддерживает ролевую модель: `admin`, `manager`, `member`, `viewer`
- Предоставляет RESTful API, управляемое через `routes.yaml`
- Интегрируется с Telegram-ботом для управления через чат
- Имеет модульную структуру: `modules/` — бизнес-логика, `handlers/` — обработка запросов

## Структура проекта

Проект реализован в модульной архитектуре. 

## Хранимые данные

Все данные хранятся в CSV-файлах. Связи между сущностями реализованы через внешние ключи (`*_user_id`), но без механизмов referential integrity на уровне СУБД (проверки выполняются в коде при необходимости).

### 1. `users.csv` — пользователи

Поля:
- `user_id` — первичный ключ (PK)
- `telegram_user_id` — уникальный идентификатор из Telegram
- `telegram_username` — имя пользователя в Telegram (опционально)
- `full_name` — полное имя (опционально)
- `registration_timestamp` — дата регистрации
- `last_login` — дата последнего входа
- `is_active` — флаг активности (`"True"`/`"False"`)
- `role` — роль: `admin`, `manager`, `member`, `viewer`

Только пользователи с ролью `admin` могут получить доступ к API управления пользователями.

### 2. `tasks.csv` — задачи (Kanban)

Поля:
- `task_id` — PK
- `title`, `description` — заголовок и описание
- `status` — `todo`, `in_progress`, `done`
- `assignee_user_id` — FK → `users.user_id` (может быть пустым)
- `creator_user_id` — FK → `users.user_id`
- `created_at`, `updated_at` — временные метки
- `due_date` — дедлайн
- `completed_at` — заполняется автоматически при `status = "done"`
- `priority` — `low`, `medium`, `high`, `urgent`
- `tags` — JSON-массив в виде строки, например: `["backend","urgent"]`

### 3. `docs.csv` — документы

Поля:
- `doc_id` — PK
- `name` — имя документа
- `content` — содержимое или путь к файлу
- `creator_user_id` — FK → `users.user_id`
- `created_at`, `updated_at` — временные метки

### 4. `events.csv` — календарные события

Поля:
- `event_id` — PK
- `title` — название события
- `start`, `end` — дата и время в формате `YYYY-MM-DD HH:MM:SS`
- `creator_user_id` — FK → `users.user_id`
- `created_at` — дата создания записи

## Авторизация

Все API-запросы (кроме `/api/telegram/auth`) должны содержать в теле JSON-поле:

```json
{ "telegram_user_id": 123456789 }
```

Сервер ищет пользователя по `telegram_user_id` в файле `users.csv`. Если пользователь не найден или `is_active != "True"`, возвращается статус `401 Unauthorized`.

Регистрация новых пользователей **не происходит автоматически**. Добавление возможно только через администраторский API (`POST /api/users`) или предварительную инициализацию CSV.

Вот обновлённый раздел **API-эндпоинты** из README с **примером каждого запроса** и **указанием ролей**, которые имеют доступ.

---

## API-эндпоинты

Все API требуют, чтобы в теле запроса (JSON) присутствовало поле `telegram_user_id`, соответствующее зарегистрированному и активному пользователю из `users.csv`.

### 1. Аутентификация

- **Эндпоинт**: `POST /api/telegram/auth`
- **Доступ**: любой пользователь Telegram (но успешен только если `telegram_user_id` уже существует в `users.csv`)
- **Описание**: проверяет существование пользователя; не создаёт новых.
- **Пример запроса**:
  ```bash
  curl -X POST http://localhost:5000/api/telegram/auth \
    -H "Content-Type: application/json" \
    -d '{"user_id": 111111111}'
  ```
- **Успешный ответ (200)**:
  ```json
  {
    "user_id": "1",
    "telegram_user_id": "111111111",
    "telegram_username": "admin_one",
    "role": "admin",
    "is_active": "True"
  }
  ```
- **Ошибка (404)**:
  ```json
  { "error": "User not found or inactive" }
  ```

---

### 2. Управление задачами

#### Список задач
- **Эндпоинт**: `GET /api/tasks`
- **Доступ**: `admin`, `manager`, `member`, `viewer`
- **Пример**:
  ```bash
  curl -X GET http://localhost:5000/api/tasks \
    -H "Content-Type: application/json" \
    -d '{"telegram_user_id": 111111111}'
  ```

#### Создание задачи
- **Эндпоинт**: `POST /api/tasks`
- **Доступ**: `admin`, `manager`, `member` (не `viewer`)
- **Пример**:
  ```bash
  curl -X POST http://localhost:5000/api/tasks \
    -H "Content-Type: application/json" \
    -d '{
      "telegram_user_id": 111111111,
      "title": "Обновить README",
      "description": "Добавить примеры API",
      "priority": "high",
      "tags": ["docs", "api"]
    }'
  ```
- **Ответ (201)**:
  ```json
  { "task_id": 101 }
  ```

#### Обновление задачи
- **Эндпоинт**: `PUT /api/tasks/101`
- **Доступ**: `admin`, `manager`, `member` (не `viewer`)
- **Пример**:
  ```bash
  curl -X PUT http://localhost:5000/api/tasks/101 \
    -H "Content-Type: application/json" \
    -d '{
      "telegram_user_id": 111111111,
      "status": "in_progress"
    }'
  ```

#### Удаление задачи
- **Эндпоинт**: `DELETE /api/tasks/101`
- **Доступ**: `admin`, `manager` (обычно только менеджеры и админы могут удалять)
- **Пример**:
  ```bash
  curl -X DELETE http://localhost:5000/api/tasks/101 \
    -H "Content-Type: application/json" \
    -d '{"telegram_user_id": 111111111}'
  ```

> В текущей реализации **нет проверки роли на удаление** — любой авторизованный пользователь может удалить любую задачу. При необходимости добавьте фильтрацию по `creator_user_id` или роли в `handlers/tasks_delete.py`.

---

### 3. Управление документами

#### Список документов
- **Эндпоинт**: `GET /api/docs`
- **Доступ**: все роли
- **Пример**:
  ```bash
  curl -X GET http://localhost:5000/api/docs \
    -H "Content-Type: application/json" \
    -d '{"telegram_user_id": 111111111}'
  ```

#### Создание документа
- **Эндпоинт**: `POST /api/docs`
- **Доступ**: `admin`, `manager`, `member`
- **Пример**:
  ```bash
  curl -X POST http://localhost:5000/api/docs \
    -H "Content-Type: application/json" \
    -d '{
      "telegram_user_id": 111111111,
      "name": "Отчёт_Q4.txt",
      "content": "Данные за четвертый квартал..."
    }'
  ```

#### Обновление документа
- **Эндпоинт**: `PUT /api/docs/42`
- **Доступ**: `admin`, `manager`, `member`
- **Пример**:
  ```bash
  curl -X PUT http://localhost:5000/api/docs/42 \
    -H "Content-Type: application/json" \
    -d '{
      "telegram_user_id": 111111111,
      "content": "Обновлённые данные..."
    }'
  ```

---

### 4. Управление событиями

#### Список событий
- **Эндпоинт**: `GET /api/calendar/events`
- **Доступ**: все роли
- **Пример**:
  ```bash
  curl -X GET http://localhost:5000/api/calendar/events \
    -H "Content-Type: application/json" \
    -d '{"telegram_user_id": 111111111}'
  ```

#### Создание события
- **Эндпоинт**: `POST /api/calendar/events`
- **Доступ**: `admin`, `manager`, `member`
- **Пример**:
  ```bash
  curl -X POST http://localhost:5000/api/calendar/events \
    -H "Content-Type: application/json" \
    -d '{
      "telegram_user_id": 111111111,
      "title": "Совещание",
      "start": "2025-12-15T10:00:00",
      "end": "2025-12-15T11:00:00"
    }'
  ```

---

### 5. Управление пользователями (админка)

#### Список пользователей
- **Эндпоинт**: `GET /api/users`
- **Доступ**: только `admin`
- **Пример**:
  ```bash
  curl -X GET http://localhost:5000/api/users \
    -H "Content-Type: application/json" \
    -d '{"telegram_user_id": 111111111}'
  ```
- **Если вызван не админом → 403 Forbidden**

#### Создание пользователя
- **Эндпоинт**: `POST /api/users`
- **Доступ**: только `admin`
- **Пример**:
  ```bash
  curl -X POST http://localhost:5000/api/users \
    -H "Content-Type: application/json" \
    -d '{
      "telegram_user_id": 111111111,
      "telegram_user_id_new": 999888777,
      "telegram_username": "ivanov",
      "full_name": "Иван Иванов",
      "role": "member"
    }'
  ```
- **Ответ (201)**:
  ```json
  { "user_id": 1002 }
  ```

> Поле `telegram_user_id` в теле — это ID **админа**, выполняющего запрос. Новые данные передаются через `telegram_user_id_new` и другие поля.

---

### 6. Уведомления в Telegram

- **Эндпоинт**: `POST /api/telegram/notify`
- **Доступ**: внутреннее использование (ботом или системой); в текущей реализации — доступно всем авторизованным
- **Пример**:
  ```bash
  curl -X POST http://localhost:5000/api/telegram/notify \
    -H "Content-Type: application/json" \
    -d '{
      "chat_id": 111111111,
      "message": "Задача #101 завершена!"
    }'
  ```
- **Примечание**: реально отправка в Telegram требует токена бота; сейчас это mock-логирование.

---

Эти примеры можно использовать для ручного тестирования или интеграции с фронтендом/ботом.

## Запуск

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

2. Создайте тестовые данные:
   ```bash
   python test/init_csv.py
   ```
   После создания, перенесите данные папки data/ в корневую папку проекта

3. Запустите сервер:
   ```bash
   python app.py
   ```

4. Протестируйте администратора:
   ```bash
   python test/test_client_admin.py
   ```
   
5. Протестируйте простого пользователя (замените данные что сгенерированы с п.2. в данные пользователя):
   ```bash
   python test/test_client_admin.py
   ```
