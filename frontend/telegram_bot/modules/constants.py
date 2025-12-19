"""Constants and configuration for Telegram bot."""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class BotConstants:
    """Constants for Telegram bot."""
    
    # Bot token from environment variables
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8521671675:AAGHlyyyx59TWb3RBVD-l6hAlnP0kHg03lU')
    
    # API server URL
    API_BASE_URL = os.getenv('API_BASE_URL', 'http://193.233.171.205:5000')
    
    # Bot commands
    COMMANDS = [
        ('start', 'Запустить бота'),
        ('help', 'Показать справку'),
        ('login', 'Войти в систему'),
        ('tasks', 'Задачи'),
        ('newtask', 'Создать задачу'),
        ('analyze', 'AI анализ задач'),
        ('export', 'Экспорт задач'),
        ('profile', 'Мой профиль'),
        ('users', 'Управление пользователями (админ)'),
        ('stats', 'Статистика системы')
    ]
    
    # Task statuses for display
    STATUS_DISPLAY = {
        'todo': 'To Do',
        'in_progress': 'In Progress',
        'done': 'Done'
    }
    
    # Task priorities
    PRIORITY_DISPLAY = {
        'low': 'Низкий',
        'medium': 'Средний',
        'high': 'Высокий',
        'urgent': 'Срочный'
    }
    
    # Maximum number of tasks to display
    MAX_TASKS_TO_SHOW = 15