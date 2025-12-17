from __future__ import annotations

from typing import Dict, Any, List, Set, Tuple

# =========================
# 1. Извлечение из daily
# =========================

def extract_blockers_from_daily(
    daily_json: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Извлекает сырые блокеры из валидированного daily JSON.
    """

    role = daily_json["role"]
    blockers = daily_json.get("blockers", [])

    extracted: List[Dict[str, Any]] = []

    for blocker in blockers:
        extracted.append({
            "author_role": role,
            "text": blocker.get("text", "").strip(),
            "task_id": blocker.get("related_task_id", "NO_TASK_ID"),
            "critical_flag": bool(blocker.get("critical", False)),
        })

    return extracted


# =========================
# 2. Нормализация
# =========================

def normalize_blocker_text(text: str) -> str:
    """
    Простейшая нормализация текста блокера. Для приличия. По факту бесполезная вещь.
    """
    return text.lower().strip()


# =========================
# 3. Верификация с трекером
# =========================

def verify_task_exists(
    task_id: str,
    known_tasks: Set[str],
) -> bool:
    """
    Проверяет, существует ли задача в трекере.
    """
    if not task_id or task_id == "NO_TASK_ID":
        return False
    return task_id in known_tasks


# =========================
# 4. Определение критичности
# =========================

def determine_severity(
    critical_flag: bool,
    task_exists: bool,
) -> str:
    """
    Определяет уровень критичности блокера.
    """

    if critical_flag and task_exists:
        return "critical"

    if critical_flag:
        return "high"

    if task_exists:
        return "medium"

    return "low"


# =========================
# 5. Повторяемость
# =========================

def is_repeat_blocker(
    normalized_text: str,
    existing_blockers: Set[str],
) -> bool:
    """
    Проверяет, был ли такой блокер уже зафиксирован ранее.
    """
    return normalized_text in existing_blockers


# =========================
# 6. Сборка blocker_event
# =========================

def build_blocker_event(
    raw_blocker: Dict[str, Any],
    known_tasks: Set[str],
    existing_blockers: Set[str],
) -> Dict[str, Any]:
    """
    Формирует нормализованное событие блокера.
    """

    normalized_text = normalize_blocker_text(raw_blocker["text"])
    task_exists = verify_task_exists(
        raw_blocker["task_id"],
        known_tasks,
    )

    severity = determine_severity(
        critical_flag=raw_blocker["critical_flag"],
        task_exists=task_exists,
    )

    repeat = is_repeat_blocker(
        normalized_text,
        existing_blockers,
    )

    return {
        "author_role": raw_blocker["author_role"],
        "text": raw_blocker["text"],
        "normalized_text": normalized_text,

        "task_id": raw_blocker["task_id"],
        "task_exists": task_exists,

        "severity": severity,
        "is_repeat": repeat,

        "source": "daily",
    }


# =========================
# 7. Эскалация
# =========================

def build_escalation_payload(
    blocker_event: Dict[str, Any]
) -> Dict[str, Any] | None:
    """
    Формирует payload для эскалации, если блокер критичный.
    """

    if blocker_event["severity"] not in {"high", "critical"}:
        return None

    return {
        "type": "BLOCKER_ESCALATION",
        "severity": blocker_event["severity"],
        "text": blocker_event["text"],
        "task_id": blocker_event["task_id"],
        "author_role": blocker_event["author_role"],
    }


# =========================
# 8. Единая точка входа
# =========================

def process_blockers(
    *,
    daily_json: Dict[str, Any],
    known_tasks: Set[str],
    existing_blockers: Set[str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Главная функция модуля blockers.

    Возвращает:
    - список blocker_event
    - список escalation_payload
    """

    raw_blockers = extract_blockers_from_daily(daily_json)

    events: List[Dict[str, Any]] = []
    escalations: List[Dict[str, Any]] = []

    for raw in raw_blockers:
        event = build_blocker_event(
            raw_blocker=raw,
            known_tasks=known_tasks,
            existing_blockers=existing_blockers,
        )

        events.append(event)

        escalation = build_escalation_payload(event)
        if escalation:
            escalations.append(escalation)

    return events, escalations
