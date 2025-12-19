# config_bot.py
"""
Конфигурация Telegram бота.
"""

import os
from dotenv import load_dotenv

load_dotenv()

class BotConfig:
    """Конфигурация бота."""

    # Токен бота из переменных окружения
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8521671675:AAGHlyyyx59TWb3RBVD-l6hAlnP0kHg03lU')

    # URL API сервера
    API_BASE_URL = os.getenv('API_BASE_URL', 'http://backend:5000')

    # Настройки логирования
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'bot.log')

    # Настройки бота
    ADMIN_USERNAMES = os.getenv('ADMIN_USERNAMES', '@admin_ivan,@manager_anna').split(',')

    # Настройки пула соединений
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 30))
    MAX_CONNECTIONS = int(os.getenv('MAX_CONNECTIONS', 100))

    @classmethod
    def validate_config(cls):
        """Проверка конфигурации."""
        if not cls.BOT_TOKEN or cls.BOT_TOKEN == '8521671675:AAGHlyyyx59TWb3RBVD-l6hAlnP0kHg03lU':
            print("Внимание: Используется демо-токен. Установите TELEGRAM_BOT_TOKEN в .env файле")

        if not cls.API_BASE_URL:
            print("Ошибка: API_BASE_URL не установлен")
            return False

        return True
