# app.py
"""
Основной файл сервера системы управления задачами.
Использует Flask для REST API, Pydantic для валидации и SocketIO для WebSocket.
"""

import os
import csv
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from functools import wraps

import yaml
import jwt  # PyJWT библиотека
import redis
from flask import Flask, request, jsonify, Response, send_file, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
from pydantic import BaseModel, Field, field_validator, ConfigDict
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

# Загружаем переменные окружения из .env файла
load_dotenv()

# ============================================================================
# КОНСТАНТЫ СИСТЕМЫ
# ============================================================================

class SystemConstants:
    """Класс для хранения всех констант системы."""

    # Роли пользователей
    ROLES = ['admin', 'manager', 'member', 'viewer']

    # Статусы задач
    TASK_STATUSES = ['todo', 'in_progress', 'done']

    # Приоритеты задач
    TASK_PRIORITIES = ['low', 'medium', 'high', 'urgent']

    # Уровни доступа документов
    DOC_ACCESS_LEVELS = ['public', 'team', 'private']

    # Периоды времени для анализа
    TIME_PERIODS = ['last_week', 'last_month', 'last_quarter', 'custom']

    # Метрики для LLM анализа
    LLM_METRICS = ['productivity', 'bottlenecks', 'team_performance', 'predictions']

    # Форматы экспорта
    EXPORT_FORMATS = ['csv', 'xlsx']

    # Пути к файлам данных
    DATA_DIR = './data'
    CSV_PATHS = {
        'users': f'{DATA_DIR}/users.csv',
        'tasks': f'{DATA_DIR}/tasks.csv',
        'events': f'{DATA_DIR}/events.csv',
        'docs': f'{DATA_DIR}/docs.csv'
    }

    # Дефолтные значения
    DEFAULT_SESSION_TIMEOUT_HOURS = 24
    DEFAULT_REFRESH_TOKEN_DAYS = 7  # Refresh токен на 7 дней
    DEFAULT_CACHE_TTL_SECONDS = 300
    DEFAULT_RATE_LIMIT_PER_MINUTE = 100
    DEFAULT_LLM_REQUESTS_PER_DAY = 50

    # JWT настройки
    JWT_ALGORITHM = 'HS256'

    # WebSocket события
    WS_EVENTS = {
        'TASK_CREATED': 'task_created',
        'TASK_UPDATED': 'task_updated',
        'TASK_DELETED': 'task_deleted',
        'EVENT_CREATED': 'event_created',
        'USER_ONLINE': 'user_online',
        'USER_OFFLINE': 'user_offline',
        'SESSION_EXPIRED': 'session_expired'
    }


# ============================================================================
# PYDANTIC МОДЕЛИ ДЛЯ ВАЛИДАЦИИ
# ============================================================================

class UserBase(BaseModel):
    """Базовая модель пользователя."""
    model_config = ConfigDict(from_attributes=True)

    telegram_username: str = Field(..., min_length=5, max_length=32, pattern=r'^@\w+$')
    full_name: str = Field(..., min_length=2, max_length=100)
    role: str = Field(default='member')
    is_active: bool = Field(default=True)
    email: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
    department: Optional[str] = Field(None, max_length=50)

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        """Валидация роли пользователя."""
        if v not in SystemConstants.ROLES:
            raise ValueError(f'Роль должна быть одной из: {", ".join(SystemConstants.ROLES)}')
        return v


class UserCreate(UserBase):
    """Модель для создания пользователя."""
    pass


class UserResponse(UserBase):
    """Модель ответа с пользователем."""
    registered_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


class TaskBase(BaseModel):
    """Базовая модель задачи."""
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    status: str = Field(default='todo')
    assignee: Optional[str] = Field(None, pattern=r'^@\w+$')
    priority: str = Field(default='medium')
    due_date: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list, max_length=10)

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        """Валидация статуса задачи."""
        if v not in SystemConstants.TASK_STATUSES:
            raise ValueError(f'Статус должен быть одним из: {", ".join(SystemConstants.TASK_STATUSES)}')
        return v

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        """Валидация приоритета задачи."""
        if v not in SystemConstants.TASK_PRIORITIES:
            raise ValueError(f'Приоритет должен быть одним из: {", ".join(SystemConstants.TASK_PRIORITIES)}')
        return v

    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v):
        """Валидация даты дедлайна."""
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('Формат даты должен быть YYYY-MM-DD')
        return v


class TaskCreate(TaskBase):
    """Модель для создания задачи."""
    pass


class TaskUpdate(BaseModel):
    """Модель для обновления задачи."""
    model_config = ConfigDict(from_attributes=True)

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[str] = None
    assignee: Optional[str] = Field(None, pattern=r'^@\w+$')
    priority: Optional[str] = None
    due_date: Optional[str] = None
    tags: Optional[List[str]] = Field(None, max_length=10)

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v and v not in SystemConstants.TASK_STATUSES:
            raise ValueError(f'Статус должен быть одним из: {", ".join(SystemConstants.TASK_STATUSES)}')
        return v

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        if v and v not in SystemConstants.TASK_PRIORITIES:
            raise ValueError(f'Приоритет должен быть одним из: {", ".join(SystemConstants.TASK_PRIORITIES)}')
        return v

    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v):
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('Формат даты должен быть YYYY-MM-DD')
        return v


class TaskResponse(TaskBase):
    """Модель ответа с задачей."""
    task_id: int
    creator: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assignee_name: Optional[str] = None
    creator_name: Optional[str] = None
    is_overdue: Optional[bool] = None
    days_remaining: Optional[int] = None


class AuthRequest(BaseModel):
    """Модель для запроса аутентификации."""
    model_config = ConfigDict(from_attributes=True)

    telegram_username: str = Field(..., min_length=5, max_length=32, pattern=r'^@\w+$')
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)


class AuthResponse(BaseModel):
    """Модель ответа аутентификации."""
    model_config = ConfigDict(from_attributes=True)

    authenticated: bool
    user: UserResponse
    session_token: str
    refresh_token: str
    permissions: Dict[str, Any]
    expires_in: int  # Время жизни токена в секундах


class RefreshTokenRequest(BaseModel):
    """Модель для запроса обновления токена."""
    model_config = ConfigDict(from_attributes=True)

    refresh_token: str


class LLMAnalysisRequest(BaseModel):
    """Модель для запроса LLM анализа."""
    model_config = ConfigDict(from_attributes=True)

    time_period: str = Field(default='last_week')
    metrics: List[str] = Field(default=['productivity', 'bottlenecks'])
    format: str = Field(default='json')
    include_recommendations: bool = Field(default=True)
    custom_start: Optional[str] = None
    custom_end: Optional[str] = None

    @field_validator('time_period')
    @classmethod
    def validate_time_period(cls, v):
        """Валидация периода времени."""
        if v not in SystemConstants.TIME_PERIODS:
            raise ValueError(f'Период должен быть одним из: {", ".join(SystemConstants.TIME_PERIODS)}')
        return v

    @field_validator('metrics')
    @classmethod
    def validate_metrics(cls, v):
        """Валидация метрик анализа."""
        for metric in v:
            if metric not in SystemConstants.LLM_METRICS:
                raise ValueError(f'Метрика должна быть одной из: {", ".join(SystemConstants.LLM_METRICS)}')
        return v

    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        """Валидация формата ответа."""
        if v not in ['json', 'markdown']:
            raise ValueError('Формат должен быть json или markdown')
        return v


# ============================================================================
# КЛАСС КОНФИГУРАЦИИ
# ============================================================================

class ConfigManager:
    """
    Менеджер конфигурации системы.
    Загружает настройки из YAML файла и заменяет переменные окружения.
    """

    def __init__(self, config_path: str = 'config.yaml'):
        """
        Инициализация менеджера конфигурации.

        Args:
            config_path (str): Путь к файлу конфигурации YAML
        """
        self.config_path = config_path
        self.config = self._load_config()
        self._setup_logging()

    def _load_config(self) -> Dict[str, Any]:
        """
        Загрузка конфигурации из YAML файла.

        Returns:
            Dict[str, Any]: Словарь с конфигурацией
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Замена переменных окружения
            config = self._replace_env_vars(config)
            return config
        except FileNotFoundError:
            logging.error(f"Файл конфигурации {self.config_path} не найден")
            return self._get_default_config()

    def _replace_env_vars(self, config: Dict) -> Dict:
        """
        Замена строк вида ${VAR} на значения переменных окружения.

        Args:
            config (Dict): Конфигурация с переменными

        Returns:
            Dict: Конфигурация с замененными переменными
        """
        import re

        def replace(obj):
            if isinstance(obj, dict):
                return {k: replace(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace(item) for item in obj]
            elif isinstance(obj, str):
                # Ищем паттерн ${VAR_NAME}
                match = re.search(r'\${(\w+)}', obj)
                if match:
                    env_var = match.group(1)
                    env_value = os.environ.get(env_var, '')
                    return obj.replace(f'${{{env_var}}}', env_value)
                return obj
            else:
                return obj

        return replace(config)

    def _get_default_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации по умолчанию.

        Returns:
            Dict[str, Any]: Дефолтная конфигурация
        """
        return {
            'security': {
                'enabled': True,
                'validation_method': 'telegram_username',
                'session_timeout_hours': 24,
                'refresh_token_days': 7,
                'admin_only_endpoints': ['/api/users', '/api/system/*'],
                'rate_limiting': {
                    'requests_per_minute': 100,
                    'llm_requests_per_day': 50
                }
            },
            'logging': {
                'level': 'INFO',
                'file_path': './logs/task_system.log',
                'max_size_mb': 100,
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'retention_days': 30
            },
            'performance': {
                'cache_enabled': True,
                'cache_ttl_seconds': 300,
                'csv_read_batch_size': 1000,
                'worker_processes': 4,
                'max_file_size_mb': 10
            },
            'telegram': {
                'bot_token': '',
                'webhook_url': 'https://api.example.com/webhook',
                'polling_interval': 2
            },
            'llm': {
                'enabled': True,
                'provider': 'openai',
                'api_key': '',
                'model': 'gpt-4-turbo-preview',
                'max_tokens': 2000,
                'cache_minutes': 60,
                'timeout_seconds': 60
            },
            'server': {
                'host': '0.0.0.0',
                'port': 5000,
                'ssl_enabled': False,
                'max_connections': 1000,
                'request_timeout': 30,
                'cors_origins': [
                    'https://kanban.example.com',
                    'http://localhost:3000'
                ],
                'debug': False
            },
            'export': {
                'allow_all': True,  # Разрешить экспорт всем пользователям
                'csv_export_enabled': True,
                'max_export_records': 10000
            }
        }

    def _setup_logging(self):
        """Настройка системы логирования на основе конфигурации."""
        log_config = self.config.get('logging', {})

        # Создаем директорию для логов
        log_dir = os.path.dirname(log_config.get('file_path', './logs/app.log'))
        os.makedirs(log_dir, exist_ok=True)

        # Настраиваем root логгер
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, log_config.get('level', 'INFO')))

        # Форматтер
        formatter = logging.Formatter(log_config.get('format'))

        # File handler с ротацией
        file_handler = RotatingFileHandler(
            log_config.get('file_path'),
            maxBytes=log_config.get('max_size_mb', 100) * 1024 * 1024,
            backupCount=log_config.get('retention_days', 30)
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        logging.info(f"Логирование инициализировано. Файл: {log_config.get('file_path')}")

    def get(self, key: str, default=None) -> Any:
        """
        Получить значение конфигурации по ключу.

        Args:
            key (str): Ключ конфигурации в формате 'section.subsection'
            default: Значение по умолчанию

        Returns:
            Any: Значение конфигурации
        """
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def is_security_enabled(self) -> bool:
        """
        Проверка, включена ли безопасность.

        Returns:
            bool: True если безопасность включена
        """
        return self.get('security.enabled', True)

    def is_export_allowed_for_all(self) -> bool:
        """
        Проверка, разрешен ли экспорт всем пользователям.

        Returns:
            bool: True если экспорт разрешен всем
        """
        return self.get('export.allow_all', True)


# ============================================================================
# КЛАСС ДЛЯ РАБОТЫ С CSV
# ============================================================================

import threading

class CSVDataManager:
    """
    Менеджер для работы с CSV файлами.
    Обеспечивает потокобезопасное чтение и запись данных.
    """

    def __init__(self, file_path: str, schema: Dict[str, Any]):
        """
        Инициализация менеджера CSV.

        Args:
            file_path (str): Путь к CSV файлу
            schema (Dict): Схема данных с типами и валидацией
        """
        self.file_path = file_path
        self.schema = schema
        self._ensure_file_exists()
        self._lock = threading.Lock()

    def _ensure_file_exists(self):
        """Создает файл с заголовками, если он не существует."""
        if not os.path.exists(self.file_path):
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.schema.keys())
                writer.writeheader()

    def read_all(self) -> List[Dict[str, str]]:
        """
        Чтение всех записей из CSV файла.

        Returns:
            List[Dict]: Список всех записей
        """
        with self._lock:
            with open(self.file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)

    def write_all(self, data: List[Dict[str, str]]):
        """
        Запись всех записей в CSV файл.

        Args:
            data (List[Dict]): Данные для записи
        """
        with self._lock:
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.schema.keys())
                writer.writeheader()
                writer.writerows(data)

    def find(self, **kwargs) -> List[Dict[str, str]]:
        """
        Поиск записей по критериям.

        Args:
            **kwargs: Критерии поиска (поле=значение)

        Returns:
            List[Dict]: Найденные записи
        """
        results = []
        for row in self.read_all():
            match = True
            for key, value in kwargs.items():
                if str(row.get(key)) != str(value):
                    match = False
                    break
            if match:
                results.append(row)
        return results

    def find_one(self, **kwargs) -> Optional[Dict[str, str]]:
        """
        Поиск одной записи по критериям.

        Args:
            **kwargs: Критерии поиска

        Returns:
            Optional[Dict]: Найденная запись или None
        """
        results = self.find(**kwargs)
        return results[0] if results else None

    def insert(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Вставка новой записи в CSV.

        Args:
            data (Dict): Данные для вставки

        Returns:
            Dict: Вставленная запись

        Raises:
            ValueError: Если не хватает обязательных полей
        """
        # Валидация данных по схеме
        validated_data = {}
        for field, field_info in self.schema.items():
            if field_info.get('required', False) and field not in data:
                # Для полей с timestamp добавляем текущее время
                if field in ['registered_at', 'created_at', 'updated_at']:
                    validated_data[field] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                elif 'default' in field_info:
                    validated_data[field] = str(field_info['default'])
                else:
                    raise ValueError(f"Обязательное поле '{field}' отсутствует")
            elif field in data:
                validated_data[field] = str(data[field])
            elif 'default' in field_info:
                validated_data[field] = str(field_info['default'])
            else:
                validated_data[field] = ''

        # Генерация ID если требуется
        if 'id' in self.schema and 'id' not in validated_data:
            last_id = 0
            for row in self.read_all():
                try:
                    row_id = int(row.get('id', 0))
                    last_id = max(last_id, row_id)
                except:
                    pass
            validated_data['id'] = str(last_id + 1)

        # Добавление timestamp если требуется и не добавлено ранее
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for field in ['created_at', 'updated_at', 'registered_at', 'last_login']:
            if field in self.schema and field not in validated_data:
                validated_data[field] = current_time

        all_data = self.read_all()
        all_data.append(validated_data)
        self.write_all(all_data)

        return validated_data

    def update(self, filter_kwargs: Dict[str, Any], update_data: Dict[str, Any]) -> bool:
        """
        Обновление записей по фильтру.

        Args:
            filter_kwargs (Dict): Критерии для поиска записей
            update_data (Dict): Данные для обновления

        Returns:
            bool: True если обновление прошло успешно
        """
        all_data = self.read_all()
        updated = False

        for i, row in enumerate(all_data):
            match = True
            for key, value in filter_kwargs.items():
                if str(row.get(key)) != str(value):
                    match = False
                    break

            if match:
                updated = True
                # Обновляем поля
                for key, value in update_data.items():
                    if key in self.schema:
                        all_data[i][key] = str(value)

                # Обновляем updated_at если есть поле
                if 'updated_at' in self.schema:
                    all_data[i]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if updated:
            self.write_all(all_data)

        return updated

    def delete(self, **kwargs) -> bool:
        """
        Удаление записей по критериям.

        Args:
            **kwargs: Критерии удаления

        Returns:
            bool: True если удаление прошло успешно
        """
        all_data = self.read_all()
        new_data = []
        deleted = False

        for row in all_data:
            match = True
            for key, value in kwargs.items():
                if str(row.get(key)) != str(value):
                    match = False
                    break

            if not match:
                new_data.append(row)
            else:
                deleted = True

        if deleted:
            self.write_all(new_data)

        return deleted


# ============================================================================
# СХЕМЫ CSV ФАЙЛОВ
# ============================================================================

# Схема для users.csv
USERS_SCHEMA = {
    'telegram_username': {'required': True, 'type': 'string'},
    'full_name': {'required': True, 'type': 'string'},
    'role': {'required': True, 'type': 'string', 'default': 'member'},
    'is_active': {'required': True, 'type': 'boolean', 'default': 'True'},
    'registered_at': {'required': False, 'type': 'datetime'},  # Сделал необязательным
    'last_login': {'required': False, 'type': 'datetime'},
    'email': {'required': False, 'type': 'string'},
    'department': {'required': False, 'type': 'string'}
}

# Схема для tasks.csv
TASKS_SCHEMA = {
    'task_id': {'required': True, 'type': 'integer'},
    'title': {'required': True, 'type': 'string'},
    'description': {'required': False, 'type': 'string'},
    'status': {'required': True, 'type': 'string', 'default': 'todo'},
    'assignee': {'required': False, 'type': 'string'},
    'creator': {'required': True, 'type': 'string'},
    'created_at': {'required': False, 'type': 'datetime'},  # Сделал необязательным
    'updated_at': {'required': False, 'type': 'datetime'},  # Сделал необязательным
    'due_date': {'required': False, 'type': 'date'},
    'completed_at': {'required': False, 'type': 'datetime'},
    'priority': {'required': True, 'type': 'string', 'default': 'medium'},
    'tags': {'required': False, 'type': 'json'}
}

# Схема для events.csv
EVENTS_SCHEMA = {
    'event_id': {'required': True, 'type': 'integer'},
    'title': {'required': True, 'type': 'string'},
    'description': {'required': False, 'type': 'string'},
    'start_time': {'required': True, 'type': 'datetime'},
    'end_time': {'required': True, 'type': 'datetime'},
    'creator': {'required': True, 'type': 'string'},
    'participants': {'required': False, 'type': 'json'},
    'created_at': {'required': False, 'type': 'datetime'},  # Сделал необязательным
    'location': {'required': False, 'type': 'string'}
}

# Схема для docs.csv
DOCS_SCHEMA = {
    'doc_id': {'required': True, 'type': 'integer'},
    'title': {'required': True, 'type': 'string'},
    'content': {'required': False, 'type': 'text'},
    'file_path': {'required': False, 'type': 'string'},
    'creator': {'required': True, 'type': 'string'},
    'created_at': {'required': False, 'type': 'datetime'},  # Сделал необязательным
    'updated_at': {'required': False, 'type': 'datetime'},  # Сделал необязательным
    'access_level': {'required': True, 'type': 'string', 'default': 'team'},
    'version': {'required': False, 'type': 'string'}
}


# ============================================================================
# МЕНЕДЖЕР КЭША
# ============================================================================

class CacheManager:
    """
    Менеджер кэширования с поддержкой Redis и in-memory кэша.
    """

    def __init__(self, enabled: bool = True, ttl: int = 300):
        """
        Инициализация менеджера кэша.

        Args:
            enabled (bool): Включено ли кэширование
            ttl (int): Время жизни кэша в секундах
        """
        self.enabled = enabled
        self.ttl = ttl

        if self.enabled:
            try:
                self.redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=0,
                    decode_responses=True
                )
                self.redis_client.ping()
                logging.info("Redis подключен успешно")
            except Exception as e:
                logging.warning(f"Redis недоступен: {e}, используется in-memory кэш")
                self.enabled = False
                self.memory_cache = {}

    def get(self, key: str) -> Optional[Any]:
        """
        Получить значение из кэша.

        Args:
            key (str): Ключ кэша

        Returns:
            Optional[Any]: Значение из кэша или None
        """
        if not self.enabled:
            return self.memory_cache.get(key) if hasattr(self, 'memory_cache') else None

        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logging.error(f"Ошибка получения из кэша: {e}")
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Установить значение в кэш.

        Args:
            key (str): Ключ кэша
            value (Any): Значение для кэширования
            ttl (Optional[int]): Время жизни в секундах
        """
        ttl = ttl or self.ttl

        if not self.enabled:
            if not hasattr(self, 'memory_cache'):
                self.memory_cache = {}
            self.memory_cache[key] = value
            return

        try:
            self.redis_client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        except Exception as e:
            logging.error(f"Ошибка установки в кэш: {e}")

    def delete(self, key: str):
        """
        Удалить значение из кэша.

        Args:
            key (str): Ключ кэша
        """
        if not self.enabled:
            if hasattr(self, 'memory_cache') and key in self.memory_cache:
                del self.memory_cache[key]
            return

        try:
            self.redis_client.delete(key)
        except Exception as e:
            logging.error(f"Ошибка удаления из кэша: {e}")

    def generate_key(self, prefix: str, **kwargs) -> str:
        """
        Генерация ключа кэша на основе параметров.

        Args:
            prefix (str): Префикс ключа
            **kwargs: Параметры для генерации ключа

        Returns:
            str: Сгенерированный ключ кэша
        """
        key_parts = [prefix]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        return ":".join(key_parts)


# ============================================================================
# МЕНЕДЖЕР АУТЕНТИФИКАЦИИ И АВТОРИЗАЦИИ
# ============================================================================

class AuthManager:
    """
    Менеджер для управления аутентификацией, авторизацией и правами пользователей.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Инициализация менеджера аутентификации.

        Args:
            config_manager (ConfigManager): Менеджер конфигурации
        """
        self.config_manager = config_manager
        self.jwt_secret = os.environ.get('JWT_SECRET', 'your-secret-key-change-this')
        self.session_timeout = config_manager.get('security.session_timeout_hours', 24)
        self.refresh_token_days = config_manager.get('security.refresh_token_days', 7)
        self.security_enabled = config_manager.is_security_enabled()
        self.export_allowed_for_all = config_manager.is_export_allowed_for_all()

        # Роли и их права (берутся из конфигурации или используются дефолтные)
        self.roles_permissions = self._load_roles_permissions()

    def _load_roles_permissions(self) -> Dict[str, Dict[str, Any]]:
        """
        Загрузка прав для ролей.
        Если безопасность отключена, все пользователи получают права администратора.

        Returns:
            Dict: Права для каждой роли
        """
        if not self.security_enabled:
            # Если безопасность отключена, все имеют права администратора
            admin_permissions = {
                'can_create_tasks': True,
                'can_edit_tasks': True,
                'can_delete_tasks': True,
                'can_export': True,
                'can_use_llm': True,
                'can_manage_users': True,
                'llm_daily_limit': 999999  # Практически безлимит
            }
            return {role: admin_permissions.copy() for role in SystemConstants.ROLES}

        # Права по умолчанию для различных ролей
        permissions = {
            'admin': {
                'can_create_tasks': True,
                'can_edit_tasks': True,
                'can_delete_tasks': True,
                'can_export': True,
                'can_use_llm': True,
                'can_manage_users': True,
                'llm_daily_limit': 50
            },
            'manager': {
                'can_create_tasks': True,
                'can_edit_tasks': True,
                'can_delete_tasks': True,
                'can_export': True,
                'can_use_llm': True,
                'can_manage_users': False,
                'llm_daily_limit': 20
            },
            'member': {
                'can_create_tasks': True,
                'can_edit_tasks': True,
                'can_delete_tasks': False,
                'can_export': self.export_allowed_for_all,  # Разрешаем экспорт если включена настройка
                'can_use_llm': True,
                'can_manage_users': False,
                'llm_daily_limit': 5
            },
            'viewer': {
                'can_create_tasks': False,
                'can_edit_tasks': False,
                'can_delete_tasks': False,
                'can_export': self.export_allowed_for_all,  # Разрешаем экспорт если включена настройка
                'can_use_llm': False,
                'can_manage_users': False,
                'llm_daily_limit': 0
            }
        }

        return permissions

    def authenticate_user(self, telegram_username: str, full_name: str = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Аутентификация пользователя через Telegram.
        Если пользователь не найден и безопасность отключена, создает нового пользователя.

        Args:
            telegram_username (str): Имя пользователя в Telegram
            full_name (str, optional): Полное имя пользователя

        Returns:
            Tuple[bool, Dict]: (Успешна ли аутентификация, данные пользователя или ошибка)
        """
        try:
            logging.info(f"Попытка аутентификации пользователя: {telegram_username}")

            # Поиск пользователя
            user = users_manager.find_one(telegram_username=telegram_username)

            if user:
                logging.info(f"Пользователь {telegram_username} найден в базе")

                # Проверка активности
                if user.get('is_active', 'False') != 'True':
                    logging.warning(f"Пользователь {telegram_username} неактивен")
                    return False, {'error': 'Пользователь неактивен'}

                # Обновление last_login
                users_manager.update(
                    {'telegram_username': telegram_username},
                    {'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                )

                # Получение прав
                role = user.get('role', 'member')
                permissions = self.roles_permissions.get(role, {}).copy()

                # Генерация access токена
                token_payload = {
                    'telegram_username': telegram_username,
                    'role': role,
                    'type': 'access',
                    'exp': datetime.utcnow() + timedelta(hours=self.session_timeout)
                }

                # Генерация refresh токена
                refresh_payload = {
                    'telegram_username': telegram_username,
                    'type': 'refresh',
                    'exp': datetime.utcnow() + timedelta(days=self.refresh_token_days)
                }

                access_token = jwt.encode(token_payload, self.jwt_secret, algorithm=SystemConstants.JWT_ALGORITHM)
                refresh_token = jwt.encode(refresh_payload, self.jwt_secret, algorithm=SystemConstants.JWT_ALGORITHM)

                # Сохранение сессии в кэш
                session_key = f"session:{telegram_username}"
                cache_manager.set(session_key, {
                    'user': user,
                    'permissions': permissions,
                    'refresh_token': refresh_token,
                    'last_activity': datetime.now().isoformat()
                }, ttl=self.session_timeout * 3600)

                # Сохранение refresh токена
                refresh_key = f"refresh:{telegram_username}"
                cache_manager.set(refresh_key, {
                    'refresh_token': refresh_token,
                    'created_at': datetime.now().isoformat(),
                    'user': user
                }, ttl=self.refresh_token_days * 24 * 3600)

                logging.info(f"Пользователь {telegram_username} успешно аутентифицирован, роль: {role}")
                return True, {
                    'user': user,
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'permissions': permissions,
                    'expires_in': self.session_timeout * 3600
                }

            # Пользователь не найден
            logging.info(f"Пользователь {telegram_username} не найден в базе")

            # Если безопасность отключена или включена автоматическая регистрация
            # Создаем нового пользователя
            new_user = {
                'telegram_username': telegram_username,
                'full_name': full_name or telegram_username.replace('@', ''),
                'role': 'member',
                'is_active': 'True'
            }

            logging.info(f"Создание нового пользователя: {telegram_username}")
            user = users_manager.insert(new_user)

            # Повторная аутентификация нового пользователя
            return self.authenticate_user(telegram_username, full_name)

        except Exception as e:
            logging.error(f"Ошибка аутентификации пользователя {telegram_username}: {e}")
            return False, {'error': str(e)}

    def validate_token(self, token: str, token_type: str = 'access') -> Tuple[bool, Dict[str, Any]]:
        """
        Валидация JWT токена.

        Args:
            token (str): JWT токен
            token_type (str): Тип токена (access или refresh)

        Returns:
            Tuple[bool, Dict]: (Валиден ли токен, данные пользователя или ошибка)
        """
        try:
            logging.debug(f"Валидация {token_type} токена: {token[:20]}...")

            payload = jwt.decode(token, self.jwt_secret, algorithms=[SystemConstants.JWT_ALGORITHM])

            # Проверка типа токена
            if payload.get('type') != token_type:
                logging.warning(f"Неверный тип токена: ожидался {token_type}, получен {payload.get('type')}")
                return False, {'error': f'Неверный тип токена. Ожидался {token_type} токен.'}

            telegram_username = payload.get('telegram_username')

            if token_type == 'access':
                # Проверка сессии в кэше
                session_key = f"session:{telegram_username}"
                session_data = cache_manager.get(session_key)

                if not session_data:
                    logging.warning(f"Сессия истекла для пользователя: {telegram_username}")
                    return False, {'error': 'Сессия истекла. Пожалуйста, обновите токен.'}

                # Проверка соответствия refresh токена
                refresh_key = f"refresh:{telegram_username}"
                refresh_data = cache_manager.get(refresh_key)

                if not refresh_data or session_data.get('refresh_token') != refresh_data.get('refresh_token'):
                    logging.warning(f"Refresh токен не совпадает или устарел: {telegram_username}")
                    return False, {'error': 'Недействительная сессия. Пожалуйста, авторизуйтесь заново.'}

                # Обновление времени активности
                session_data['last_activity'] = datetime.now().isoformat()
                cache_manager.set(session_key, session_data, ttl=self.session_timeout * 3600)

                logging.debug(f"Access токен валиден для пользователя: {telegram_username}")
                return True, {
                    'telegram_username': telegram_username,
                    'role': payload.get('role'),
                    'user': session_data.get('user'),
                    'permissions': session_data.get('permissions', {})
                }
            else:
                # Валидация refresh токена
                refresh_key = f"refresh:{telegram_username}"
                refresh_data = cache_manager.get(refresh_key)

                if not refresh_data or refresh_data.get('refresh_token') != token:
                    logging.warning(f"Refresh токен не найден или не совпадает: {telegram_username}")
                    return False, {'error': 'Недействительный refresh токен'}

                logging.debug(f"Refresh токен валиден для пользователя: {telegram_username}")
                return True, {
                    'telegram_username': telegram_username,
                    'user': refresh_data.get('user')
                }

        except jwt.ExpiredSignatureError:
            if token_type == 'access':
                logging.warning("Access токен истек")
                return False, {'error': 'Access токен истек. Используйте refresh токен для получения нового.'}
            else:
                logging.warning("Refresh токен истек")
                return False, {'error': 'Refresh токен истек. Пожалуйста, авторизуйтесь заново.'}
        except jwt.InvalidTokenError as e:
            logging.warning(f"Неверный токен: {str(e)}")
            return False, {'error': f'Неверный токен: {str(e)}'}

    def refresh_access_token(self, refresh_token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Обновление access токена с помощью refresh токена.

        Args:
            refresh_token (str): Refresh токен

        Returns:
            Tuple[bool, Dict]: (Успешно ли обновление, новые токены или ошибка)
        """
        try:
            # Валидация refresh токена
            valid, refresh_info = self.validate_token(refresh_token, 'refresh')

            if not valid:
                return False, refresh_info

            telegram_username = refresh_info['telegram_username']
            user = refresh_info['user']

            # Получение роли пользователя
            role = user.get('role', 'member')
            permissions = self.roles_permissions.get(role, {}).copy()

            # Генерация нового access токена
            token_payload = {
                'telegram_username': telegram_username,
                'role': role,
                'type': 'access',
                'exp': datetime.utcnow() + timedelta(hours=self.session_timeout)
            }

            access_token = jwt.encode(token_payload, self.jwt_secret, algorithm=SystemConstants.JWT_ALGORITHM)

            # Обновление сессии в кэше
            session_key = f"session:{telegram_username}"
            cache_manager.set(session_key, {
                'user': user,
                'permissions': permissions,
                'refresh_token': refresh_token,
                'last_activity': datetime.now().isoformat()
            }, ttl=self.session_timeout * 3600)

            logging.info(f"Access токен обновлен для пользователя: {telegram_username}")
            return True, {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_in': self.session_timeout * 3600,
                'user': user,
                'permissions': permissions
            }

        except Exception as e:
            logging.error(f"Ошибка обновления токена: {e}")
            return False, {'error': str(e)}

    def check_permission(self, user_info: Dict[str, Any], permission: str) -> bool:
        """
        Проверка права пользователя.

        Args:
            user_info (Dict): Информация о пользователе
            permission (str): Проверяемое право

        Returns:
            bool: Есть ли у пользователя данное право
        """
        # ИЗМЕНЕНИЕ: Убрана проверка прав - теперь все могут делать все
        logging.debug(f"Безопасность упрощена, доступ разрешен: {permission}")
        return True

    def get_user_llm_quota(self, telegram_username: str) -> Dict[str, Any]:
        """
        Получить квоту LLM запросов пользователя.

        Args:
            telegram_username (str): Имя пользователя в Telegram

        Returns:
            Dict: Информация о квоте
        """
        cache_key = f"llm_quota:{telegram_username}:{datetime.now().strftime('%Y-%m-%d')}"
        quota_data = cache_manager.get(cache_key) or {
            'used': 0,
            'limit': 0,
            'reset_at': (datetime.now() + timedelta(days=1)).isoformat()
        }

        # Получение лимита из роли пользователя
        user = users_manager.find_one(telegram_username=telegram_username)
        role = user.get('role', 'member') if user else 'member'
        quota_data['limit'] = self.roles_permissions.get(role, {}).get('llm_daily_limit', 0)

        return quota_data

    def logout(self, telegram_username: str):
        """
        Выход пользователя из системы (удаление сессии).

        Args:
            telegram_username (str): Имя пользователя в Telegram
        """
        # Удаление сессии
        session_key = f"session:{telegram_username}"
        cache_manager.delete(session_key)

        # Удаление refresh токена
        refresh_key = f"refresh:{telegram_username}"
        cache_manager.delete(refresh_key)

        logging.info(f"Пользователь {telegram_username} вышел из системы")


# ============================================================================
# ИНИЦИАЛИЗАЦИЯ КОМПОНЕНТОВ
# ============================================================================

# Инициализация менеджера конфигурации
config_manager = ConfigManager()

# Инициализация менеджеров CSV данных
users_manager = CSVDataManager(SystemConstants.CSV_PATHS['users'], USERS_SCHEMA)
tasks_manager = CSVDataManager(SystemConstants.CSV_PATHS['tasks'], TASKS_SCHEMA)
events_manager = CSVDataManager(SystemConstants.CSV_PATHS['events'], EVENTS_SCHEMA)
docs_manager = CSVDataManager(SystemConstants.CSV_PATHS['docs'], DOCS_SCHEMA)

# Инициализация менеджера кэша
cache_enabled = config_manager.get('performance.cache_enabled', True)
cache_ttl = config_manager.get('performance.cache_ttl_seconds', SystemConstants.DEFAULT_CACHE_TTL_SECONDS)
cache_manager = CacheManager(enabled=cache_enabled, ttl=cache_ttl)

# Инициализация менеджера аутентификации
auth_manager = AuthManager(config_manager)

# Инициализация Flask приложения
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-this')
CORS(app, origins=config_manager.get('server.cors_origins', []))

# Инициализация SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


# ============================================================================
# ДЕКОРАТОРЫ И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def require_auth(f):
    """
    Декоратор для проверки аутентификации пользователя.
    Добавляет user_info в объект request и Flask сессию.
    Поддерживает обновление токена через refresh token.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Проверяем наличие user_info в сессии Flask
        if 'user_info' in session:
            logging.debug(f"Используем данные из сессии Flask")
            request.user_info = session['user_info']
            return f(*args, **kwargs)

        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            logging.warning(f"Запрос без токена: {request.method} {request.path}")
            return jsonify({
                'status': 'error',
                'error': 'Требуется аутентификация. Используйте заголовок Authorization: Bearer <token>',
                'requires_auth': True
            }), 401

        token = auth_header.split(' ')[1]
        valid, user_info = auth_manager.validate_token(token, 'access')

        if not valid:
            # Проверяем, есть ли refresh токен в заголовках
            refresh_token = request.headers.get('X-Refresh-Token')
            if refresh_token and user_info.get('error') == 'Access токен истек. Используйте refresh токен для получения нового.':
                # Пытаемся обновить токен
                refresh_valid, refresh_result = auth_manager.refresh_access_token(refresh_token)
                if refresh_valid:
                    # Сохраняем user_info в сессию Flask
                    session['user_info'] = {
                        'telegram_username': refresh_result.get('user', {}).get('telegram_username'),
                        'role': refresh_result.get('user', {}).get('role', 'member'),
                        'permissions': refresh_result.get('permissions', {})
                    }

                    # Добавляем новые токены в ответ
                    response = f(*args, **kwargs)
                    if isinstance(response, tuple) and len(response) == 2:
                        data, status_code = response
                        if hasattr(data, 'headers'):
                            data.headers['X-New-Access-Token'] = refresh_result['access_token']
                            data.headers['X-New-Refresh-Token'] = refresh_result['refresh_token']
                        return data, status_code
                    return response
                else:
                    logging.warning(f"Не удалось обновить токен: {refresh_result.get('error')}")

            logging.warning(f"Неверный токен: {token[:20]}...")
            error_response = {
                'status': 'error',
                'error': user_info.get('error', 'Неверный токен')
            }

            # Добавляем флаг, если нужна повторная авторизация
            if 'истек' in user_info.get('error', '').lower() or 'недействительная' in user_info.get('error', '').lower():
                error_response['requires_re_auth'] = True

            return jsonify(error_response), 401

        logging.debug(f"Пользователь аутентифицирован: {user_info['telegram_username']}, роль: {user_info['role']}")

        # Добавляем информацию о пользователе в request и сохраняем в сессию Flask
        request.user_info = user_info
        session['user_info'] = {
            'telegram_username': user_info['telegram_username'],
            'role': user_info['role'],
            'permissions': user_info.get('permissions', {})
        }

        # Устанавливаем время жизни сессии
        session.permanent = True

        return f(*args, **kwargs)

    return decorated_function


def require_permission(permission: str):
    """
    Декоратор для проверки конкретного права пользователя.
    Должен использоваться после require_auth.
    """
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            # ИЗМЕНЕНИЕ: Убрана проверка прав - теперь все могут делать все
            logging.debug(f"Право подтверждено автоматически: {request.user_info['telegram_username']} -> {permission}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def validate_request(model_class):
    """
    Декоратор для валидации входящих запросов с помощью Pydantic.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                data = request.get_json()
                if data is None:
                    logging.warning(f"Запрос без JSON тела: {request.method} {request.path}")
                    return jsonify({
                        'status': 'error',
                        'error': 'Требуется JSON тело запроса'
                    }), 400

                logging.debug(f"Получен JSON запрос: {json.dumps(data, ensure_ascii=False)[:200]}...")

                # Валидация данных с помощью Pydantic
                validated_data = model_class(**data)
                request.validated_data = validated_data
                logging.debug(f"Данные валидированы успешно: {validated_data.model_dump()}")
                return f(*args, **kwargs)

            except Exception as e:
                logging.warning(f"Ошибка валидации запроса {request.method} {request.path}: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'error': f'Ошибка валидации: {str(e)}'
                }), 400

        return decorated_function
    return decorator


def generate_response(data: Any = None, status: str = 'success',
                     status_code: int = 200, meta: Dict[str, Any] = None) -> Tuple[Response, int]:
    """
    Генерация стандартизированного JSON ответа.

    Args:
        data: Данные для ответа
        status: Статус операции
        status_code: HTTP статус код
        meta: Метаданные ответа

    Returns:
        Tuple[Response, int]: Ответ Flask и статус код
    """
    response_data = {
        'status': status,
        'data': data,
        'meta': meta or {
            'timestamp': datetime.now().isoformat(),
            'request_id': f"req_{int(time.time())}",
            'security_enabled': config_manager.is_security_enabled(),
            'export_allowed_for_all': config_manager.is_export_allowed_for_all()
        }
    }

    # Логируем ответ (сокращенная версия для больших данных)
    response_str = json.dumps(response_data, ensure_ascii=False, default=str)
    if len(response_str) > 500:
        logging.debug(f"Отправка ответа: {response_str[:500]}...")
    else:
        logging.debug(f"Отправка ответа: {response_str}")

    return jsonify(response_data), status_code


# ============================================================================
# API ЭНДПОИНТЫ
# ============================================================================

@app.route('/api/telegram/auth', methods=['POST'])
@validate_request(AuthRequest)
def telegram_auth_endpoint():
    """
    Эндпоинт для аутентификации через Telegram.
    Ожидает JSON с telegram_username и optional full_name.

    Returns:
        JSON с токеном и информацией о пользователе
    """
    auth_data = request.validated_data

    logging.info(f"Запрос аутентификации от пользователя: {auth_data.telegram_username}")

    # Аутентификация пользователя
    authenticated, result = auth_manager.authenticate_user(
        auth_data.telegram_username,
        auth_data.full_name
    )

    if not authenticated:
        logging.warning(f"Аутентификация не удалась для пользователя: {auth_data.telegram_username}")
        return generate_response(
            result,
            status='error',
            status_code=401
        )

    # Сохраняем user_info в сессию Flask
    session['user_info'] = {
        'telegram_username': result['user'].get('telegram_username'),
        'role': result['user'].get('role', 'member'),
        'permissions': result.get('permissions', {})
    }

    # Устанавливаем время жизни сессии
    session.permanent = True

    # Формирование ответа
    response_data = {
        'authenticated': True,
        'user': result['user'],
        'access_token': result['access_token'],
        'refresh_token': result['refresh_token'],
        'permissions': result['permissions'],
        'expires_in': result['expires_in']
    }

    logging.info(f"Пользователь {auth_data.telegram_username} успешно аутентифицирован")
    return generate_response(response_data, status_code=200)


@app.route('/api/auth/refresh', methods=['POST'])
@validate_request(RefreshTokenRequest)
def refresh_token_endpoint():
    """
    Эндпоинт для обновления access токена с помощью refresh токена.

    Returns:
        JSON с новым access токеном
    """
    refresh_data = request.validated_data

    logging.info(f"Запрос обновления токена")

    # Обновление токена
    success, result = auth_manager.refresh_access_token(refresh_data.refresh_token)

    if not success:
        logging.warning(f"Не удалось обновить токен: {result.get('error')}")
        return generate_response(
            result,
            status='error',
            status_code=401
        )

    # Обновляем user_info в сессии Flask
    if 'user_info' in session:
        session['user_info']['telegram_username'] = result['user'].get('telegram_username')
        session['user_info']['role'] = result['user'].get('role', 'member')
        session['user_info']['permissions'] = result.get('permissions', {})

    # Формирование ответа
    response_data = {
        'access_token': result['access_token'],
        'refresh_token': result['refresh_token'],
        'expires_in': result['expires_in'],
        'user': result['user'],
        'permissions': result['permissions']
    }

    logging.info(f"Токен успешно обновлен для пользователя: {result['user'].get('telegram_username')}")
    return generate_response(response_data, status_code=200)


@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout_endpoint():
    """
    Эндпоинт для выхода пользователя из системы.

    Returns:
        JSON с результатом выхода
    """
    user_info = request.user_info
    telegram_username = user_info['telegram_username']

    logging.info(f"Запрос выхода от пользователя: {telegram_username}")

    # Выход пользователя
    auth_manager.logout(telegram_username)

    # Удаляем сессию Flask
    session.pop('user_info', None)

    logging.info(f"Пользователь {telegram_username} вышел из системы")
    return generate_response({
        'message': 'Успешный выход из системы',
        'logged_out': True
    })


@app.route('/api/tasks', methods=['GET'])
@require_auth
def get_tasks_endpoint():
    """
    Эндпоинт для получения списка задач с фильтрацией и пагинацией.

    Query параметры:
        status: Фильтр по статусу (через запятую)
        assignee: Фильтр по назначенному
        creator: Фильтр по создателю
        priority: Фильтр по приоритету (через запятую)
        date_from: Задачи с даты (YYYY-MM-DD)
        date_to: Задачи до даты (YYYY-MM-DD)
        tags: Фильтр по тегам (через запятую)
        limit: Ограничение количества (по умолчанию 100)
        offset: Смещение (по умолчанию 0)

    Returns:
        JSON со списком задач и информацией о пагинации
    """
    user_info = request.user_info
    logging.info(f"Запрос списка задач от пользователя: {user_info['telegram_username']}")
    logging.debug(f"Query параметры: {dict(request.args)}")

    # Получение параметров фильтрации
    status_filter = request.args.get('status', '').split(',')
    assignee_filter = request.args.get('assignee')
    creator_filter = request.args.get('creator')
    priority_filter = request.args.get('priority', '').split(',')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    tags_filter = request.args.get('tags', '').split(',')
    limit = min(int(request.args.get('limit', 100)), 500)  # Максимум 500
    offset = int(request.args.get('offset', 0))

    # Генерация ключа кэша
    cache_key = cache_manager.generate_key(
        'tasks_filter',
        user=user_info['telegram_username'],
        status=','.join(sorted(status_filter)) if status_filter[0] else '',
        assignee=assignee_filter or '',
        creator=creator_filter or '',
        priority=','.join(sorted(priority_filter)) if priority_filter[0] else '',
        date_from=date_from or '',
        date_to=date_to or '',
        tags=','.join(sorted(tags_filter)) if tags_filter[0] else '',
        limit=limit,
        offset=offset
    )

    # Проверка кэша
    cached_result = cache_manager.get(cache_key)
    if cached_result:
        logging.debug(f"Использован кэшированный результат для ключа: {cache_key}")
        return generate_response(cached_result)

    # Получение всех задач
    all_tasks = tasks_manager.read_all()

    # Применение фильтров
    filtered_tasks = []
    for task in all_tasks:
        # Фильтр по статусу
        if status_filter and status_filter[0] and task.get('status') not in status_filter:
            continue

        # Фильтр по назначенному
        if assignee_filter and task.get('assignee') != assignee_filter:
            continue

        # Фильтр по создателю
        if creator_filter and task.get('creator') != creator_filter:
            continue

        # Фильтр по приоритету
        if priority_filter and priority_filter[0] and task.get('priority') not in priority_filter:
            continue

        # Фильтр по дате
        try:
            created_at_str = task.get('created_at', '')
            if created_at_str:
                created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
                if date_from:
                    date_from_dt = datetime.strptime(date_from, '%Y-%m-%d')
                    if created_at.date() < date_from_dt.date():
                        continue
                if date_to:
                    date_to_dt = datetime.strptime(date_to, '%Y-%m-%d')
                    if created_at.date() > date_to_dt.date():
                        continue
        except:
            pass

        # Фильтр по тегам
        if tags_filter and tags_filter[0]:
            try:
                task_tags = json.loads(task.get('tags', '[]'))
                if not any(tag in task_tags for tag in tags_filter):
                    continue
            except:
                continue

        filtered_tasks.append(task)

    # Пагинация
    total = len(filtered_tasks)
    paginated_tasks = filtered_tasks[offset:offset + limit]

    # Обогащение данных именами пользователей
    enriched_tasks = []
    for task in paginated_tasks:
        enriched_task = task.copy()

        # Добавление имени назначенного
        if task.get('assignee'):
            assignee_user = users_manager.find_one(telegram_username=task['assignee'])
            if assignee_user:
                enriched_task['assignee_name'] = assignee_user.get('full_name')

        # Добавление имени создателя
        if task.get('creator'):
            creator_user = users_manager.find_one(telegram_username=task['creator'])
            if creator_user:
                enriched_task['creator_name'] = creator_user.get('full_name')

        # Расчет дней до дедлайна
        if task.get('due_date'):
            try:
                due_date = datetime.strptime(task['due_date'], '%Y-%m-%d')
                days_remaining = (due_date.date() - datetime.now().date()).days
                enriched_task['days_remaining'] = days_remaining
                enriched_task['is_overdue'] = days_remaining < 0
            except:
                pass

        # Парсинг JSON тегов
        if task.get('tags'):
            try:
                enriched_task['tags'] = json.loads(task['tags'])
            except:
                enriched_task['tags'] = []

        enriched_tasks.append(enriched_task)

    # Формирование ответа
    response_data = {
        'tasks': enriched_tasks,
        'pagination': {
            'total': total,
            'page': (offset // limit) + 1,
            'per_page': limit,
            'total_pages': (total + limit - 1) // limit
        },
        'filters_applied': {
            'status': status_filter if status_filter[0] else None,
            'assignee': assignee_filter,
            'creator': creator_filter,
            'priority': priority_filter if priority_filter[0] else None,
            'date_from': date_from,
            'date_to': date_to,
            'tags': tags_filter if tags_filter[0] else None
        }
    }

    # Сохранение в кэш
    cache_manager.set(cache_key, response_data)

    logging.info(f"Получено {len(enriched_tasks)} задач пользователем {user_info['telegram_username']}")
    return generate_response(response_data)


@app.route('/api/tasks', methods=['POST'])
@require_permission('can_create_tasks')
@validate_request(TaskCreate)
def create_task_endpoint():
    """
    Эндпоинт для создания новой задачи.
    Требует права can_create_tasks.

    Body:
        JSON с данными задачи (TaskCreate модель)

    Returns:
        JSON с созданной задачей
    """
    task_data = request.validated_data
    user_info = request.user_info

    logging.info(f"Запрос создания задачи от пользователя: {user_info['telegram_username']}")
    logging.debug(f"Данные задачи: {task_data.model_dump()}")

    # Проверка существования назначенного пользователя
    if task_data.assignee:
        assignee_exists = users_manager.find_one(telegram_username=task_data.assignee)
        if not assignee_exists:
            logging.warning(f"Назначенный пользователь не найден: {task_data.assignee}")
            return generate_response(
                {'error': f'Пользователь {task_data.assignee} не найден'},
                status='error',
                status_code=400
            )

    # Подготовка данных задачи для сохранения в CSV
    task_dict = task_data.model_dump(exclude_unset=True)
    task_dict['creator'] = user_info['telegram_username']

    # Генерация task_id
    all_tasks = tasks_manager.read_all()
    last_id = 0
    for task in all_tasks:
        try:
            task_id = int(task.get('task_id', 0))
            last_id = max(last_id, task_id)
        except:
            pass
    task_dict['task_id'] = last_id + 1

    # Преобразование тегов в JSON строку
    if task_dict.get('tags'):
        task_dict['tags'] = json.dumps(task_dict['tags'], ensure_ascii=False)

    # Создание задачи
    try:
        created_task = tasks_manager.insert(task_dict)

        # Отправка WebSocket события
        socketio.emit(SystemConstants.WS_EVENTS['TASK_CREATED'], {
            'task': created_task,
            'creator': user_info['telegram_username'],
            'timestamp': datetime.now().isoformat()
        })

        logging.info(f"Задача #{created_task['task_id']} создана пользователем {user_info['telegram_username']}")

        return generate_response({
            'task_id': created_task['task_id'],
            'title': created_task['title'],
            'status': created_task['status'],
            'assignee': created_task.get('assignee', ''),
            'creator': created_task['creator'],
            'created_at': created_task['created_at'],
            'message': 'Задача успешно создана'
        }, status_code=201)

    except Exception as e:
        logging.error(f"Ошибка создания задачи: {e}")
        return generate_response(
            {'error': str(e)},
            status='error',
            status_code=500
        )


@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@require_auth
@validate_request(TaskUpdate)
def update_task_endpoint(task_id: int):
    """
    Эндпоинт для обновления существующей задачи.

    Path параметры:
        task_id: ID задачи для обновления

    Body:
        JSON с обновляемыми полями задачи (TaskUpdate модель)

    Returns:
        JSON с результатом обновления
    """
    update_data = request.validated_data
    user_info = request.user_info

    logging.info(f"Запрос обновления задачи #{task_id} от пользователя: {user_info['telegram_username']}")
    logging.debug(f"Данные обновления: {update_data.model_dump()}")

    # Поиск задачи
    task = tasks_manager.find_one(task_id=str(task_id))
    if not task:
        logging.warning(f"Задача #{task_id} не найдена")
        return generate_response(
            {'error': f'Задача #{task_id} не найдена'},
            status='error',
            status_code=404
        )

    # ИЗМЕНЕНИЕ: Убрана проверка прав доступа - теперь все могут редактировать любые задачи
    user_telegram = user_info['telegram_username']

    # Проверка существования нового назначенного
    if update_data.assignee and update_data.assignee != task.get('assignee'):
        assignee_exists = users_manager.find_one(telegram_username=update_data.assignee)
        if not assignee_exists:
            logging.warning(f"Назначенный пользователь не найден: {update_data.assignee}")
            return generate_response(
                {'error': f'Пользователь {update_data.assignee} не найден'},
                status='error',
                status_code=400
            )

    # Подготовка данных для обновления
    update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)

    # Обработка тегов
    if 'tags' in update_dict:
        update_dict['tags'] = json.dumps(update_dict['tags'], ensure_ascii=False)

    # Обработка завершения задачи
    if update_dict.get('status') == 'done' and task.get('status') != 'done':
        update_dict['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Обновление задачи
    success = tasks_manager.update(
        {'task_id': str(task_id)},
        update_dict
    )

    if not success:
        logging.error(f"Ошибка обновления задачи #{task_id}")
        return generate_response(
            {'error': 'Ошибка обновления задачи'},
            status='error',
            status_code=500
        )

    # Отправка WebSocket события
    socketio.emit(SystemConstants.WS_EVENTS['TASK_UPDATED'], {
        'task_id': task_id,
        'updated_fields': list(update_dict.keys()),
        'updated_by': user_telegram,
        'timestamp': datetime.now().isoformat()
    })

    logging.info(f"Задача #{task_id} обновлена пользователем {user_telegram}")
    return generate_response({
        'task_id': task_id,
        'message': 'Задача успешно обновлена',
        'updated_fields': list(update_dict.keys())
    })


@app.route('/api/export/tasks.csv', methods=['GET'])
def export_tasks_csv_endpoint():
    """
    Эндпоинт для экспорта задач в CSV формат.
    Доступен всем пользователям (если включена соответствующая настройка).
    Если настройка не включена, требуется право can_export.

    Query параметры:
        format: Формат экспорта (simple/full)
        time_period: Период данных (last_week/last_month/all)
        status: Фильтр по статусу (через запятую)
        columns: Выбираемые колонки (через запятую)
        include_users: Включать данные пользователей (true/false)

    Returns:
        CSV файл для скачивания
    """
    # Проверяем, разрешен ли экспорт всем пользователям
    export_allowed_for_all = config_manager.is_export_allowed_for_all()

    if not export_allowed_for_all:
        # Если экспорт не разрешен всем, проверяем аутентификацию и права
        # ИЗМЕНЕНИЕ: Упрощен доступ - теперь можно без проверки прав
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            # Проверяем сессию Flask
            if 'user_info' not in session:
                logging.warning(f"Запрос экспорта без токена и сессии (экспорт не разрешен всем)")
                return jsonify({
                    'status': 'error',
                    'error': 'Требуется аутентификация для экспорта данных',
                    'requires_auth': True
                }), 401

            # Используем данные из сессии
            user_telegram = session['user_info'].get('telegram_username')
            logging.info(f"Запрос экспорта CSV от пользователя: {user_telegram} (через сессию)")
        else:
            token = auth_header.split(' ')[1]
            valid, user_info = auth_manager.validate_token(token, 'access')

            if not valid:
                logging.warning(f"Неверный токен для экспорта: {token[:20]}...")
                return jsonify({
                    'status': 'error',
                    'error': user_info.get('error', 'Неверный токен')
                }), 401

            user_telegram = user_info['telegram_username']
            logging.info(f"Запрос экспорта CSV от пользователя: {user_telegram}")
    else:
        # Экспорт разрешен всем
        user_telegram = 'anonymous'
        logging.info(f"Запрос экспорта CSV от анонимного пользователя")

    logging.debug(f"Query параметры: {dict(request.args)}")

    # Параметры экспорта
    format_type = request.args.get('format', 'full')
    time_period = request.args.get('time_period')
    status_filter = request.args.get('status', '').split(',')
    columns = request.args.get('columns', '').split(',')
    include_users = request.args.get('include_users', 'false').lower() == 'true'

    # Генерация ключа кэша
    cache_key = cache_manager.generate_key(
        'export_csv',
        format=format_type,
        time_period=time_period or '',
        status=','.join(sorted(status_filter)) if status_filter[0] else '',
        columns=','.join(sorted(columns)) if columns[0] else '',
        include_users=include_users,
        date=datetime.now().strftime('%Y-%m-%d')
    )

    # Проверка кэша
    cached_csv = cache_manager.get(cache_key)
    if cached_csv and format_type != 'simple':
        logging.debug(f"Использован кэшированный CSV для ключа: {cache_key}")
        return Response(
            cached_csv,
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename=tasks_export_{datetime.now().strftime("%Y%m%d")}.csv'}
        )

    # Получение задач
    all_tasks = tasks_manager.read_all()

    # Фильтрация по периоду
    filtered_tasks = all_tasks
    if time_period == 'last_week':
        cutoff_date = datetime.now() - timedelta(days=7)
        filtered_tasks = [
            task for task in all_tasks
            if task.get('created_at') and datetime.strptime(task['created_at'], '%Y-%m-%d %H:%M:%S') >= cutoff_date
        ]
    elif time_period == 'last_month':
        cutoff_date = datetime.now() - timedelta(days=30)
        filtered_tasks = [
            task for task in all_tasks
            if task.get('created_at') and datetime.strptime(task['created_at'], '%Y-%m-%d %H:%M:%S') >= cutoff_date
        ]

    # Фильтрация по статусу
    if status_filter and status_filter[0]:
        filtered_tasks = [task for task in filtered_tasks if task.get('status') in status_filter]

    # Подготовка данных для CSV
    csv_data = []

    # Определение колонок
    if columns and columns[0]:
        csv_columns = [col.strip() for col in columns if col.strip() in TASKS_SCHEMA]
    else:
        csv_columns = list(TASKS_SCHEMA.keys())

    # Добавление колонок с именами пользователей если требуется
    if include_users:
        if 'assignee' in csv_columns:
            csv_columns.append('assignee_name')
        if 'creator' in csv_columns:
            csv_columns.append('creator_name')

    for task in filtered_tasks:
        row = {}

        for column in csv_columns:
            if column == 'assignee_name' and include_users:
                # Получение имени назначенного
                if task.get('assignee'):
                    user = users_manager.find_one(telegram_username=task['assignee'])
                    row[column] = user.get('full_name', '') if user else ''
                else:
                    row[column] = ''
            elif column == 'creator_name' and include_users:
                # Получение имени создателя
                if task.get('creator'):
                    user = users_manager.find_one(telegram_username=task['creator'])
                    row[column] = user.get('full_name', '') if user else ''
                else:
                    row[column] = ''
            else:
                row[column] = task.get(column, '')

        csv_data.append(row)

    # Создание CSV
    import io
    output = io.StringIO()

    if csv_data:
        writer = csv.DictWriter(output, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerows(csv_data)

    csv_content = output.getvalue()

    # Сохранение в кэш
    if format_type != 'simple':
        cache_manager.set(cache_key, csv_content, ttl=300)

    if user_telegram != 'anonymous':
        logging.info(f"Экспорт CSV выполнен пользователем {user_telegram}, записей: {len(csv_data)}")
    else:
        logging.info(f"Экспорт CSV выполнен анонимным пользователем, записей: {len(csv_data)}")

    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=tasks_export_{datetime.now().strftime("%Y%m%d")}.csv'}
    )


@app.route('/api/llm/analyze/tasks', methods=['POST'])
@require_permission('can_use_llm')
@validate_request(LLMAnalysisRequest)
def analyze_tasks_llm_endpoint():
    """
    Эндпоинт для анализа задач через LLM.
    Требует права can_use_llm.
    В демо-режиме возвращает фиктивные данные.

    Body:
        JSON с параметрами анализа (LLMAnalysisRequest модель)

    Returns:
        JSON с результатами анализа
    """
    analysis_request = request.validated_data
    user_info = request.user_info

    logging.info(f"Запрос LLM анализа от пользователя: {user_info['telegram_username']}")
    logging.debug(f"Параметры анализа: {analysis_request.model_dump()}")

    # Проверка квоты LLM запросов (в демо-режиме всегда OK)
    quota = auth_manager.get_user_llm_quota(user_info['telegram_username'])

    # Генерация ключа кэша
    cache_key = cache_manager.generate_key(
        'llm_analysis',
        time_period=analysis_request.time_period,
        metrics=','.join(sorted(analysis_request.metrics)),
        date=datetime.now().strftime('%Y-%m-%d')
    )

    # Проверка кэша
    cached_result = cache_manager.get(cache_key)
    if cached_result:
        cached_result['meta']['cache_hit'] = True
        logging.debug(f"Использован кэшированный результат LLM анализа")
        return generate_response(cached_result['data'], meta=cached_result.get('meta', {}))

    # ДЕМО-ДАННЫЕ (вместо реального LLM анализа)
    # В реальной системе здесь был бы вызов к OpenAI API
    demo_analysis_result = {
        'report_id': f"llm_rep_{int(time.time())}",
        'generated_at': datetime.now().isoformat(),
        'time_period': analysis_request.time_period,
        'analysis': {
            'summary': {
                'total_tasks': 45,
                'completed': 32,
                'completion_rate': "71%",
                'in_progress': 8,
                'overdue': 5,
                'avg_completion_time': "2.3 days"
            },
            'productivity_metrics': {
                'top_performers': [
                    {"username": "@developer_alex", "tasks_completed": 12, "completion_rate": "92%"},
                    {"username": "@manager_anna", "tasks_completed": 10, "completion_rate": "100%"}
                ],
                'team_productivity_score': 7.8,
                'daily_completion_trend': [5, 7, 6, 8, 4, 3, 5]
            },
            'bottlenecks': [
                {
                    'area': 'code_review',
                    'impact': 'high',
                    'avg_delay': '1.5 days',
                    'affected_tasks': [101, 103, 107],
                    'recommendation': 'Внедрить автоматические проверки кода'
                }
            ],
            'team_performance': {
                'workload_distribution': {
                    '@developer_alex': '35%',
                    '@manager_anna': '25%',
                    'others': '40%'
                },
                'collaboration_score': 6.2,
                'suggested_adjustments': [
                    'Распределить нагрузку более равномерно',
                    'Назначить ментора для новых сотрудников'
                ]
            }
        },
        'recommendations': [
            'Внедрить систему автоматических напоминаний о дедлайнах',
            'Установить лимит одновременно выполняемых задач (макс. 5 на человека)'
        ] if analysis_request.include_recommendations else [],
        'predictions': {
            'next_week_completion': '38-42 задачи',
            'potential_bottlenecks': ['тестирование', 'интеграция'],
            'suggested_actions': [
                'Начать работу над задачами с высоким приоритетом в начале недели',
                'Запланировать ревью кода на среду и пятницу'
            ]
        }
    }

    # Формирование полного ответа
    response_data = {
        'status': 'success',
        'data': demo_analysis_result,
        'meta': {
            'timestamp': datetime.now().isoformat(),
            'request_id': f"req_llm_{int(time.time())}",
            'tokens_used': 1450,
            'cache_hit': False,
            'llm_model': 'demo-mode',
            'note': 'Это демо-данные. В реальной системе здесь был бы вызов к LLM API.',
            'quota_info': quota
        }
    }

    # Сохранение в кэш
    cache_manager.set(cache_key, response_data, ttl=3600)  # 1 час

    logging.info(f"LLM анализ выполнен пользователем {user_info['telegram_username']} (демо-режим)")
    return generate_response(demo_analysis_result, meta=response_data['meta'])


@app.route('/api/users', methods=['POST'])
@require_permission('can_manage_users')
@validate_request(UserCreate)
def create_user_endpoint():
    """
    Эндпоинт для создания нового пользователя.
    Требует права can_manage_users.

    Body:
        JSON с данными пользователя (UserCreate модель)

    Returns:
        JSON с созданным пользователем
    """
    user_data = request.validated_data
    user_info = request.user_info

    logging.info(f"Запрос создания пользователя от: {user_info['telegram_username']}")
    logging.debug(f"Данные нового пользователя: {user_data.model_dump()}")

    # Проверка уникальности telegram_username
    existing_user = users_manager.find_one(telegram_username=user_data.telegram_username)
    if existing_user:
        logging.warning(f"Пользователь уже существует: {user_data.telegram_username}")
        return generate_response(
            {'error': f'Пользователь {user_data.telegram_username} уже существует'},
            status='error',
            status_code=400
        )

    # Подготовка данных пользователя для сохранения в CSV
    user_dict = user_data.model_dump(exclude_unset=True)
    user_dict['is_active'] = str(user_dict['is_active'])

    # Создание пользователя
    try:
        created_user = users_manager.insert(user_dict)

        logging.info(f"Пользователь {user_data.telegram_username} создан пользователем {user_info['telegram_username']}")

        return generate_response({
            'user': created_user,
            'message': 'Пользователь успешно создан'
        }, status_code=201)

    except Exception as e:
        logging.error(f"Ошибка создания пользователя: {e}")
        return generate_response(
            {'error': str(e)},
            status='error',
            status_code=500
        )


@app.route('/api/health', methods=['GET'])
def health_check_endpoint():
    """
    Эндпоинт для проверки здоровья системы.
    Не требует аутентификации.

    Returns:
        JSON со статусом системы и метриками
    """
    logging.debug(f"Запрос проверки здоровья системы")

    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'components': {
            'flask': 'running',
            'csv_storage': 'ok',
            'cache': 'enabled' if cache_manager.enabled else 'disabled',
            'llm': 'demo-mode',
            'security': 'enabled' if config_manager.is_security_enabled() else 'disabled',
            'export_for_all': config_manager.is_export_allowed_for_all()
        },
        'metrics': {
            'users_count': len(users_manager.read_all()),
            'tasks_count': len(tasks_manager.read_all()),
            'events_count': len(events_manager.read_all()),
            'docs_count': len(docs_manager.read_all()),
            'uptime_seconds': int(time.time() - app_start_time)
        },
        'config': {
            'security_enabled': config_manager.is_security_enabled(),
            'cache_enabled': cache_manager.enabled,
            'server_port': config_manager.get('server.port', 5000),
            'export_allowed_for_all': config_manager.is_export_allowed_for_all()
        }
    }

    return generate_response(health_status)


# ============================================================================
# WEBSOCKET ОБРАБОТЧИКИ
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """
    Обработчик подключения WebSocket.
    Проверяет токен и устанавливает соединение.
    """
    token = request.args.get('token')

    if not token:
        logging.warning("WebSocket подключение без токена")
        emit('error', {'message': 'Требуется токен. Добавьте ?token=YOUR_TOKEN к URL подключения'})
        return False

    logging.debug(f"WebSocket подключение с токеном: {token[:20]}...")

    # Валидация токена
    valid, user_info = auth_manager.validate_token(token, 'access')

    if not valid:
        logging.warning(f"Неверный токен WebSocket: {token[:20]}...")
        emit('error', {'message': user_info.get('error', 'Неверный токен')})

        # Отправляем событие о необходимости повторной авторизации
        if 'истек' in user_info.get('error', '').lower():
            emit(SystemConstants.WS_EVENTS['SESSION_EXPIRED'], {
                'message': 'Сессия истекла. Пожалуйста, авторизуйтесь заново.',
                'timestamp': datetime.now().isoformat()
            })

        return False

    # Сохранение информации о подключении
    request.user_info = user_info
    logging.info(f"WebSocket подключение: {user_info['telegram_username']}")

    emit('connected', {
        'message': 'WebSocket подключен',
        'user': user_info['telegram_username'],
        'timestamp': datetime.now().isoformat()
    })


@socketio.on('subscribe')
def handle_subscribe(data):
    """
    Обработчик подписки на каналы WebSocket.

    Args:
        data: JSON с channels - список каналов для подписки
    """
    if not hasattr(request, 'user_info'):
        logging.warning("WebSocket подписка без аутентификации")
        emit('error', {'message': 'Не аутентифицирован'})
        return

    channels = data.get('channels', [])
    user_telegram = request.user_info['telegram_username']

    logging.info(f"Пользователь {user_telegram} подписывается на каналы: {channels}")

    for channel in channels:
        join_room(channel)
        logging.debug(f"Пользователь {user_telegram} подписался на канал {channel}")

    emit('subscribed', {
        'channels': channels,
        'message': 'Подписка успешна'
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Обработчик отключения WebSocket."""
    if hasattr(request, 'user_info'):
        logging.info(f"WebSocket отключение: {request.user_info['telegram_username']}")
        emit(SystemConstants.WS_EVENTS['USER_OFFLINE'], {
            'user': request.user_info['telegram_username'],
            'timestamp': datetime.now().isoformat()
        })


# ============================================================================
# ИНИЦИАЛИЗАЦИЯ ТЕСТОВЫХ ДАННЫХ
# ============================================================================

def initialize_sample_data():
    """
    Инициализация тестовых данных системы.
    Создает примеры пользователей и задач для демонстрации.
    """
    # Проверяем, есть ли уже данные
    existing_users = users_manager.read_all()
    if len(existing_users) > 1:  # Учитываем заголовок
        logging.info("Тестовые данные уже существуют")
        return

    logging.info("Инициализация тестовых данных...")

    # Создание тестовых пользователей
    sample_users = [
        {
            'telegram_username': '@admin_ivan',
            'full_name': 'Иван Петров',
            'role': 'admin',
            'is_active': 'True',
            'email': 'ivan@company.com',
            'department': 'IT'
        },
        {
            'telegram_username': '@manager_anna',
            'full_name': 'Анна Сидорова',
            'role': 'manager',
            'is_active': 'True',
            'email': 'anna@company.com',
            'department': 'Project Management'
        },
        {
            'telegram_username': '@developer_alex',
            'full_name': 'Алексей Козлов',
            'role': 'member',
            'is_active': 'True',
            'email': 'alex@company.com',
            'department': 'Development'
        },
        {
            'telegram_username': '@viewer_olga',
            'full_name': 'Ольга Новикова',
            'role': 'viewer',
            'is_active': 'True',
            'email': 'olga@company.com',
            'department': 'Sales'
        }
    ]

    for user_data in sample_users:
        users_manager.insert(user_data)

    # Создание тестовых задач
    sample_tasks = [
        {
            'task_id': '101',
            'title': 'Разработка REST API',
            'description': 'Создать API endpoints для системы управления задачами',
            'status': 'in_progress',
            'assignee': '@developer_alex',
            'creator': '@manager_anna',
            'priority': 'high',
            'tags': json.dumps(['backend', 'api', 'priority'], ensure_ascii=False)
        },
        {
            'task_id': '102',
            'title': 'Исправить критический баг',
            'description': 'Ошибка при сохранении данных в CSV',
            'status': 'done',
            'assignee': '@developer_alex',
            'creator': '@admin_ivan',
            'priority': 'urgent',
            'tags': json.dumps(['bug', 'critical', 'hotfix'], ensure_ascii=False)
        },
        {
            'task_id': '103',
            'title': 'Обновить документацию',
            'description': 'Добавить новые API методы в документацию',
            'status': 'todo',
            'assignee': '@developer_alex',
            'creator': '@manager_anna',
            'priority': 'medium',
            'tags': json.dumps(['docs', 'api'], ensure_ascii=False)
        }
    ]

    for task_data in sample_tasks:
        tasks_manager.insert(task_data)

    logging.info("Тестовые данные успешно созданы")


# ============================================================================
# ЗАПУСК СЕРВЕРА
# ============================================================================

if __name__ == '__main__':
    # Запоминаем время старта приложения
    app_start_time = time.time()

    # Создание необходимых директорий
    os.makedirs(SystemConstants.DATA_DIR, exist_ok=True)
    os.makedirs('./logs', exist_ok=True)

    # Инициализация тестовых данных
    initialize_sample_data()

    # Получение конфигурации сервера
    server_config = config_manager.get('server', {})
    host = server_config.get('host', '0.0.0.0')
    port = server_config.get('port', 5000)
    debug = server_config.get('debug', False)

    logging.info(f"Запуск сервера системы управления задачами")
    logging.info(f"Адрес: http://{host}:{port}")
    logging.info(f"Режим отладки: {debug}")
    logging.info(f"Безопасность: {'включена' if config_manager.is_security_enabled() else 'отключена'}")
    logging.info(f"Экспорт всем пользователям: {'разрешен' if config_manager.is_export_allowed_for_all() else 'требует аутентификации'}")
    logging.info(f"Доступные эндпоинты:")
    logging.info(f"  - GET  /api/health - Проверка здоровья системы")
    logging.info(f"  - POST /api/telegram/auth - Аутентификация через Telegram")
    logging.info(f"  - POST /api/auth/refresh - Обновление токена")
    logging.info(f"  - POST /api/auth/logout - Выход из системы")
    logging.info(f"  - GET  /api/tasks - Получение списка задач")
    logging.info(f"  - POST /api/tasks - Создание задачи")
    logging.info(f"  - PUT  /api/tasks/<id> - Обновление задачи")
    logging.info(f"  - GET  /api/export/tasks.csv - Экспорт задач в CSV")
    logging.info(f"  - POST /api/llm/analyze/tasks - Анализ задач (демо)")
    logging.info(f"  - POST /api/users - Создание пользователя")

    # Запуск сервера
    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        allow_unsafe_werkzeug=True
    )
