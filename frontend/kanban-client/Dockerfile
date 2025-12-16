FROM node:18-alpine

WORKDIR /app

# Копируем файлы зависимостей
COPY package*.json ./
COPY setup.bash ./

# Даем права на выполнение скрипта
RUN chmod +x setup.bash

# Запускаем скрипт установки (автоматически отвечаем "y")
RUN echo "y" | ./setup.bash 2>/dev/null || true

# Устанавливаем axios дополнительно
RUN npm install axios

# Копируем остальные файлы
COPY . .

# Собираем приложение
RUN npm run build

# Устанавливаем serve для статических файлов
RUN npm install -g serve

EXPOSE 3000

CMD ["serve", "-s", "build", "-l", "3000"]