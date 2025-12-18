# modules/agent_core/agent_module.py

# Как использовать:
# # Простой пример использования
# from modules.agent_core.agent_module import create_agent

# # Создаем агента
# agent = create_agent()

# # Получаем задачи из CSV в формате JSON
# tasks_json = agent.get_tasks_json()

# # Печатаем результат
# print(json.dumps(tasks_json, ensure_ascii=False, indent=2))

# # Закрываем соединение
# agent.close()

# # Или используем контекстный менеджер
# with create_agent() as agent:
#     tasks_json = agent.get_tasks_json()
#     print(f"Всего задач: {tasks_json['total_tasks']}")
#     print(f"В работе: {tasks_json['summary']['in_progress']}")
# Что было изменено:
# Добавлен параметр tasks_file_path в конструктор класса для указания пути к CSV файлу

# Добавлен метод _read_tasks_csv() для чтения и парсинга CSV файла

# Добавлен метод _parse_tags() для корректной обработки тегов из CSV

# Добавлен метод get_tasks_json() - единая функция, которая возвращает итоговый JSON с задачами и статистикой

# Удалена функция run_examples() и примеры использования

# Сохранились все оригинальные функции для работы с AI-агентом (process_daily_report, process_analytics и т.д.)

# Формат возвращаемого JSON:
# json
# {
#   "success": true,
#   "total_tasks": 4,
#   "tasks": [
#     {
#       "task_id": 101,
#       "title": "Разработка REST API",
#       "description": "Создать API endpoints для системы управления задачами",
#       "status": "in_progress",
#       "assignee": "@developer_alex",
#       "creator": "@manager_anna",
#       "created_at": "",
#       "updated_at": "",
#       "due_date": "",
#       "completed_at": "",
#       "priority": "high",
#       "tags": ["backend", "api", "priority"]
#     },
#     ...
#   ],
#   "statistics": {
#     "by_status": {"in_progress": 2, "done": 1, "todo": 1},
#     "by_priority": {"high": 2, "urgent": 1, "medium": 1},
#     "by_assignee": {"@developer_alex": 3, "не назначен": 1}
#   },
#   "summary": {
#     "in_progress": 2,
#     "todo": 1,
#     "done": 1,
#     "high_priority": 3,
#     "without_assignee": 1
#   }
# }

import httpx
import csv
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from modules.agent_core.llm_core.agent_process import agent_process
from modules.agent_core.llm_core.blockers import process_blockers

class AgentModule:
    """Модуль для работы с AI-агентом для daily-отчетов и аналитики"""

    def __init__(
        self,
        api_key: str = "38w68Yk1th",
        model: str = "Qwen/Qwen3-8B",
        api_url: str = "https://qwen3-8b.product.nova.neurotech.k2.cloud/v1/chat/completions",
        timeout_config: Optional[Dict[str, float]] = None,
        tasks_file_path: str = "data/tasks.csv"
    ):
        """
        Инициализация модуля агента

        Args:
            api_key: API ключ для доступа к модели
            model: Название модели
            api_url: URL API эндпоинта
            timeout_config: Конфигурация таймаутов (connect, read, write, pool)
            tasks_file_path: Путь к файлу с задачами
        """
        self.api_key = api_key
        self.model = model
        self.api_url = api_url
        self.tasks_file_path = Path(tasks_file_path)

        # Конфигурация таймаутов по умолчанию
        default_timeout = {
            "connect": 10.0,
            "read": 120.0,
            "write": 10.0,
            "pool": 10.0
        }

        if timeout_config:
            default_timeout.update(timeout_config)

        # Создаем HTTP-клиент
        self.client = httpx.Client(
            timeout=httpx.Timeout(**default_timeout),
            verify=False  # ВАЖНО: отключение SSL проверки
        )

    def _parse_tags(self, tags_str: str) -> List[str]:
        """
        Парсит строку с тегами из CSV
        
        Args:
            tags_str: Строка с тегами
            
        Returns:
            Список тегов
        """
        if not tags_str or tags_str.strip() == '':
            return []
        
        try:
            # Очищаем строку от лишних кавычек и преобразуем в список
            clean_str = tags_str.strip()
            if clean_str.startswith('[') and clean_str.endswith(']'):
                clean_str = clean_str[1:-1]
            
            # Разделяем по запятым и убираем кавычки
            tags = [tag.strip().replace('"', '').replace("'", "") 
                   for tag in clean_str.split(',') if tag.strip()]
            return tags
        except Exception as e:
            print(f"Ошибка при парсинге тегов '{tags_str}': {e}")
            return []

    def _read_tasks_csv(self) -> List[Dict[str, Any]]:
        """
        Читает задачи из CSV файла
        
        Returns:
            Список задач в виде словарей
        """
        tasks = []
        
        if not self.tasks_file_path.exists():
            print(f"Файл {self.tasks_file_path} не найден")
            return tasks
        
        try:
            with open(self.tasks_file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                for row_num, row in enumerate(csv_reader, 1):
                    try:
                        # Обрабатываем каждую задачу
                        task = {
                            "task_id": int(row.get("task_id", 0)) if row.get("task_id") else 0,
                            "title": row.get("title", ""),
                            "description": row.get("description", ""),
                            "status": row.get("status", ""),
                            "assignee": row.get("assignee", ""),
                            "creator": row.get("creator", ""),
                            "created_at": row.get("created_at", ""),
                            "updated_at": row.get("updated_at", ""),
                            "due_date": row.get("due_date", ""),
                            "completed_at": row.get("completed_at", ""),
                            "priority": row.get("priority", ""),
                            "tags": self._parse_tags(row.get("tags", ""))
                        }
                        tasks.append(task)
                    except Exception as e:
                        print(f"Ошибка при обработке строки {row_num}: {e}")
                        continue
        except Exception as e:
            print(f"Ошибка при чтении файла {self.tasks_file_path}: {e}")
        
        return tasks

    def get_tasks_json(self) -> Dict[str, Any]:
        """
        Читает задачи из CSV файла и возвращает их в формате JSON
        
        Returns:
            Словарь с задачами и статистикой
        """
        tasks = self._read_tasks_csv()
        
        # Собираем статистику
        status_stats = {}
        priority_stats = {}
        assignee_stats = {}
        
        for task in tasks:
            # Статистика по статусам
            status = task["status"] if task["status"] else "без статуса"
            status_stats[status] = status_stats.get(status, 0) + 1
            
            # Статистика по приоритетам
            priority = task["priority"] if task["priority"] else "без приоритета"
            priority_stats[priority] = priority_stats.get(priority, 0) + 1
            
            # Статистика по исполнителям
            assignee = task["assignee"] if task["assignee"] else "не назначен"
            assignee_stats[assignee] = assignee_stats.get(assignee, 0) + 1
        
        # Создаем итоговый JSON
        result = {
            "success": True,
            "total_tasks": len(tasks),
            "tasks": tasks,
            "statistics": {
                "by_status": status_stats,
                "by_priority": priority_stats,
                "by_assignee": assignee_stats
            },
            "summary": {
                "in_progress": status_stats.get("in_progress", 0),
                "todo": status_stats.get("todo", 0),
                "done": status_stats.get("done", 0),
                "high_priority": priority_stats.get("high", 0) + priority_stats.get("urgent", 0),
                "without_assignee": assignee_stats.get("не назначен", 0)
            }
        }
        
        return result

    def process_daily_report(
        self,
        message: str,
        role: str = "DEV",
        daily_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Обработка daily-отчета

        Args:
            message: Сообщение с отчетом
            role: Роль пользователя (DEV, PM и т.д.)
            daily_state: Состояние daily-отчета

        Returns:
            Ответ от агента
        """
        if daily_state is None:
            daily_state = {
                "mode": "INITIAL",
                "quality_retries": 0,
            }

        payload = {
            "message": message,
            "role": role,
            "daily_state": daily_state,
        }

        return agent_process(
            mode="DAILY",
            payload=payload,
            backend_context={},
            client=self.client,
            api_url=self.api_url,
            api_key=self.api_key,
            model=self.model,
        )

    def process_blockers_from_daily(
        self,
        daily_response: Dict[str, Any],
        known_tasks: Optional[set] = None,
        existing_blockers: Optional[set] = None
    ) -> Tuple[list, list]:
        """
        Обработка блокеров из daily-отчета

        Args:
            daily_response: Ответ от process_daily_report
            known_tasks: Известные задачи
            existing_blockers: Существующие блокеры

        Returns:
            Кортеж (events, escalations)
        """
        if daily_response.get("type") != "json":
            return [], []

        daily_json = daily_response["data"]["daily"]

        if known_tasks is None:
            known_tasks = set()

        if existing_blockers is None:
            existing_blockers = set()

        events, escalations = process_blockers(
            daily_json=daily_json,
            known_tasks=known_tasks,
            existing_blockers=existing_blockers,
        )

        return events, escalations

    def process_analytics(
        self,
        message: str,
        metrics: Optional[Dict[str, Any]] = None,
        mode: str = "INTENT"
    ) -> Dict[str, Any]:
        """
        Обработка аналитического запроса

        Args:
            message: Запрос аналитики
            metrics: Метрики для отчета
            mode: Режим работы (INTENT или REPORT)

        Returns:
            Ответ от агента
        """
        backend_context = {}

        if metrics and mode == "REPORT":
            backend_context = {"metrics": metrics}

        return agent_process(
            mode="ANALYTICS",
            payload={"message": message},
            backend_context=backend_context,
            client=self.client,
            api_url=self.api_url,
            api_key=self.api_key,
            model=self.model,
        )

    def close(self) -> None:
        """Закрытие HTTP-клиента"""
        self.client.close()

    def __enter__(self):
        """Поддержка контекстного менеджера"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Закрытие клиента при выходе из контекста"""
        self.close()


def create_agent(
    api_key: str = "38w68Yk1th",
    model: str = "Qwen/Qwen3-8B",
    api_url: str = "https://qwen3-8b.product.nova.neurotech.k2.cloud/v1/chat/completions",
    tasks_file_path: str = "data/tasks.csv"
) -> AgentModule:
    """
    Создание и настройка агента

    Args:
        api_key: API ключ
        model: Модель
        api_url: URL API
        tasks_file_path: Путь к файлу с задачами

    Returns:
        Экземпляр AgentModule
    """
    return AgentModule(
        api_key=api_key,
        model=model,
        api_url=api_url,
        tasks_file_path=tasks_file_path
    )