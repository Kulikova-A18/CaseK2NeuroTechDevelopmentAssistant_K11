from typing import Dict, Any

from modules.agent_core.llm_core.daily import (
    handle_daily_initial,
    handle_daily_clarification,
)
from modules.agent_core.llm_core.analytics import (
    handle_analytics_intent,
    handle_analytics_report,
)
from modules.agent_core.llm_core.digest import handle_personal_digest
from modules.agent_core.llm_core.blockers import process_blockers

from modules.agent_core.llm_core.utils.validators import ValidationError

MAX_QUALITY_RETRIES = 2

# =========================
# DAILY
# =========================

def _process_daily(
    *,
    payload: Dict[str, Any],
    backend_context: Dict[str, Any],
    client,
    api_url: str,
    api_key: str,
    model: str,
) -> Dict[str, Any]:

    message = payload["message"]
    role = payload["role"]
    state = payload.get("daily_state", {})

    mode = state.get("mode", "INITIAL")
    previous_daily = state.get("previous_daily")

    quality_retries = state.get("quality_retries", 0)

    try:
        # --- INITIAL ---
        if mode == "INITIAL":
            daily = handle_daily_initial(
                client=client,
                api_url=api_url,
                api_key=api_key,
                model=model,
                message=message,
            )

        # --- CLARIFICATION ---
        elif mode == "CLARIFICATION":
            if not previous_daily:
                raise AgentProcessError("Missing previous_daily for clarification")

            daily = handle_daily_clarification(
                client=client,
                api_url=api_url,
                api_key=api_key,
                model=model,
                clarification_text=message,
                previous_daily=previous_daily,
            )

        else:
            raise AgentProcessError(f"Unknown daily mode: {mode}")

    except ValidationError:
        # --- технический ретрай ---
        if quality_retries >= MAX_QUALITY_RETRIES:
            return {
                "type": "text",
                "data": "Ответ слишком общий. Пожалуйста, опиши, что именно было сделано.",
            }

        return {
            "type": "json",
            "data": {
                "next_action": "RETRY",
                "daily_state": {
                    "mode": "INITIAL",
                    "quality_retries": quality_retries + 1,
                },
            },
        }

    # --- СОДЕРЖАТЕЛЬНОЕ УТОЧНЕНИЕ ---
    if daily["clarification"]["needs_clarification"]:
        return {
          "type": "json",
          "data": {
            "next_action": "ASK_CLARIFICATION",
            "question": daily["clarification"]["question"],
            "daily_state": {
              "mode": "CLARIFICATION",
              "previous_daily": daily,
              "quality_retries": quality_retries
            }
          }
        }

    known_tasks = set(backend_context.get("known_tasks", []))
    existing_blockers = set(backend_context.get("existing_blockers", []))
    
    blocker_events, escalations = process_blockers(
        daily_json=daily["daily"],   # ВАЖНО: именно daily.daily
        known_tasks=known_tasks,
        existing_blockers=existing_blockers,
    )
    
    response_data = {
        "next_action": "SUCCESS",
        "daily": daily,
        "blockers": blocker_events,
    }
    
    # если есть эскалации — отдаем backend’у
    if escalations:
        response_data["escalations"] = escalations
    
    return {
        "type": "json",
        "data": response_data,
    }


# =========================
# ANALYTICS
# =========================

def _process_analytics(
    *,
    payload: Dict[str, Any],
    backend_context: Dict[str, Any],
    client,
    api_url: str,
    api_key: str,
    model: str,
) -> Dict[str, Any]:
    """
    Единый analytics-флоу:
    1) извлечение intent
    2) передача intent backend’у
    3) форматирование отчёта (если метрики уже есть)
    """

    # --- ШАГ 1: если метрик ещё нет — извлекаем intent ---
    if "metrics" not in backend_context:
        leader_message = payload["message"]

        try:
            intent = handle_analytics_intent(
                client=client,
                api_url=api_url,
                api_key=api_key,
                model=model,
                leader_message=leader_message,
            )
        except RuntimeError:
            return {
                "type": "text",
                "data": "Извини, этот тип аналитического запроса сейчас не поддерживается.",
            }

        # ВАЖНО: возвращаем intent backend’у
        return {
            "type": "json",
            "data": intent,
        }

    # --- ШАГ 2: метрики уже посчитаны backend’ом ---
    metrics = backend_context["metrics"]

    report = handle_analytics_report(
        client=client,
        api_url=api_url,
        api_key=api_key,
        model=model,
        metrics=metrics,
    )

    return {
        "type": "text",
        "data": report,
    }


# =========================
# DIGEST
# =========================

def _process_digest(
    *,
    backend_context: Dict[str, Any],

    client,
    api_url: str,
    api_key: str,
    model: str,
) -> Dict[str, Any]:

    kanban = backend_context["kanban"]
    blockers = backend_context.get("blockers", [])
    role = backend_context["role"]

    digest = handle_personal_digest(
        client=client,
        api_url=api_url,
        api_key=api_key,
        model=model,
        kanban=kanban,
        blockers=blockers,
        user_role=role,
    )

    return {
        "type": "text",
        "data": digest,
    }


# =========================
# AGENT PROCESS (ORCHESTRATION)
# =========================


class AgentProcessError(Exception):
    pass


def agent_process(
    *,
    mode: str,
    payload: Dict[str, Any],
    client,
    api_url: str,
    api_key: str,
    model: str,

    backend_context: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Главный orchestrator LLM-логики.

    backend_context — данные, которые LLM НЕ считает:
    - kanban
    - known_tasks
    - existing_blockers
    - metrics
    """

    if mode == "DAILY":
        return _process_daily(
            payload=payload,
            backend_context=backend_context,
            client=client,
            api_url=api_url,
            api_key=api_key,
            model=model,
        )

    if mode == "ANALYTICS":
        return _process_analytics(
            payload=payload,
            backend_context=backend_context,
            client=client,
            api_url=api_url,
            api_key=api_key,
            model=model,
        )

    if mode == "DIGEST":
        return _process_digest(
            backend_context=backend_context,
            client=client,
            api_url=api_url,
            api_key=api_key,
            model=model,
        )

    raise AgentProcessError(f"Unsupported mode: {mode}")
