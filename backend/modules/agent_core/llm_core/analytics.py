from typing import Dict, Any

from modules.agent_core.llm_core.prompts import (
    ANALYTICS_INTENT_SYSTEM_PROMPT,
    ANALYTICS_REPORT_SYSTEM_PROMPT,
)
from modules.agent_core.llm_core.utils.builders import (
    build_analytics_intent_prompt,
    build_analytics_report_prompt,
)
from modules.agent_core.llm_core.utils.llm_json import call_llm_json, LLMJsonError
from modules.agent_core.llm_core.utils.llm_text import call_llm_text, LLMTextError
from modules.agent_core.llm_core.utils.validators import (
    validate_analytics_intent,
    ValidationError,
)


def handle_analytics_intent(
    *,
    client,
    api_url: str,
    api_key: str,
    model: str,
    leader_message: str,
) -> Dict[str, Any]:
    """
    Шаг 1.
    Тимлид пишет сообщение → LLM возвращает JSON-инструкцию
    в формате AnalyticsIntent:

    {
      "intent": "<ANALYTICS_TYPE>",
      "params": { ... }
    }
    """

    user_prompt = build_analytics_intent_prompt(leader_message)

    try:
        result = call_llm_json(
            client=client,
            api_url=api_url,
            api_key=api_key,
            model=model,
            system_prompt=ANALYTICS_INTENT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
    except LLMJsonError as e:
        raise RuntimeError(f"LLM JSON error in analytics_intent: {e}") from e

    try:
        validated = validate_analytics_intent(result)
    except ValidationError as e:
        raise RuntimeError(f"Analytics intent validation error: {e}") from e

    return validated


def handle_analytics_report(
    *,
    client,
    api_url: str,
    api_key: str,
    model: str,
    metrics: Dict[str, Any],
) -> str:
    """
    Шаг 2.
    Backend посчитал метрики → LLM формирует текстовый отчёт
    для тимлида.
    """

    user_prompt = build_analytics_report_prompt(metrics)

    try:
        report = call_llm_text(
            client=client,
            api_url=api_url,
            api_key=api_key,
            model=model,
            system_prompt=ANALYTICS_REPORT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
    except LLMTextError as e:
        raise RuntimeError(f"LLM text error in analytics_report: {e}") from e

    return report
