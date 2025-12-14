# bot.py
"""
Telegram бот для системы управления задачами.
Взаимодействует с REST API сервера, предоставляет интерфейс для управления задачами через Telegram.
"""

import os
import logging
import json
import asyncio
import pandas as pd
from io import BytesIO
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum

import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# ============================================================================
# КОНСТАНТЫ И КОНФИГУРАЦИЯ
# ============================================================================

class BotConstants:
    """Константы для Telegram бота."""

    # Токен бота из переменных окружения
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8521671675:AAGHlyyyx59TWb3RBVD-l6hAlnP0kHg03lU')

    # URL API сервера
    API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5000')

    # Команды бота
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

    # Статусы задач для отображения
    STATUS_DISPLAY = {
        'todo': 'To Do',
        'in_progress': 'In Progress',
        'done': 'Done'
    }

    # Приоритеты задач
    PRIORITY_DISPLAY = {
        'low': 'Низкий',
        'medium': 'Средний',
        'high': 'Высокий',
        'urgent': 'Срочный'
    }

    # Максимальное количество задач для отображения
    MAX_TASKS_TO_SHOW = 15


# ============================================================================
# КЛАСС ДЛЯ РАБОТЫ С API
# ============================================================================

class APIClient:
    """Клиент для взаимодействия с API сервера."""

    def __init__(self, base_url: str = BotConstants.API_BASE_URL):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_headers(self, token: str = None) -> Dict[str, str]:
        """Получить заголовки для запроса."""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'TelegramTaskBot/1.0'
        }
        if token:
            headers['Authorization'] = f'Bearer {token}'
        return headers

    async def authenticate(self, telegram_username: str, full_name: str = None) -> Dict[str, Any]:
        """Аутентификация пользователя."""
        url = f"{self.base_url}/api/telegram/auth"
        data = {
            'telegram_username': telegram_username,
            'full_name': full_name
        }

        try:
            async with self.session.post(url, json=data, headers=self._get_headers()) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('data', {})
                elif response.status == 404:
                    logging.warning(f"Пользователь {telegram_username} не найден в системе")
                    return {}
                else:
                    logging.error(f"Ошибка аутентификации: {response.status}")
                    return {}
        except aiohttp.ClientError as e:
            logging.error(f"Ошибка подключения к API: {e}")
            return {}

    async def get_tasks(self, token: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Получить список задач."""
        url = f"{self.base_url}/api/tasks"

        # Подготовка параметров запроса
        params = {}
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    params[key] = ','.join(value)
                else:
                    params[key] = value

        try:
            async with self.session.get(url, params=params, headers=self._get_headers(token)) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('data', {}).get('tasks', [])
                elif response.status == 401:
                    logging.error("Токен истек или недействителен")
                    return []
                else:
                    logging.error(f"Ошибка получения задач: {response.status}")
                    return []
        except aiohttp.ClientError as e:
            logging.error(f"Ошибка подключения к API: {e}")
            return []

    async def create_task(self, token: str, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создать новую задачу."""
        url = f"{self.base_url}/api/tasks"

        async with self.session.post(url, json=task_data, headers=self._get_headers(token)) as response:
            if response.status == 201:
                result = await response.json()
                return result.get('data', {})
            else:
                error_text = await response.text()
                logging.error(f"Ошибка создания задачи: {response.status}, {error_text}")
                return None

    async def update_task(self, token: str, task_id: int, update_data: Dict[str, Any]) -> bool:
        """Обновить задачу."""
        url = f"{self.base_url}/api/tasks/{task_id}"

        async with self.session.put(url, json=update_data, headers=self._get_headers(token)) as response:
            return response.status == 200

    async def get_llm_analysis(self, token: str, analysis_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Получить AI анализ задач."""
        url = f"{self.base_url}/api/llm/analyze/tasks"

        async with self.session.post(url, json=analysis_params, headers=self._get_headers(token)) as response:
            if response.status == 200:
                result = await response.json()
                return result.get('data', {})
            else:
                logging.error(f"Ошибка получения анализа: {response.status}")
                return None

    async def export_tasks_csv(self, token: str, params: Dict[str, Any] = None) -> Optional[bytes]:
        """Экспортировать задачи в CSV."""
        url = f"{self.base_url}/api/export/tasks.csv"

        # Подготовка параметров запроса
        query_params = params or {}

        async with self.session.get(url, params=query_params, headers=self._get_headers(token)) as response:
            if response.status == 200:
                return await response.read()
            else:
                logging.error(f"Ошибка экспорта: {response.status}")
                return None

    async def create_user(self, token: str, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создать нового пользователя."""
        url = f"{self.base_url}/api/users"

        async with self.session.post(url, json=user_data, headers=self._get_headers(token)) as response:
            if response.status == 201:
                result = await response.json()
                return result.get('data', {})
            else:
                logging.error(f"Ошибка создания пользователя: {response.status}")
                return None

    async def get_system_health(self) -> Optional[Dict[str, Any]]:
        """Получить статус здоровья системы."""
        url = f"{self.base_url}/api/health"

        try:
            async with self.session.get(url, headers=self._get_headers()) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('data', {})
                else:
                    logging.error(f"Ошибка проверки здоровья: {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logging.error(f"API недоступен: {e}")
            return None


# ============================================================================
# СОСТОЯНИЯ БОТА (FSM)
# ============================================================================

class TaskStates(StatesGroup):
    """Состояния для создания/редактирования задач."""
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_priority = State()
    waiting_for_due_date = State()
    waiting_for_tags = State()
    waiting_for_task_id = State()
    waiting_for_update_field = State()
    waiting_for_update_value = State()


class UserStates(StatesGroup):
    """Состояния для управления пользователями."""
    waiting_for_username = State()
    waiting_for_full_name = State()
    waiting_for_role = State()


class AnalysisStates(StatesGroup):
    """Состояния для AI анализа."""
    waiting_for_period = State()


# ============================================================================
# КЛАСС ДЛЯ ХРАНЕНИЯ ДАННЫХ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================================

class UserSession:
    """Класс для хранения данных сессии пользователя."""

    def __init__(self):
        self.sessions = {}  # user_id -> session_data

    def get_session(self, user_id: int) -> Dict[str, Any]:
        """Получить сессию пользователя."""
        return self.sessions.get(user_id, {})

    def set_session(self, user_id: int, session_data: Dict[str, Any]):
        """Установить сессию пользователя."""
        self.sessions[user_id] = session_data

    def get_token(self, user_id: int) -> Optional[str]:
        """Получить токен пользователя."""
        session = self.get_session(user_id)
        if not session:
            logging.debug(f"Сессия не найдена для пользователя {user_id}")
            return None

        # Ищем токен в разных возможных местах
        token = None

        # Проверяем напрямую в сессии
        if 'access_token' in session:
            token = session['access_token']
        elif 'session_token' in session:
            token = session['session_token']
        elif 'token' in session:
            token = session['token']

        # Проверяем в user_info
        if not token and 'user_info' in session:
            user_info = session['user_info']
            if 'access_token' in user_info:
                token = user_info['access_token']
            elif 'session_token' in user_info:
                token = user_info['session_token']
            elif 'token' in user_info:
                token = user_info['token']

        # Проверяем в data внутри user_info
        if not token and 'user_info' in session:
            user_info = session['user_info']
            if 'data' in user_info and isinstance(user_info['data'], dict):
                data = user_info['data']
                if 'access_token' in data:
                    token = data['access_token']
                elif 'session_token' in data:
                    token = data['session_token']
                elif 'token' in data:
                    token = data['token']

        if token:
            logging.debug(f"Токен найден для пользователя {user_id}: {token[:10]}...")
        else:
            logging.warning(f"Токен не найден для пользователя {user_id}. Доступные ключи: {list(session.keys())}")
            if 'user_info' in session:
                logging.warning(f"User info ключи: {list(session['user_info'].keys())}")

        return token

    def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию о пользователе."""
        session = self.get_session(user_id)
        if not session:
            return None

        # Возвращаем user_info из разных возможных мест
        if 'user_info' in session:
            return session['user_info']
        elif 'user' in session:
            return {'user': session['user']}

        return None

    def clear_session(self, user_id: int):
        """Очистить сессию пользователя."""
        if user_id in self.sessions:
            del self.sessions[user_id]
            logging.info(f"Сессия очищена для пользователя {user_id}")


# ============================================================================
# УТИЛИТЫ ДЛЯ ФОРМАТИРОВАНИЯ
# ============================================================================

class MessageFormatter:
    """Класс для форматирования сообщений."""

    @staticmethod
    def format_task(task: Dict[str, Any]) -> str:
        """Форматировать задачу для отображения."""
        status_display = BotConstants.STATUS_DISPLAY.get(task.get('status', 'todo'), 'To Do')
        priority_display = BotConstants.PRIORITY_DISPLAY.get(task.get('priority', 'medium'), 'Средний')

        lines = [
            f"Задача #{task.get('task_id', 'N/A')}",
            f"",
            f"Заголовок: {task.get('title', 'Без названия')}",
            f"",
        ]

        if task.get('description'):
            desc = task['description']
            if len(desc) > 100:
                desc = desc[:100] + "..."
            lines.append(f"Описание:\n{desc}")

        lines.extend([
            f"",
            f"Назначена: {task.get('assignee_name', task.get('assignee', 'Не назначена'))}",
            f"Создатель: {task.get('creator_name', task.get('creator', 'Неизвестно'))}",
            f"",
            f"Статус: {status_display}",
            f"Приоритет: {priority_display}",
        ])

        if task.get('created_at'):
            created_date = task['created_at'].split('T')[0] if 'T' in task['created_at'] else task['created_at'][:10]
            lines.append(f"Создана: {created_date}")

        if task.get('due_date'):
            due_date = task['due_date']
            days_remaining = task.get('days_remaining')
            if days_remaining is not None:
                if days_remaining < 0:
                    lines.append(f"Дедлайн: Просрочено на {abs(days_remaining)} дней")
                elif days_remaining == 0:
                    lines.append(f"Дедлайн: Сегодня")
                elif days_remaining <= 2:
                    lines.append(f"Дедлайн: {due_date} (осталось {days_remaining} дней)")
                else:
                    lines.append(f"Дедлайн: {due_date} (осталось {days_remaining} дней)")
            else:
                lines.append(f"Дедлайн: {due_date}")

        if task.get('tags'):
            tags = task['tags']
            if isinstance(tags, list):
                lines.append(f"Теги: {' '.join([f'#{tag}' for tag in tags])}")
            elif isinstance(tags, str):
                try:
                    tags_list = json.loads(tags)
                    lines.append(f"Теги: {' '.join([f'#{tag}' for tag in tags_list])}")
                except:
                    lines.append(f"Теги: {tags}")

        return "\n".join(lines)

    @staticmethod
    def format_tasks_list(tasks: List[Dict[str, Any]], total_count: int = None) -> str:
        """Форматировать список задач."""
        if not tasks:
            return "Задачи не найдены"

        max_tasks = BotConstants.MAX_TASKS_TO_SHOW
        displayed_tasks = tasks[:max_tasks]

        if total_count is None:
            total_count = len(tasks)

        lines = [f"Найдено задач: {total_count}", ""]

        if total_count > max_tasks:
            lines.append(f"Показаны первые {max_tasks} задач")
            lines.append(f"Для просмотра всех задач используйте экспорт")
            lines.append("")

        for task in displayed_tasks:
            status_display = BotConstants.STATUS_DISPLAY.get(task.get('status', 'todo'), 'To Do')[:1]
            priority_display = BotConstants.PRIORITY_DISPLAY.get(task.get('priority', 'medium'), 'Средний')[:1]

            task_id = task.get('task_id', '?')
            title = task.get('title', 'Без названия')[:30]
            assignee = task.get('assignee_name', task.get('assignee', 'Не назначена'))[:15]

            line = f"#{task_id} - {title} • {assignee} ({status_display}/{priority_display})"

            if task.get('due_date'):
                days_remaining = task.get('days_remaining', 0)
                if days_remaining < 0:
                    line += f" [Просрочено]"
                elif days_remaining == 0:
                    line += f" [Сегодня]"
                elif days_remaining <= 2:
                    line += f" [Скоро]"

            lines.append(line)

        if total_count > max_tasks:
            lines.append(f"\n... и еще {total_count - max_tasks} задач")
            lines.append("Для просмотра всех задач используйте экспорт")

        return "\n".join(lines)

    @staticmethod
    def format_user_info(user_info: Dict[str, Any]) -> str:
        """Форматировать информацию о пользователе."""
        if not user_info:
            return "Информация о пользователе недоступна"

        # Извлекаем данные пользователя
        user = {}
        if 'user' in user_info:
            user = user_info['user']
        elif 'data' in user_info and 'user' in user_info['data']:
            user = user_info['data']['user']

        permissions = user_info.get('permissions', {})

        lines = [
            f"Ваш профиль",
            f"",
            f"Имя: {user.get('full_name', 'Не указано')}",
            f"Telegram: {user.get('telegram_username', 'Не указан')}",
            f"Роль: {user.get('role', 'member').title()}",
            f"Статус: {'Активен' if str(user.get('is_active', '')).lower() == 'true' else 'Неактивен'}",
            f"",
        ]

        if user.get('email'):
            lines.append(f"Email: {user['email']}")
        if user.get('department'):
            lines.append(f"Отдел: {user['department']}")

        lines.extend([
            f"",
            f"Права доступа:",
        ])

        if permissions.get('can_create_tasks'):
            lines.append(f"- Создавать задачи")
        if permissions.get('can_edit_tasks'):
            lines.append(f"- Редактировать задачи")
        if permissions.get('can_delete_tasks'):
            lines.append(f"- Удалять задачи")
        if permissions.get('can_export'):
            lines.append(f"- Экспортировать данные")
        if permissions.get('can_use_llm'):
            lines.append(f"- Использовать AI анализ")
        if permissions.get('can_manage_users'):
            lines.append(f"- Управлять пользователями")

        llm_limit = permissions.get('llm_daily_limit', 0)
        lines.append(f"\nЛимит AI запросов: {llm_limit}/день")

        if user.get('last_login'):
            lines.append(f"")
            lines.append(f"Последний вход: {user['last_login']}")

        return "\n".join(lines)


# ============================================================================
# КЛАВИАТУРЫ
# ============================================================================

class Keyboards:
    """Класс для создания клавиатур."""

    @staticmethod
    def get_main_menu() -> ReplyKeyboardMarkup:
        """Главное меню."""
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Задачи"), KeyboardButton(text="Создать задачу")],
                [KeyboardButton(text="AI Анализ"), KeyboardButton(text="Экспорт")],
                [KeyboardButton(text="Профиль"), KeyboardButton(text="Помощь")]
            ],
            resize_keyboard=True,
            input_field_placeholder="Выберите действие..."
        )

    @staticmethod
    def get_tasks_menu() -> ReplyKeyboardMarkup:
        """Меню задач."""
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Мои задачи"), KeyboardButton(text="Все задачи")],
                [KeyboardButton(text="Поиск по фильтрам")],
                [KeyboardButton(text="Назад в меню")]
            ],
            resize_keyboard=True
        )

    @staticmethod
    def get_cancel_keyboard() -> ReplyKeyboardMarkup:
        """Клавиатура с кнопкой отмены."""
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Отмена")]],
            resize_keyboard=True
        )

    @staticmethod
    def get_task_filters_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура для фильтрации задач."""
        builder = InlineKeyboardBuilder()

        builder.add(
            InlineKeyboardButton(text="To Do", callback_data="filter_status:todo"),
            InlineKeyboardButton(text="In Progress", callback_data="filter_status:in_progress"),
            InlineKeyboardButton(text="Done", callback_data="filter_status:done"),
            InlineKeyboardButton(text="Низкий", callback_data="filter_priority:low"),
            InlineKeyboardButton(text="Средний", callback_data="filter_priority:medium"),
            InlineKeyboardButton(text="Высокий", callback_data="filter_priority:high"),
            InlineKeyboardButton(text="Срочный", callback_data="filter_priority:urgent"),
            InlineKeyboardButton(text="Мои задачи", callback_data="filter_assignee:me"),
            InlineKeyboardButton(text="Сегодня", callback_data="filter_today:true"),
            InlineKeyboardButton(text="Очистить", callback_data="filter_clear:all"),
            InlineKeyboardButton(text="Применить", callback_data="filter_apply:true"),
        )

        builder.adjust(3, 3, 2, 1, 1)
        return builder.as_markup()

    @staticmethod
    def get_priority_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура для выбора приоритета."""
        builder = InlineKeyboardBuilder()

        builder.add(
            InlineKeyboardButton(text="Низкий", callback_data="priority:low"),
            InlineKeyboardButton(text="Средний", callback_data="priority:medium"),
            InlineKeyboardButton(text="Высокий", callback_data="priority:high"),
            InlineKeyboardButton(text="Срочный", callback_data="priority:urgent"),
        )

        builder.adjust(2, 2)
        return builder.as_markup()

    @staticmethod
    def get_status_keyboard(task_id: int = None) -> InlineKeyboardMarkup:
        """Клавиатура для изменения статуса задачи."""
        builder = InlineKeyboardBuilder()

        if task_id:
            builder.add(
                InlineKeyboardButton(text="To Do", callback_data=f"status_{task_id}:todo"),
                InlineKeyboardButton(text="In Progress", callback_data=f"status_{task_id}:in_progress"),
                InlineKeyboardButton(text="Done", callback_data=f"status_{task_id}:done"),
            )
        else:
            builder.add(
                InlineKeyboardButton(text="To Do", callback_data="status:todo"),
                InlineKeyboardButton(text="In Progress", callback_data="status:in_progress"),
                InlineKeyboardButton(text="Done", callback_data="status:done"),
            )

        builder.adjust(3)
        return builder.as_markup()

    @staticmethod
    def get_analysis_period_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура для выбора периода анализа."""
        builder = InlineKeyboardBuilder()

        builder.add(
            InlineKeyboardButton(text="Неделя", callback_data="analysis_period:last_week"),
            InlineKeyboardButton(text="Месяц", callback_data="analysis_period:last_month"),
            InlineKeyboardButton(text="Квартал", callback_data="analysis_period:last_quarter"),
        )

        builder.adjust(3)
        return builder.as_markup()

    @staticmethod
    def get_export_format_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура для выбора формата экспорта."""
        builder = InlineKeyboardBuilder()

        builder.add(
            InlineKeyboardButton(text="CSV", callback_data="export_format:csv"),
            InlineKeyboardButton(text="Excel", callback_data="export_format:excel"),
        )

        builder.adjust(2)
        return builder.as_markup()

    @staticmethod
    def get_task_actions_keyboard(task_id: int) -> InlineKeyboardMarkup:
        """Клавиатура с действиями для задачи."""
        builder = InlineKeyboardBuilder()

        builder.add(
            InlineKeyboardButton(text="Редактировать", callback_data=f"edit_task:{task_id}"),
            InlineKeyboardButton(text="Изменить статус", callback_data=f"change_status:{task_id}"),
            InlineKeyboardButton(text="Изменить дедлайн", callback_data=f"change_due:{task_id}"),
            InlineKeyboardButton(text="Переназначить", callback_data=f"reassign:{task_id}"),
            InlineKeyboardButton(text="Удалить", callback_data=f"delete_task:{task_id}"),
        )

        builder.adjust(2, 2, 1)
        return builder.as_markup()


# ============================================================================
# ИНИЦИАЛИЗАЦИЯ БОТА
# ============================================================================

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BotConstants.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация менеджера сессий
user_sessions = UserSession()


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def convert_to_excel(data: List[Dict[str, Any]]) -> BytesIO:
    """Конвертировать данные в Excel файл."""
    try:
        # Создаем DataFrame из данных
        df = pd.DataFrame(data)

        # Создаем буфер для Excel файла
        output = BytesIO()

        # Используем ExcelWriter для записи
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Tasks')

            # Получаем workbook и worksheet для настройки ширины колонок
            worksheet = writer.sheets['Tasks']

            # Автонастройка ширины колонок
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        output.seek(0)
        return output
    except Exception as e:
        logging.error(f"Ошибка создания Excel файла: {e}")
        return None


def csv_to_excel(csv_data: bytes) -> Optional[BytesIO]:
    """Конвертировать CSV данные в Excel файл."""
    try:
        # Читаем CSV данные в DataFrame
        df = pd.read_csv(BytesIO(csv_data))

        # Создаем буфер для Excel файла
        output = BytesIO()

        # Используем ExcelWriter для записи
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Tasks')

            # Получаем workbook и worksheet для настройки ширины колонок
            worksheet = writer.sheets['Tasks']

            # Автонастройка ширины колонок
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        output.seek(0)
        return output
    except Exception as e:
        logging.error(f"Ошибка конвертации CSV в Excel: {e}")
        return None


# ============================================================================
# ОСНОВНЫЕ ОБРАБОТЧИКИ
# ============================================================================

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start."""
    await state.clear()

    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else f"user_{user_id}"
    full_name = message.from_user.full_name or f"Пользователь {user_id}"

    # Приветственное сообщение
    welcome_text = (
        f"Добро пожаловать в Task Manager Bot!\n\n"
        f"Я помогу вам управлять задачами вашей команды:\n"
        f"- Создавать и отслеживать задачи\n"
        f"- Получать уведомления об изменениях\n"
        f"- Анализировать продуктивность с помощью AI\n"
        f"- Экспортировать данные в CSV и Excel\n\n"
        f"Для начала работы используйте команду /login\n"
        f"Или выберите действие в меню ниже"
    )

    # Попытка автоматической аутентификации
    async with APIClient() as api_client:
        auth_result = await api_client.authenticate(username, full_name)

        if auth_result and auth_result.get('authenticated'):
            # Сохраняем сессию
            session_data = {
                'access_token': auth_result.get('access_token'),
                'user_info': auth_result
            }
            user_sessions.set_session(user_id, session_data)

            logging.info(f"Пользователь {user_id} ({username}) успешно аутентифицирован")
            logging.debug(f"Токен сохранен: {auth_result.get('access_token', '')[:10]}...")

            welcome_text += f"\n\nВы успешно вошли как {auth_result.get('user', {}).get('full_name', username)}"
            await message.answer(
                welcome_text,
                reply_markup=Keyboards.get_main_menu()
            )
        else:
            # Показываем меню без авторизации
            logging.info(f"Пользователь {user_id} ({username}) не аутентифицирован")
            await message.answer(
                welcome_text
            )
            await message.answer(
                "Для использования всех функций бота необходимо войти в систему.\n"
                "Используйте команду /login",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="/login")]],
                    resize_keyboard=True
                )
            )


@dp.message(Command("login"))
async def cmd_login(message: Message, state: FSMContext):
    """Обработчик команды /login."""
    await state.clear()

    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else f"user_{user_id}"
    full_name = message.from_user.full_name or f"Пользователь {user_id}"

    await message.answer(
        "Пытаюсь войти в систему..."
    )

    async with APIClient() as api_client:
        auth_result = await api_client.authenticate(username, full_name)

        if auth_result and auth_result.get('authenticated'):
            # Сохраняем сессию
            session_data = {
                'access_token': auth_result.get('access_token'),
                'user_info': auth_result
            }
            user_sessions.set_session(user_id, session_data)

            logging.info(f"Пользователь {user_id} ({username}) успешно вошел")
            logging.debug(f"Токен сохранен: {auth_result.get('access_token', '')[:10]}...")

            user_data = auth_result.get('user', {})
            await message.answer(
                f"Успешный вход!\n\n"
                f"Добро пожаловать, {user_data.get('full_name', username)}!\n"
                f"Ваша роль: {user_data.get('role', 'member').title()}\n\n"
                f"Теперь вы можете использовать все функции бота.",
                reply_markup=Keyboards.get_main_menu()
            )
        else:
            logging.warning(f"Пользователь {user_id} ({username}) не смог войти в систему")
            await message.answer(
                "Не удалось войти в систему\n\n"
                "Возможные причины:\n"
                "- Ваш Telegram не зарегистрирован в системе\n"
                "- Система недоступна\n"
                "- Ошибка аутентификации\n\n"
                "Обратитесь к администратору для регистрации."
            )


@dp.message(F.text == "Задачи")
@dp.message(Command("tasks"))
async def cmd_tasks(message: Message, state: FSMContext):
    """Обработчик команды просмотра задач."""
    await state.clear()

    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)

    logging.info(f"Запрос задач от пользователя {user_id}, токен найден: {token is not None}")

    if not token:
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return

    # Показываем меню задач
    await message.answer(
        "Меню задач",
        reply_markup=Keyboards.get_tasks_menu()
    )


@dp.message(F.text == "Мои задачи")
async def cmd_my_tasks(message: Message, state: FSMContext):
    """Обработчик команды моих задач."""
    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)

    if not token:
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return

    # Получаем информацию о пользователе для фильтрации
    user_info = user_sessions.get_user_info(user_id)
    username = None
    if user_info:
        user_data = user_info.get('user', {})
        username = user_data.get('telegram_username')

    filters = {}
    if username:
        filters['assignee'] = username

    await load_and_show_tasks(message, token, filters, "Мои задачи")


@dp.message(F.text == "Все задачи")
async def cmd_all_tasks(message: Message, state: FSMContext):
    """Обработчик команды всех задач."""
    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)

    if not token:
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return

    await load_and_show_tasks(message, token, {}, "Все задачи")


@dp.message(F.text == "Поиск по фильтрам")
async def cmd_filter_search(message: Message, state: FSMContext):
    """Обработчик поиска задач по фильтрам."""
    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)

    if not token:
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return

    # Показываем фильтры задач
    await message.answer(
        "Поиск задач по фильтрам\n\n"
        "Выберите фильтры для поиска задач:",
        reply_markup=Keyboards.get_task_filters_keyboard()
    )


async def load_and_show_tasks(message: Message, token: str, filters: Dict[str, Any], title: str = "Задачи"):
    """Загрузить и показать задачи."""
    await message.answer(
        f"Загружаю {title.lower()}...",
        reply_markup=ReplyKeyboardRemove()
    )

    async with APIClient() as api_client:
        tasks = await api_client.get_tasks(token, filters)

        if not tasks:
            await message.answer(
                "Задачи не найдены",
                reply_markup=Keyboards.get_tasks_menu()
            )
            return

        # Отображаем список задач
        formatter = MessageFormatter()
        tasks_text = formatter.format_tasks_list(tasks, len(tasks))

        # Создаем клавиатуру с предложением экспорта если много задач
        reply_markup = Keyboards.get_tasks_menu()

        if len(tasks) > BotConstants.MAX_TASKS_TO_SHOW:
            # Добавляем кнопку для экспорта
            builder = InlineKeyboardBuilder()
            builder.add(
                InlineKeyboardButton(text="📤 Экспорт всех задач", callback_data="export_all_tasks"),
            )
            reply_markup = builder.as_markup()

        await message.answer(
            tasks_text,
            reply_markup=reply_markup
        )


@dp.message(F.text == "Создать задачу")
@dp.message(Command("newtask"))
async def cmd_new_task(message: Message, state: FSMContext):
    """Обработчик создания новой задачи."""
    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)

    logging.info(f"Запрос создания задачи от пользователя {user_id}, токен найден: {token is not None}")

    if not token:
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return

    await state.set_state(TaskStates.waiting_for_title)
    await message.answer(
        "Создание новой задачи\n\n"
        "Введите заголовок задачи:",
        reply_markup=Keyboards.get_cancel_keyboard()
    )


@dp.message(F.text == "AI Анализ")
@dp.message(Command("analyze"))
async def cmd_analyze(message: Message, state: FSMContext):
    """Обработчик команды AI анализа."""
    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)

    logging.info(f"Запрос AI анализа от пользователя {user_id}, токен найден: {token is not None}")

    if not token:
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return

    await message.answer(
        "AI Анализ задач\n\n"
        "Выберите период для анализа:",
        reply_markup=Keyboards.get_analysis_period_keyboard()
    )


@dp.message(F.text == "Экспорт")
@dp.message(Command("export"))
async def cmd_export(message: Message, state: FSMContext):
    """Обработчик команды экспорта."""
    user_id = message.from_user.id
    token = user_sessions.get_token(user_id)

    logging.info(f"Запрос экспорта от пользователя {user_id}, токен найден: {token is not None}")

    if not token:
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в системе.",
            reply_markup=Keyboards.get_main_menu()
        )
        return

    await message.answer(
        "Экспорт задач\n\n"
        "Выберите формат экспорта:",
        reply_markup=Keyboards.get_export_format_keyboard()
    )


@dp.callback_query(F.data == "export_all_tasks")
async def handle_export_all_tasks(callback: CallbackQuery):
    """Обработчик экспорта всех задач."""
    user_id = callback.from_user.id
    token = user_sessions.get_token(user_id)

    if not token:
        await callback.answer("Вы не авторизованы")
        return

    await callback.message.edit_text(
        "Экспорт всех задач\n\n"
        "Выберите формат экспорта:",
        reply_markup=Keyboards.get_export_format_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("export_format:"))
async def handle_export_format(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора формата экспорта."""
    user_id = callback.from_user.id
    token = user_sessions.get_token(user_id)

    if not token:
        await callback.answer("Вы не авторизованы")
        return

    _, export_format = callback.data.split(":", 1)

    await callback.message.edit_text(
        f"Экспорт задач в {export_format.upper()}\n\n"
        "Подготавливаю файл...",
    )

    async with APIClient() as api_client:
        # Получаем все задачи
        tasks = await api_client.get_tasks(token, {})

        if not tasks:
            await callback.message.edit_text(
                "Задачи не найдены для экспорта.",
            )
            await callback.answer("Нет задач для экспорта")
            return

        if export_format == "csv":
            # Используем API для экспорта в CSV
            csv_data = await api_client.export_tasks_csv(token)

            if csv_data:
                # Отправляем CSV файл
                await callback.message.answer_document(
                    types.BufferedInputFile(
                        csv_data,
                        filename=f"tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    ),
                    caption="Экспорт завершен\n\nФайл с задачами в CSV формате готов.",
                )
                await callback.answer("Экспорт CSV завершен")
            else:
                await callback.message.edit_text(
                    "Ошибка экспорта\n\n"
                    "Не удалось экспортировать задачи в CSV. Попробуйте позже.",
                )
                await callback.answer("Ошибка экспорта")

        elif export_format == "excel":
            try:
                # Пытаемся создать Excel напрямую из данных
                excel_buffer = convert_to_excel(tasks)

                if excel_buffer:
                    # Отправляем Excel файл
                    await callback.message.answer_document(
                        types.BufferedInputFile(
                            excel_buffer.read(),
                            filename=f"tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        ),
                        caption="Экспорт завершен\n\nФайл с задачами в Excel формате готов.",
                    )
                    await callback.answer("Экспорт Excel завершен")
                else:
                    # Если не удалось создать Excel напрямую, пробуем через CSV
                    logging.info("Прямое создание Excel не удалось, пробуем через CSV...")

                    # Сначала получаем CSV
                    csv_data = await api_client.export_tasks_csv(token)

                    if csv_data:
                        # Конвертируем CSV в Excel
                        excel_buffer = csv_to_excel(csv_data)

                        if excel_buffer:
                            # Отправляем Excel файл
                            await callback.message.answer_document(
                                types.BufferedInputFile(
                                    excel_buffer.read(),
                                    filename=f"tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                                ),
                                caption="Экспорт завершен\n\nФайл с задачами в Excel формате готов (создан из CSV).",
                            )
                            await callback.answer("Экспорт Excel завершен")
                        else:
                            await callback.message.edit_text(
                                "Ошибка экспорта\n\n"
                                "Не удалось создать Excel файл даже через CSV. Попробуйте экспортировать в CSV.",
                            )
                            await callback.answer("Ошибка создания Excel")
                    else:
                        await callback.message.edit_text(
                            "Ошибка экспорта\n\n"
                            "Не удалось получить данные для экспорта. Попробуйте позже.",
                        )
                        await callback.answer("Ошибка получения данных")
            except Exception as e:
                logging.error(f"Ошибка создания Excel: {e}")

                # Пробуем альтернативный метод - создаем CSV и конвертируем
                try:
                    csv_data = await api_client.export_tasks_csv(token)
                    if csv_data:
                        excel_buffer = csv_to_excel(csv_data)
                        if excel_buffer:
                            await callback.message.answer_document(
                                types.BufferedInputFile(
                                    excel_buffer.read(),
                                    filename=f"tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                                ),
                                caption="Экспорт завершен\n\nФайл с задачами в Excel формате готов (создан через CSV).",
                            )
                            await callback.answer("Экспорт Excel завершен")
                        else:
                            await callback.message.edit_text(
                                f"Ошибка экспорта\n\n"
                                f"Не удалось создать Excel файл: {str(e)[:100]}",
                            )
                            await callback.answer("Ошибка экспорта")
                    else:
                        await callback.message.edit_text(
                            f"Ошибка экспорта\n\n"
                            f"Не удалось получить данные: {str(e)[:100]}",
                        )
                        await callback.answer("Ошибка экспорта")
                except Exception as e2:
                    logging.error(f"Ошибка альтернативного метода: {e2}")
                    await callback.message.edit_text(
                        f"Ошибка экспорта\n\n"
                        f"Не удалось создать Excel файл. Попробуйте экспортировать в CSV.",
                    )
                    await callback.answer("Ошибка экспорта")


@dp.message(F.text == "Профиль")
@dp.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext):
    """Обработчик команды просмотра профиля."""
    await state.clear()

    user_id = message.from_user.id
    user_info = user_sessions.get_user_info(user_id)

    logging.info(f"Запрос профиля от пользователя {user_id}, информация найдена: {user_info is not None}")

    if not user_info:
        await message.answer(
            "Вы не авторизованы\n\n"
            "Используйте команду /login для входа в систему.",
            reply_markup=Keyboards.get_main_menu()
        )
        return

    # Форматируем информацию о пользователе
    formatter = MessageFormatter()
    profile_text = formatter.format_user_info(user_info)

    await message.answer(
        profile_text,
        reply_markup=Keyboards.get_main_menu()
    )


@dp.message(F.text == "Назад в меню")
async def cmd_back_to_menu(message: Message, state: FSMContext):
    """Обработчик возврата в главное меню."""
    await state.clear()
    await message.answer(
        "Возвращаюсь в главное меню.",
        reply_markup=Keyboards.get_main_menu()
    )


@dp.message(F.text == "Отмена")
async def cmd_cancel(message: Message, state: FSMContext):
    """Обработчик отмены действий."""
    await state.clear()
    await message.answer(
        "Действие отменено\n\n"
        "Возвращаюсь в главное меню.",
        reply_markup=Keyboards.get_main_menu()
    )


# ============================================================================
# ОБРАБОТЧИКИ КНОПОК МЕНЮ
# ============================================================================

@dp.message(F.text == "Помощь")
async def cmd_help_button(message: Message):
    """Обработчик кнопки помощи."""
    await cmd_help(message)


# ============================================================================
# ОБРАБОТЧИК CALLBACK ЗАПРОСОВ
# ============================================================================

@dp.callback_query(F.data.startswith("filter_"))
async def handle_task_filters(callback: CallbackQuery, state: FSMContext):
    """Обработчик фильтров задач."""
    user_id = callback.from_user.id
    token = user_sessions.get_token(user_id)

    if not token:
        await callback.answer("Вы не авторизованы")
        return

    filter_type, filter_value = callback.data.split(":", 1)
    current_filters = await state.get_data() or {}

    if filter_type == "filter_status":
        status_filters = current_filters.get('status', [])
        if filter_value in status_filters:
            status_filters.remove(filter_value)
            await callback.answer(f"Фильтр {filter_value} удален")
        else:
            status_filters.append(filter_value)
            await callback.answer(f"Фильтр {filter_value} добавлен")
        current_filters['status'] = status_filters

    elif filter_type == "filter_priority":
        priority_filters = current_filters.get('priority', [])
        if filter_value in priority_filters:
            priority_filters.remove(filter_value)
            await callback.answer(f"Фильтр {filter_value} удален")
        else:
            priority_filters.append(filter_value)
            await callback.answer(f"Фильтр {filter_value} добавлен")
        current_filters['priority'] = priority_filters

    elif filter_type == "filter_assignee":
        if filter_value == "me":
            user_info = user_sessions.get_user_info(user_id)
            if user_info:
                user_data = user_info.get('user', {})
                username = user_data.get('telegram_username')
                if username:
                    current_filters['assignee'] = username
                    await callback.answer("Показать только мои задачи")
        else:
            current_filters.pop('assignee', None)
            await callback.answer("Фильтр назначения сброшен")

    elif filter_type == "filter_today":
        if filter_value == "true":
            today = datetime.now().strftime('%Y-%m-%d')
            current_filters['date_from'] = today
            current_filters['date_to'] = today
            await callback.answer("Показать задачи на сегодня")

    elif filter_type == "filter_clear":
        await state.clear()
        current_filters = {}
        await callback.message.edit_text(
            "Фильтры сброшены\n\n"
            "Выберите фильтры для отображения задач:",
            reply_markup=Keyboards.get_task_filters_keyboard()
        )
        await callback.answer("Фильтры сброшены")
        return

    elif filter_type == "filter_apply":
        # Применяем фильтры и загружаем задачи
        await load_and_show_tasks(callback.message, token, current_filters, "отфильтрованные задачи")
        await callback.answer("Фильтры применены")
        return

    await state.set_data(current_filters)

    filter_text = "Текущие фильтры:\n"
    if current_filters.get('status'):
        filter_text += f"Статус: {', '.join(current_filters['status'])}\n"
    if current_filters.get('priority'):
        filter_text += f"Приоритет: {', '.join(current_filters['priority'])}\n"
    if current_filters.get('assignee'):
        filter_text += f"Назначена: {current_filters['assignee']}\n"
    if current_filters.get('date_from'):
        filter_text += f"Дата: {current_filters['date_from']}"
        if current_filters.get('date_to'):
            filter_text += f" - {current_filters['date_to']}"
        filter_text += "\n"

    if not current_filters:
        filter_text = "Фильтры задач\n\nВыберите фильтры для отображения задач:"

    await callback.message.edit_text(
        filter_text,
        reply_markup=Keyboards.get_task_filters_keyboard()
    )


@dp.callback_query(F.data.startswith("analysis_period:"))
async def handle_analysis_period(callback: CallbackQuery):
    """Обработчик выбора периода анализа."""
    user_id = callback.from_user.id
    token = user_sessions.get_token(user_id)

    if not token:
        await callback.answer("Вы не авторизованы")
        return

    _, period = callback.data.split(":", 1)

    period_display = {
        'last_week': 'неделю',
        'last_month': 'месяц',
        'last_quarter': 'квартал'
    }.get(period, period)

    await callback.message.edit_text(
        f"Анализ задач за {period_display}\n\n"
        "Запрашиваю анализ у AI...",
    )

    async with APIClient() as api_client:
        analysis_params = {
            'time_period': period,
            'metrics': ['productivity', 'bottlenecks', 'team_performance'],
            'include_recommendations': True
        }

        analysis_result = await api_client.get_llm_analysis(token, analysis_params)

        if analysis_result:
            summary = analysis_result.get('analysis', {}).get('summary', {})
            recommendations = analysis_result.get('recommendations', [])

            analysis_text = (
                f"AI Анализ задач ({period_display})\n\n"
                f"Общая статистика:\n"
                f"- Всего задач: {summary.get('total_tasks', 0)}\n"
                f"- Выполнено: {summary.get('completed', 0)}\n"
                f"- В работе: {summary.get('in_progress', 0)}\n"
                f"- Просрочено: {summary.get('overdue', 0)}\n"
                f"- Процент выполнения: {summary.get('completion_rate', '0%')}\n\n"
            )

            if recommendations:
                analysis_text += "Рекомендации:\n"
                for i, rec in enumerate(recommendations[:5], 1):
                    analysis_text += f"{i}. {rec}\n"

            await callback.message.edit_text(
                analysis_text,
            )
        else:
            await callback.message.edit_text(
                "Ошибка анализа\n\n"
                "Не удалось получить анализ задач. Попробуйте позже.",
            )

    await callback.answer("Анализ завершен")


# ============================================================================
# ОБРАБОТЧИК НЕИЗВЕСТНЫХ СООБЩЕНИЙ И КОМАНДЫ HELP
# ============================================================================

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help."""
    help_text = (
        "Справка по командам\n\n"
        "Основные команды:\n"
        "/start - Запустить бота\n"
        "/login - Войти в систему\n"
        "/tasks - Задачи\n"
        "/newtask - Создать задачу\n"
        "/analyze - AI анализ задач\n"
        "/export - Экспорт задач\n"
        "/profile - Мой профиль\n\n"
        "Быстрые действия:\n"
        "Используйте кнопки меню для быстрого доступа к функциям."
    )
    await message.answer(help_text, reply_markup=Keyboards.get_main_menu())


@dp.message()
async def handle_unknown_message(message: Message):
    """Обработчик неизвестных сообщений."""
    logging.info(f"Получено неизвестное сообщение: {message.text} от пользователя {message.from_user.id}")

    await message.answer(
        "Я не понял ваше сообщение\n\n"
        "Используйте команды из меню или напишите /help для справки.",
        reply_markup=Keyboards.get_main_menu()
    )


# ============================================================================
# ЗАПУСК БОТА
# ============================================================================

async def main():
    """Основная функция запуска бота."""
    logger.info("Запуск Telegram бота...")

    # Установка команд бота
    commands = [
        types.BotCommand(command=cmd, description=desc)
        for cmd, desc in BotConstants.COMMANDS
    ]
    await bot.set_my_commands(commands)

    logger.info(f"Бот запущен с {len(commands)} командами")
    logger.info(f"API сервер: {BotConstants.API_BASE_URL}")

    # Запуск бота
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
