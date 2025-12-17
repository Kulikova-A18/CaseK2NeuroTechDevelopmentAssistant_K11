import json
import re
from typing import Optional, Dict, Any, Type, TypeVar
import httpx

from .llm_text import call_llm_text, LLMTextError


T = TypeVar("T")  # для TypedDict / Pydantic при необходимости


class LLMJsonError(Exception):
    pass


# Регулярка для вытаскивания первого JSON-объекта
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(raw_text: str) -> str:
    """
    Извлекает JSON-объект из ответа модели.
    """
    match = _JSON_RE.search(raw_text)
    if not match:
        raise LLMJsonError(
            f"Не найден JSON в ответе модели. Raw: {raw_text!r}"
        )
    return match.group(0)


def _parse_json(json_str: str) -> Dict[str, Any]:
    """
    Парсит JSON-строку в dict.
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise LLMJsonError(
            f"Ошибка парсинга JSON: {e}. Payload: {json_str!r}"
        ) from e

    if not isinstance(data, dict):
        raise LLMJsonError(
            f"Ожидался JSON-объект (dict), получено: {type(data)}"
        )

    return data


def call_llm_json(
    *,
    client: httpx.Client,
    api_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    response_schema: Optional[Type[T]] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any] | T:
    """
    Вызов LLM с ожиданием СТРОГО JSON-ответа.

    1. Вызывает LLM в текстовом режиме.
    2. Вытаскивает JSON.
    3. Парсит.
    4. (Опционально) валидирует через schema.
    """

    try:
        raw_text = call_llm_text(
            client=client,
            api_url=api_url,
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,   # КРИТИЧНО: никакой креативности
            max_tokens=max_tokens,
        )
    except LLMTextError as e:
        raise LLMJsonError(f"Ошибка вызова LLM: {e}") from e

    json_str = _extract_json(raw_text)
    parsed = _parse_json(json_str)

    if response_schema is not None:
        try:
            return response_schema(**parsed)  # Pydantic / dataclass
        except Exception as e:
            raise LLMJsonError(
                f"JSON не соответствует схеме {response_schema}: {e}. "
                f"Payload: {parsed}"
            ) from e

    return parsed