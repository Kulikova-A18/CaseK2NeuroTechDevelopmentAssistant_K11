from typing import Optional

from prompts import FAQ_ANSWER_SYSTEM_PROMPT
from llm_core.utils.builders import build_faq_answer_prompt
from llm_core.utils.llm_text import call_llm_text, LLMTextError



def handle_faq(
    *,
    client,
    api_url: str,
    api_key: str,
    model: str,
    question: str,
    context: Optional[str] = None,
) -> str:
    """
    Обработка FAQ-вопроса.

    На вход:
    - question: вопрос пользователя
    - context: (опционально) контекст из базы знаний / RAG

    На выход:
    - текстовый ответ модели (без reasoning)
    """

    user_prompt = build_faq_answer_prompt(
        question=question,
        context=context,
    )

    try:
        answer = call_llm_text(
            client=client,
            api_url=api_url,
            api_key=api_key,
            model=model,
            system_prompt=FAQ_ANSWER_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
    except LLMTextError as e:
        raise RuntimeError(f"FAQ LLM error: {e}") from e

    return answer
