# Docker развертывание проекта

## Предварительные требования

1. Установите Docker и Docker Compose:
   ```bash
   # Для Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install docker.io docker-compose
   sudo usermod -aG docker $USER
   
   # Перезайдите в систему для применения изменений
   ```

2. Проверьте установку:
   ```bash
   docker --version
   docker-compose --version
   ```

## Быстрый старт

### Способ 1: Используя Makefile
```bash
# Сборка и запуск
make build && make up

# Или одной командой
make rebuild

# Проверка статуса
make status

# Просмотр логов
make logs

# Остановка
make down

# Очистка
make clean
```

### Способ 2: Используя скрипт
```bash
# Дайте права на выполнение
chmod +x docker-run.sh

# Запуск
./docker-run.sh up

# Пересборка и запуск
./docker-run.sh up true

# Проверка статуса
./docker-run.sh check

# Остановка
./docker-run.sh down
```

### Способ 3: Используя docker-compose напрямую
```bash
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Просмотр логов
docker-compose logs -f

# Пересборка
docker-compose up -d --build
```

### Способ 4: Если хотите проверить каждый сервис отдельно
```bash
# Тест backend отдельно
cd backend
sudo docker build -t backend-app .
sudo docker run -p 5000:5000 backend-app

# Тест frontend отдельно
cd ../frontend/kanban-client
sudo docker build -t frontend-app .
sudo docker run -p 3000:3000 frontend-app

# Тест telegram bot отдельно
cd ../telegram_bot
sudo docker build -t telegram-bot-app .
sudo docker run telegram-bot-app
```

## Доступ к сервисам

- **Frontend (React)**: http://backend:3000
- **Backend (Flask API)**: http://backend:5000
- **Telegram Bot**: Работает в фоновом режиме

## Полезные команды

### Управление контейнерами
```bash
# Список всех контейнеров
docker ps

# Список образов
docker images

# Очистка неиспользуемых ресурсов
docker system prune

# Вход в контейнер
docker-compose exec backend bash
docker-compose exec frontend sh
```

### Мониторинг
```bash
# Просмотр использования ресурсов
docker stats

# Просмотр логов конкретного сервиса
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f telegram-bot
```

### Отладка
```bash
# Проверка работоспособности бэкенда
curl http://backend:5000

# Проверка фронтенда
curl http://backend:3000

# Проверка healthcheck
docker-compose ps
```

## Конфигурация

### Переменные окружения
Создайте файл `.env` в корне проекта для настройки:
```env
# Backend
SECRET_KEY=your-secret-key

# Telegram Bot
TELEGRAM_BOT_TOKEN=your-bot-token
```

### Изменение портов
Чтобы изменить порты, отредактируйте `docker-compose.yml`:
```yaml
ports:
  - "8080:5000"  # Внешний:Внутренний порт
```

## Устранение неполадок

### Проблема: Контейнеры не запускаются
```bash
# Проверьте логи
docker-compose logs

# Пересоберите контейнеры
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Проблема: Ошибки при сборке
```bash
# Очистите кэш Docker
docker builder prune

# Удалите все образы и пересоберите
docker-compose down -v --rmi all
docker-compose build
```

### Проблема: Нет доступа к сервисам
```bash
# Проверьте, запущены ли контейнеры
docker-compose ps

# Проверьте, слушают ли порты
netstat -tulpn | grep :3000
netstat -tulpn | grep :5000
```

## Производительность

### Оптимизация сборки
- Используйте `.dockerignore` для исключения ненужных файлов
- Используйте многоступенчатую сборку для уменьшения размера образов
- Кэшируйте зависимости с помощью слоев Docker

### Оптимизация запуска
```bash
# Ограничение ресурсов (опционально)
docker-compose up -d --scale frontend=2 --scale backend=2
```

## Безопасность

### Рекомендации
1. Не используйте root пользователя внутри контейнеров
2. Храните секреты в `.env` файле или Docker Secrets
3. Регулярно обновляйте базовые образы
4. Используйте сканирование уязвимостей:
   ```bash
   docker scan <image-name>
   ```

## Деплой на продакшен

### Рекомендации для продакшена:
1. Используйте отдельные `.env.production` файлы
2. Настройте reverse proxy (nginx, traefik)
3. Настройте мониторинг и логирование
4. Используйте Docker Swarm или Kubernetes для оркестрации
