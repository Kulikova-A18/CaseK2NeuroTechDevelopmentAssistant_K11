from typing import Dict, Any, List

from llm_core.prompts import PERSONAL_DIGEST_SYSTEM_PROMPT
from llm_core.utils.builders import build_personal_digest_prompt
from llm_core.utils.llm_text import call_llm_text, LLMTextError


def handle_personal_digest(
    *,
    client,
    api_url: str,
    api_key: str,
    model: str,
    kanban: Dict[str, List[Dict[str, Any]]],
    blockers: List[Dict[str, Any]],
    user_role: str,
) -> str:
    """
    Формирует персональный дайджест пользователя
    на основе данных канбан-доски и блокеров.
    """

    digest_data = {
        "role": user_role,
        "kanban": kanban,
        "blockers": blockers,
    }

    user_prompt = build_personal_digest_prompt(digest_data)

    try:
        text = call_llm_text(
            client=client,
            api_url=api_url,
            api_key=api_key,
            model=model,
            system_prompt=PERSONAL_DIGEST_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
    except LLMTextError as e:
        raise RuntimeError(f"LLM error in personal_digest: {e}") from e

    return text
