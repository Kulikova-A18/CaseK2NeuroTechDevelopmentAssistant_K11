# 1. Быстрый запуск примеров (без параметров):
# python
# from agent_module import run_examples
#
# run_examples()

import httpx
from typing import Dict, Any, Optional, Tuple
from llm_core.agent_process import agent_process
from llm_core.blockers import process_blockers

class AgentModule:
    """Модуль для работы с AI-агентом для daily-отчетов и аналитики"""

    def __init__(
        self,
        api_key: str = "38w68Yk1th",
        model: str = "Qwen/Qwen3-8B",
        api_url: str = "https://qwen3-8b.product.nova.neurotech.k2.cloud/v1/chat/completions",
        timeout_config: Optional[Dict[str, float]] = None
    ):
        """
        Инициализация модуля агента

        Args:
            api_key: API ключ для доступа к модели
            model: Название модели
            api_url: URL API эндпоинта
            timeout_config: Конфигурация таймаутов (connect, read, write, pool)
        """
        self.api_key = api_key
        self.model = model
        self.api_url = api_url

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

    def run_daily_example(self) -> None:
        """Пример использования для daily-отчетов"""
        print("=" * 50)
        print("DAILY REPORT EXAMPLE")
        print("=" * 50)

        # Обработка daily-отчета
        daily_resp = self.process_daily_report(
            message=(
                "Вчера доделал интеграцию платежей по TASK-12. "
                "Сегодня начинаю TASK-15. "
                "Есть блокер — жду доступы к тестовому стенду."
            ),
            role="DEV"
        )

        print("DAILY RESPONSE:")
        print(daily_resp)
        print()

        # Обработка блокеров
        known_tasks = {"TASK-12", "TASK-15"}
        existing_blockers = set()

        events, escalations = self.process_blockers_from_daily(
            daily_response=daily_resp,
            known_tasks=known_tasks,
            existing_blockers=existing_blockers
        )

        print("BLOCKER EVENTS:")
        for event in events:
            print(f"  - {event}")
        print()

        print("ESCALATIONS:")
        for escalation in escalations:
            print(f"  - {escalation}")
        print()

    def run_analytics_example(self) -> None:
        """Пример использования для аналитики"""
        print("=" * 50)
        print("ANALYTICS EXAMPLE")
        print("=" * 50)

        # Шаг 1 - Определение намерения
        intent_resp = self.process_analytics(
            message="Покажи общий статус спринта, но подробно, с прогнозом."
        )

        print("ANALYTICS INTENT:")
        print(intent_resp)
        print()

        # Шаг 2 - Генерация отчета (если поддерживается)
        if intent_resp.get("type") == "json":
            metrics = {
                "completed_tasks": 12,
                "total_tasks": 20,
                "velocity_trend": "down",
                "blockers": 2,
            }

            report_resp = self.process_analytics(
                message="Покажи общий статус спринта, но подробно, с прогнозом.",
                metrics=metrics,
                mode="REPORT"
            )

            print("ANALYTICS REPORT:")
            print(report_resp)
            print()

    def close(self) -> None:
        """Закрытие HTTP-клиента"""
        self.client.close()

    def __enter__(self):
        """Поддержка контекстного менеджера"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Закрытие клиента при выходе из контекста"""
        self.close()


# Функция для быстрого запуска примеров без параметров
def run_examples():
    """
    Запуск всех примеров использования модуля

    Пример вызова:
        from agent_module import run_examples
        run_examples()
    """
    # Создаем экземпляр модуля
    agent = AgentModule(api_key="YOUR_API_KEY_HERE")

    try:
        # Запускаем примеры
        agent.run_daily_example()
        agent.run_analytics_example()

    finally:
        # Закрываем клиент
        agent.close()


# Альтернативная функция для более простого использования
def create_agent(
    api_key: str = "YOUR_API_KEY_HERE",
    model: str = "Qwen/Qwen3-8B",
    api_url: str = "https://qwen3-8b.product.nova.neurotech.k2.cloud/v1/chat/completions"
) -> AgentModule:
    """
    Создание и настройка агента

    Args:
        api_key: API ключ
        model: Модель
        api_url: URL API

    Returns:
        Экземпляр AgentModule
    """
    return AgentModule(api_key=api_key, model=model, api_url=api_url)

