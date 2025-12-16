#!/bin/bash

set -e
set -x

echo "=== Запуск проекта CaseK2NeuroTechDevelopmentAssistant через Docker ==="
echo "Текущая директория: $(pwd)"
echo

# Проверка наличия docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "Ошибка: docker-compose не установлен!"
    echo "Установите Docker и Docker Compose"
    exit 1
fi

# Проверка наличия необходимых файлов
if [ ! -f "docker-compose.yml" ]; then
    echo "Ошибка: docker-compose.yml не найден!"
    exit 1
fi

# Параметры запуска
ACTION=${1:-up}
FORCE_REBUILD=${2:-false}

case $ACTION in
    "up")
        if [ "$FORCE_REBUILD" = "true" ]; then
            echo "Сборка и запуск контейнеров..."
            docker-compose up -d --build
        else
            echo "Запуск контейнеров..."
            docker-compose up -d
        fi
        ;;
    "down")
        echo "Остановка контейнеров..."
        docker-compose down
        ;;
    "build")
        echo "Сборка контейнеров..."
        docker-compose build
        ;;
    "logs")
        echo "Просмотр логов..."
        docker-compose logs -f
        ;;
    "restart")
        echo "Перезапуск контейнеров..."
        docker-compose restart
        ;;
    "clean")
        echo "Очистка..."
        docker-compose down -v
        ;;
    "check")
        echo "=== Статус контейнеров ==="
        docker-compose ps
        echo -e "\n=== Проверка сервисов ==="
        
        # Проверка бэкенда
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000 | grep -q "200\|404"; then
            echo "✓ Backend доступен на http://localhost:5000"
        else
            echo "✗ Backend недоступен"
        fi
        
        # Проверка фронтенда
        if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200"; then
            echo "✓ Frontend доступен на http://localhost:3000"
        else
            echo "✗ Frontend недоступен"
        fi
        ;;
    *)
        echo "Использование: $0 [up|down|build|logs|restart|clean|check] [true для пересборки]"
        echo "Примеры:"
        echo "  $0 up          # Запуск контейнеров"
        echo "  $0 up true     # Пересборка и запуск"
        echo "  $0 check       # Проверка статуса"
        exit 1
        ;;
esac