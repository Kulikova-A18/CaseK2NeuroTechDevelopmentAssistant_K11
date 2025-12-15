from typing import Any, Dict, List


class ValidationError(Exception):
    """Ошибка валидации данных, полученных от LLM."""
    pass


# =========================
# DAILY
# =========================

def validate_daily_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Проверяет JSON, полученный из daily.
    Ожидаем строгий контракт:
    {
        "yesterday": list[str],
        "today": list[str],
        "blockers": list[dict]
    }
    """

    if not isinstance(data, dict):
        raise ValidationError("Daily output must be a dict")

    required_keys = {"yesterday", "today", "blockers"}
    missing = required_keys - data.keys()
    if missing:
        raise ValidationError(f"Missing keys in daily JSON: {missing}")

    if not isinstance(data["yesterday"], list):
        raise ValidationError("Field 'yesterday' must be a list")

    if not isinstance(data["today"], list):
        raise ValidationError("Field 'today' must be a list")

    if not isinstance(data["blockers"], list):
        raise ValidationError("Field 'blockers' must be a list")

    # Проверяем элементы списков
    for item in data["yesterday"]:
        if not isinstance(item, str):
            raise ValidationError("Items in 'yesterday' must be strings")

    for item in data["today"]:
        if not isinstance(item, str):
            raise ValidationError("Items in 'today' must be strings")

    for blocker in data["blockers"]:
        if not isinstance(blocker, dict):
            raise ValidationError("Each blocker must be an object")

        if "description" not in blocker:
            raise ValidationError("Blocker missing 'description' field")

        if not isinstance(blocker["description"], str):
            raise ValidationError("Blocker 'description' must be a string")

        # task_id может быть строкой или None
        if "task_id" in blocker and blocker["task_id"] is not None:
            if not isinstance(blocker["task_id"], str):
                raise ValidationError("Blocker 'task_id' must be string or null")

    return data


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
