from typing import Any, Dict, List


class ValidationError(Exception):
    """Ошибка валидации данных, полученных от LLM."""
    pass


# =========================
# DAILY
# =========================

from typing import Any, Dict, List, Set


class ValidationError(Exception):
    pass


def validate_daily_json(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Валидирует результат LLM для режима DAILY.

    ОЖИДАЕМЫЙ ФОРМАТ:

    {
      "daily": {
        "role": "DEV" | "QA",
        "yesterday": [{"task_id": "STRING", "summary": "STRING"}],
        "today": [{"task_id": "STRING", "summary": "STRING"}],
        "blockers": [{"text": "STRING", "critical": true|false, "related_task_id": "STRING"}],
        "quality": "EMPTY" | "TOO_SHORT" | "NO_TASKS_MENTIONED" | "DETAIL_OK" | "GREAT"
      },
      "clarification": {
        "needs_clarification": true|false,
        "question": "STRING"
      }
    }
    """

    if not isinstance(payload, dict):
        raise ValidationError("Daily payload must be a dict")

    
    if "daily" not in payload:
        raise ValidationError("Missing 'daily' key in daily payload")
    if "clarification" not in payload:
        raise ValidationError("Missing 'clarification' key in daily payload")

    daily = payload["daily"]
    clarification = payload["clarification"]

    if not isinstance(daily, dict):
        raise ValidationError("'daily' must be an object")
    if not isinstance(clarification, dict):
        raise ValidationError("'clarification' must be an object")


    required_daily = {"role", "yesterday", "today", "blockers", "quality"}
    missing_daily = required_daily - set(daily.keys())
    if missing_daily:
        raise ValidationError(f"Missing keys in daily JSON: {missing_daily}")


    role = daily["role"]
    if role not in {"DEV", "QA"}:
        raise ValidationError("daily.role must be 'DEV' or 'QA'")


    quality = daily["quality"]
    allowed_quality = {"EMPTY", "TOO_SHORT", "NO_TASKS_MENTIONED", "DETAIL_OK", "GREAT"}
    if quality not in allowed_quality:
        raise ValidationError(f"daily.quality must be one of {sorted(allowed_quality)}")


    for key in ("yesterday", "today"):
        items = daily[key]
        if not isinstance(items, list):
            raise ValidationError(f"'{key}' must be a list")

        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                raise ValidationError(f"Items in '{key}' must be objects")

            if "task_id" not in item or "summary" not in item:
                raise ValidationError(f"Each item in '{key}' must have task_id and summary")

            if not isinstance(item["task_id"], str):
                raise ValidationError(f"{key}[{idx}].task_id must be string")
            if not isinstance(item["summary"], str):
                raise ValidationError(f"{key}[{idx}].summary must be string")

  
    blockers = daily["blockers"]
    if not isinstance(blockers, list):
        raise ValidationError("'blockers' must be a list")

    for idx, b in enumerate(blockers):
        if not isinstance(b, dict):
            raise ValidationError("Items in 'blockers' must be objects")

        required_blocker = {"text", "critical", "related_task_id"}
        missing_blocker = required_blocker - set(b.keys())
        if missing_blocker:
            raise ValidationError(f"Missing keys in blocker[{idx}]: {missing_blocker}")

        if not isinstance(b["text"], str):
            raise ValidationError(f"blockers[{idx}].text must be string")
        if not isinstance(b["critical"], bool):
            raise ValidationError(f"blockers[{idx}].critical must be boolean")
        if not isinstance(b["related_task_id"], str):
            raise ValidationError(f"blockers[{idx}].related_task_id must be string")


    required_clar = {"needs_clarification", "question"}
    missing_clar = required_clar - set(clarification.keys())
    if missing_clar:
        raise ValidationError(f"Missing keys in clarification: {missing_clar}")

    if not isinstance(clarification["needs_clarification"], bool):
        raise ValidationError("clarification.needs_clarification must be boolean")
    if not isinstance(clarification["question"], str):
        raise ValidationError("clarification.question must be string")

    
    needs = clarification["needs_clarification"]
    q = clarification["question"]
    if not needs and q != "":
        raise ValidationError('clarification.question must be "" when needs_clarification is false')
    if needs and not q.strip():
        raise ValidationError("clarification.question must be non-empty when needs_clarification is true")

    return payload



# =========================
# ANALYTICS
# =========================

def validate_analytics_intent(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ожидаем:
    {
        "intent": str,
        "params": dict
    }
    """

    if not isinstance(data, dict):
        raise ValidationError("Analytics intent must be a dict")

    if "intent" not in data:
        raise ValidationError("Missing 'intent' in analytics JSON")

    if not isinstance(data["intent"], str):
        raise ValidationError("'intent' must be a string")

    if "params" in data and not isinstance(data["params"], dict):
        raise ValidationError("'params' must be a dict if present")

    return data


# =========================
# BLOCKERS
# =========================

def validate_blocker(blocker: Dict[str, Any]) -> Dict[str, Any]:
    """
    Проверка одного блокера после классификации.
    """

    required_keys = {"task_id", "description", "severity"}

    missing = required_keys - blocker.keys()
    if missing:
        raise ValidationError(f"Blocker missing keys: {missing}")

    if blocker["task_id"] is not None and not isinstance(blocker["task_id"], str):
        raise ValidationError("Blocker 'task_id' must be string or null")

    if not isinstance(blocker["description"], str):
        raise ValidationError("Blocker 'description' must be string")

    if blocker["severity"] not in {"low", "medium", "high", "critical"}:
        raise ValidationError(
            f"Invalid blocker severity: {blocker['severity']}"
        )

    return blocker
