from typing import Dict, Any

from llm_core.prompts import (
    DAILY_SYSTEM_PROMPT,
    DAILY_CLARIFICATION_SYSTEM_PROMPT,
)
from llm_core.schemas import DailyReport
from llm_core.utils.builders import (
    build_daily_initial_prompt,
    build_daily_clarification_prompt,
)
from llm_core.utils.llm_json import call_llm_json, LLMJsonError
from llm_core.utils.validators import validate_daily_json, ValidationError


# Используется agent_core для маршрутизации
DAILY_INITIAL = "daily_initial"
DAILY_CLARIFICATION = "daily_clarification"


def handle_daily_initial(
    *,
    client,
    api_url: str,
    api_key: str,
    model: str,
    message: str,
) -> DailyReport:
    """
    Обработка первичного daily-ответа разработчика.
    На вход — сырой текст.
    На выход — валидный DailyReport.
    """

    user_prompt = build_daily_initial_prompt(message)

    try:
        result = call_llm_json(
            client=client,
            api_url=api_url,
            api_key=api_key,
            model=model,
            system_prompt=DAILY_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
    except LLMJsonError as e:
        raise RuntimeError(f"LLM JSON error in daily_initial: {e}") from e

    try:
        validated = validate_daily_json(result)
    except ValidationError as e:
        raise RuntimeError(f"Daily validation error: {e}") from e

    return validated


def handle_daily_clarification(
    *,
    client,
    api_url: str,
    api_key: str,
    model: str,
    previous_daily: Dict[str, Any],
    clarification_text: str,
) -> DailyReport:
    """
    Обработка уточнения daily.
    На вход:
      - предыдущий daily JSON
      - уточняющий текст от разработчика
    На выход — обновлённый DailyReport.
    """

    user_prompt = build_daily_clarification_prompt(
        previous_json=previous_daily,
        clarification_text=clarification_text,
    )

    try:
        result = call_llm_json(
            client=client,
            api_url=api_url,
            api_key=api_key,
            model=model,
            system_prompt=DAILY_CLARIFICATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
    except LLMJsonError as e:
        raise RuntimeError(f"LLM JSON error in daily_clarification: {e}") from e

    try:
        validated = validate_daily_json(result)
    except ValidationError as e:
        raise RuntimeError(f"Daily validation error (clarification): {e}") from e
    
    return validated
