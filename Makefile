.PHONY: build up down logs clean restart status ps shell-backend shell-frontend

# Основные команды
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

logs-bot:
	docker-compose logs -f telegram-bot

clean:
	docker-compose down -v
	docker system prune -f

restart:
	docker-compose restart

status:
	docker-compose ps

ps:
	docker-compose ps

# Команды для отладки
shell-backend:
	docker-compose exec backend /bin/bash

shell-frontend:
	docker-compose exec frontend /bin/sh

shell-bot:
	docker-compose exec telegram-bot /bin/bash

# Пересборка и запуск
rebuild:
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

# Проверка логов
check:
	@echo "=== Проверка контейнеров ==="
	docker-compose ps
	@echo "\n=== Проверка сети ==="
	docker network inspect casek2neurotechdevelopmentassistant_k11_app-network || true

# Очистка всего
deep-clean:
	docker-compose down -v --rmi all
	docker system prune -af