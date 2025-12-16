#!/bin/sh
set -e

echo "Starting React application..."

# Проверка наличия сборки
if [ ! -d "build" ]; then
    echo "Building application..."
    npm run build
fi

# Запуск приложения
exec serve -s build -l 3000 "$@"