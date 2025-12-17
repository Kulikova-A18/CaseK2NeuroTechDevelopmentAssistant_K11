from typing import Optional, Dict, Any, List
import httpx
import re


class LLMTextError(Exception):
    pass


def _strip_thinking(text: str) -> str:
    """
    Удаляет reasoning-блоки вида <think>...</think>
    """
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def call_llm_text(
    *,
    client: httpx.Client,
    api_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: Optional[int] = None,
    extra_params: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Чистая функция вызова LLM в текстовом режиме.
    """

    if not api_key:
        raise LLMTextError("api_key is required")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
    }

    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    if extra_params:
        payload.update(extra_params)

    try:
        response = client.post(
            api_url,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
    except Exception as e:
        raise LLMTextError(f"HTTP request failed: {e}") from e

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        raise LLMTextError(
            f"Bad LLM response: {e} | raw={response.text!r}"
        ) from e

    content = _strip_thinking(content)

    return content