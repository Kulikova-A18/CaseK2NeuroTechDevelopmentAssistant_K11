from __future__ import annotations

from typing import Dict, Any, List


# =========================
# DAILY
# =========================

def build_daily_initial_prompt(raw_text: str) -> str:
    return f"""
Ответ разработчика на daily:

\"\"\"
{raw_text}
\"\"\"

Разбери этот текст согласно инструкциям.
"""


def build_daily_clarification_prompt(
    previous_json: Dict[str, Any],
    clarification_text: str
) -> str:
    return f"""
Исходный daily JSON:
{previous_json}

Уточнение от разработчика:
\"\"\"
{clarification_text}
\"\"\"

Обнови JSON, сохранив структуру.
"""


# =========================
# FAQ
# =========================


def build_faq_answer_prompt(question: str, context: str | None = None) -> str:
    if context:
        return f"""
Контекст:
{context}

Вопрос:
{question}
"""
    return f"""
Вопрос:
{question}
"""


# =========================
# ANALYTICS
# =========================

def build_analytics_intent_prompt(message: str) -> str:
    return f"""
Запрос пользователя:
\"\"\"
{message}
\"\"\"

Определи аналитический интент.
"""


def build_analytics_report_prompt(metrics: Dict[str, Any]) -> str:
    return f"""
Тебе передали структурированные метрики спринта команды разработки.

Метрики:
{metrics}

"""

# =========================
# BLOCKERS
# =========================

def build_blockers_prompt(blockers: List[Dict[str, Any]]) -> str:
    return f"""
Список блокеров:
{blockers}

Классифицируй блокеры и оцени критичность.
"""


# =========================
# DIGEST
# =========================


from typing import Dict, Any


def build_personal_digest_prompt(data: Dict[str, Any]) -> str:
    return f"""
Данные для формирования персональной сводки:

{data}
"""
