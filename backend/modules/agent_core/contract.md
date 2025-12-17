# Agent Core — LLM Contract

## 0) Что это

`agent_core` — модуль LLM-логики. Он делает две вещи:

1. **Парсит текст** пользователя в структурированный JSON (daily, analytics intent).
2. **Пишет текстовые ответы** на основе переданных backend-ом данных (analytics report, faq answer, digest).

**LLM ничего не хранит, ничего не считает, никуда не ходит.**
Все интеграции (трекер, БД, телега, хранение истории) — только backend.

---

## 1) Точка входа

### `agent_process(...)`

Единая функция, которую вызывает backend.

```python
agent_process(
    *,
    mode: str,
    payload: dict,
    backend_context: dict,
    client,            # httpx.Client
    api_url: str,
    api_key: str,
    model: str,
) -> dict
```

### Общий формат ответа

```json
{
  "type": "json" | "text",
  "data": <object | string>
}
```

* `type="json"` — в `data` будет dict (структура/intent).
* `type="text"` — в `data` будет строка (отчёт/ответ/дайджест).

---

## 2) LLM клиент и конфигурация (ответственность backend)

Backend:

* создаёт `httpx.Client(...)`
* передаёт `api_url`, `api_key`, `model`
* управляет таймаутами/ретраями на уровне HTTP (если нужно)

Agent:

* не создаёт клиент сам
* не читает env напрямую
* не хранит ключи

---

## 3) DAILY режим

### 3.1 Вход

```json
{
  "message": "сырой текст daily",
  "role": "DEV" | "QA",
  "daily_state": {
    "mode": "INITIAL" | "CLARIFICATION",
    "quality_retries": 0
  }
}
```

**Пояснения:**

* `role` всегда задаёт backend.
* `daily_state.mode`:

  * `INITIAL` — первичный daily
  * `CLARIFICATION` — ответ пользователя на уточняющий вопрос
* `quality_retries` — счётчик попыток, если backend просит переформулировать.

### 3.2 Выход (JSON)

```json
{
  "daily": {
    "role": "DEV" | "QA",
    "yesterday": [{"task_id":"TASK-1","summary":"..." }],
    "today": [{"task_id":"TASK-2","summary":"..." }],
    "blockers": [{"text":"...","critical":true,"related_task_id":"TASK-2"}],
    "quality": "EMPTY" | "TOO_SHORT" | "NO_TASKS_MENTIONED" | "DETAIL_OK" | "GREAT"
  },
  "clarification": {
    "needs_clarification": true | false,
    "question": "STRING"
  }
}
```

---

## 4) DAILY: пример backend-логики уточнений и ретраев

Backend должен различать три причины “переспрашивания”:

### A) Уточнение по смыслу (needs_clarification=true)

LLM вернул `clarification.needs_clarification=true`.

**Backend flow:**

1. `agent_process(mode="DAILY", daily_state.mode="INITIAL")`
2. если `needs_clarification=true` → показать пользователю `question`
3. пользователь отвечает
4. backend вызывает `agent_process(mode="DAILY", daily_state.mode="CLARIFICATION")`
5. повторять до `needs_clarification=false`

**Важно:** это “логическое уточнение”, числовой лимит не обязателен.

---

### B) LLM не прошёл валидацию (валидатор упал)

Это технический сбой: модель вернула невалидный JSON/поля.

**Backend flow (авторетрай):**

1. backend ловит ошибку (`RuntimeError` от daily handler)
2. backend делает 1–2 повторных вызова с тем же входом (retry)
3. если повторно невалидно:

   * возвращает пользователю fallback-сообщение: “Не смог разобрать daily, переформулируй: вчера/сегодня/блокеры одной строкой”
   * или логирует и принимает пустой daily

Рекомендованный лимит: `retry_count=1..2`.

---

### Пример псевдокода backend для DAILY

```python
def process_daily(message, role, daily_state):
    for attempt in range(2):  # retry for technical validation issues
        try:
            resp = agent_process(
                mode="DAILY",
                payload={"message": message, "role": role, "daily_state": daily_state},
                backend_context={},
                client=client, api_url=API_URL, api_key=KEY, model=MODEL,
            )
            break
        except RuntimeError:
            if attempt == 1:
                return {"type": "text", "data": "Не смог разобрать daily. Переформулируй: вчера/сегодня/блокеры."}

    data = resp["data"]  # {"daily":..., "clarification":...}

    if data["clarification"]["needs_clarification"]:
        # отправить вопрос пользователю, ожидать ответа и вызвать снова with mode=CLARIFICATION
        return {"type": "text", "data": data["clarification"]["question"]}

    if data["daily"]["quality"] in {"EMPTY","TOO_SHORT","NO_TASKS_MENTIONED"} and daily_state["quality_retries"] < 2:
        daily_state["quality_retries"] += 1
        return {"type": "text", "data": "Слишком общо. Напиши: что сделал вчера, что планируешь сегодня, есть ли блокеры (желательно с ID задач)."}

    return resp  # валидный daily json
```

---

## 5) ANALYTICS режим (двухшаговый)

### 5.1 Шаг 1: intent detection

#### Вход

```json
{
  "message": "запрос тимлида"
}
```

#### Выход (JSON)

```json
{
  "intent": "TEAM_OVERVIEW" | "TEAM_RISKS" | "WORKLOAD" | "RELEASE_BLOCKERS",
  "params": {}
}
```

Доп. параметр только для `TEAM_OVERVIEW`:

```json
"params": { "detail_level": "BASIC" | "EXTENDED" }
```

Если параметры не нужны → **обязательно** `{}`.

---

### 5.2 Список intent (что должен считать backend)

1. **TEAM_OVERVIEW**
   Общий обзор спринта/периода.
   Backend собирает агрегаты прогресса, динамику, ключевые цели, статус.

   `detail_level`:

   * `BASIC` — короткий обзор
   * `EXTENDED` — расширенный обзор (может включать прогнозы, риск срыва, динамику velocity и т.п.)

2. **TEAM_RISKS**
   Риски/блокеры команды: топ проблем, критичность, влияние.

3. **WORKLOAD**
   Загрузка участников: перегруз/недогруз, концентрация задач, перекосы.

4. **RELEASE_BLOCKERS**
   Что блокирует релиз/цели спринта: критические задачи/зависимости/блокеры.

**Важно:** расчёт и формирование метрик — backend. LLM только формулирует.

---

### 5.3 Шаг 2: отчёт по метрикам

#### Вход

```json
{
  "metrics": { "любая структура с агрегатами, которую считает backend" },
  "leader_message": "оригинальный запрос тимлида (опционально)"
}
```

#### Выход

```json
{
  "type": "text",
  "data": "текстовый аналитический отчёт"
}
```

---

### 5.4 Пример backend-логики для ANALYTICS

```python
# 1) intent
intent_resp = agent_process(
    mode="ANALYTICS",
    payload={"message": leader_message},
    backend_context={},
    client=client, api_url=API_URL, api_key=KEY, model=MODEL,
)

if intent_resp["type"] == "text":
    return intent_resp  # неподдержано

intent = intent_resp["data"]["intent"]
params = intent_resp["data"]["params"]

# 2) backend считает метрики по intent/params
metrics = compute_metrics(intent=intent, params=params)

# 3) report
report_resp = agent_process(
    mode="ANALYTICS",
    payload={"metrics": metrics, "leader_message": leader_message},
    backend_context={},
    client=client, api_url=API_URL, api_key=KEY, model=MODEL,
)

return report_resp
```

---

## 6) FAQ режим

### Вход

```json
{ "message": "вопрос" }
```

### Выход (TEXT)

```json
{ "type": "text", "data": "ответ" }
```

Ограничения:

* только общие Scrum/Agile понятия
* без “у нас в команде…”
* без предложения действий/организации процессов
* без выдуманных инструментов/времени/правил

---

## 7) DIGEST режим (персональный)

### Вход

```json
{
  "data": {
    "task_counts": { "in_progress": 0, "in_review": 0, "done": 0 },
    "current_tasks": [ {"id":"TASK-1","title":"..."} ],
    "blockers": [ {"text":"...","severity":"high","is_repeat":false,"task_id":"TASK-1"} ],
    "notes": ["..."]
  }
}
```

### Выход (TEXT)

```json
{ "type": "text", "data": "унифицированный дайджест" }
```

LLM:

* не даёт советов
* не выдумывает данные
* строго следует шаблону

---

## 8) Blockers pipeline (после DAILY)

`blockers.py` — чистая бизнес-логика классификации блокеров, вызывается backend-ом **после** успешного `DAILY`.

### Зачем backend-у отдельный модуль

* Daily даёт “сырые” блокеры (текст + флаг critical + task_id).
* `blockers.py` приводит их к унифицированным событиям (`blocker_event`) и выделяет то, что надо эскалировать (`escalation_payload`).
* Это позволяет:

  * хранить блокеры в едином формате,
  * отличать повторные блокеры от новых,
  * вычислять “severity” единообразно,
  * строить эскалации независимо от UI.

---

### Вход

#### 1.1 `daily_json: Dict[str, Any]`

Это **строго** объект `daily` из ответа LLM:

```python
daily_json = daily_resp["data"]["daily"]
```

Ожидаемые поля:

```json
{
  "role": "DEV" | "QA",
  "blockers": [
    {
      "text": "STRING",
      "critical": true | false,
      "related_task_id": "STRING"
    }
  ]
}
```

* `role` — роль автора (из daily).
* `blockers[]` — список блокеров, может быть пустым.

#### `known_tasks: Set[str]`

Множество ID задач, которые реально существуют в трекере (или канбан-таблице).

Пример:

```python
known_tasks = {"TASK-1", "TASK-2", "BUG-10"}
```

Используется только для проверки `task_exists`.

#### `existing_blockers: Set[str]`

Множество нормализованных текстов блокеров, которые уже были зафиксированы ранее (история).

Пример:

```python
existing_blockers = {"жду доступы к стенду", "жду ревью mr"}
```

Используется для определения `is_repeat`.

---

### Основная функция

#### `process_blockers(...)`

```python
events, escalations = process_blockers(
    daily_json=daily_json,
    known_tasks=known_tasks,
    existing_blockers=existing_blockers,
)
```

---

### Выходные данные

#### `events: List[Dict[str, Any]]` (blocker_event)

Каждый блокер превращается в событие единого формата:

```json
{
  "author_role": "DEV" | "QA",
  "text": "оригинальный текст",
  "normalized_text": "нормализованный текст",

  "task_id": "TASK-123" | "NO_TASK_ID",
  "task_exists": true | false,

  "severity": "low" | "medium" | "high" | "critical",
  "is_repeat": true | false,

  "source": "daily"
}
```

Правила:

* `normalized_text` — `lower().strip()`.
* `task_exists` — `task_id in known_tasks` (если task_id валидный).
* `severity` определяется по двум факторам:

  * `critical_flag` (из daily: `critical`)
  * `task_exists`

Текущая матрица severity:

| critical_flag | task_exists | severity |
| ------------- | ----------- | -------- |
| True          | True        | critical |
| True          | False       | high     |
| False         | True        | medium   |
| False         | False       | low      |

* `is_repeat` — `normalized_text in existing_blockers`.

#### `escalations: List[Dict[str, Any]]` (escalation_payload)

Формируется **только** для severity `high` или `critical`:

```json
{
  "type": "BLOCKER_ESCALATION",
  "severity": "high" | "critical",
  "text": "оригинальный текст",
  "task_id": "TASK-123" | "NO_TASK_ID",
  "author_role": "DEV" | "QA"
}
```

Если блокер `low/medium` → `None` и в `escalations` не попадает.

---

### Как backend использует результаты

#### Хранение истории (для repeat detection)

Чтобы `is_repeat` работал, backend должен:

* сохранять `normalized_text` из `events` куда-то (БД/таблица/файл),
* при следующем daily доставать множество `existing_blockers`.

Пример логики:

```python
events, escalations = process_blockers(...)

# сохранить events в журнал
save_blocker_events(events)

# обновить историю repeat detection
for e in events:
    store_normalized_blocker_text(e["normalized_text"])
```

#### Эскалация

`escalations` backend может:

* отправить тимлиду в отдельный канал/чат,
* записать в “alerts”,
* поднять “urgent” событие в UI.

Важно: **backend решает куда и как**, `blockers.py` только выдаёт структуру.

#### Привязка к пользователю

`blockers.py` не знает `user_id`.
Backend должен добавить идентификатор автора сам:

```python
for e in events:
    e["author_id"] = user_id

for esc in escalations:
    esc["author_id"] = user_id
```

---

## 5) Пример полного флоу DAILY → BLOCKERS

```python
# 1) daily
daily_resp = agent_process(mode="DAILY", ...)

daily_json = daily_resp["data"]["daily"]

# 2) backend получает данные трекера
known_tasks = get_known_task_ids_from_tracker()
existing_blockers = get_existing_blockers_for_team()

# 3) классификация блокеров
events, escalations = process_blockers(
    daily_json=daily_json,
    known_tasks=known_tasks,
    existing_blockers=existing_blockers,
)

# 4) хранение
save_blocker_events(events)

# 5) эскалации
for esc in escalations:
    notify_teamlead(esc)
```

---

## 6) Ограничения (важно)

* Модуль не вычисляет время/дедлайны.
* `existing_blockers` — точное совпадение по нормализованному тексту (без семантики).
* `task_exists` зависит только от `known_tasks` (никаких API вызовов).

---

Если хочешь — я допишу в контракт **один рекомендованный формат хранения истории** (таблица `blocker_events` и таблица `blocker_text_index`), чтобы backend не гадал, как формировать `existing_blockers`.

---

## 9) Примеры вызова `agent_process`

### DAILY (initial)

```python
resp = agent_process(
    mode="DAILY",
    payload={
        "message": "Вчера закрыл TASK-12, сегодня начну TASK-15. Блокер: нет доступов к стенду.",
        "role": "DEV",
        "daily_state": {"mode": "INITIAL", "quality_retries": 0},
    },
    backend_context={},
    client=client, api_url=API_URL, api_key=KEY, model=MODEL,
)
```

### DAILY (clarification)

```python
resp = agent_process(
    mode="DAILY",
    payload={
        "message": "Да, блокер относится к TASK-15: без стенда не могу проверить интеграцию.",
        "role": "DEV",
        "daily_state": {"mode": "CLARIFICATION", "quality_retries": 0},
    },
    backend_context={},
    client=client, api_url=API_URL, api_key=KEY, model=MODEL,
)
```

### ANALYTICS (step 1 intent)

```python
resp = agent_process(
    mode="ANALYTICS",
    payload={"message": "Дай общий статус спринта, но расширенно, с прогнозом."},
    backend_context={},
    client=client, api_url=API_URL, api_key=KEY, model=MODEL,
)
```

### ANALYTICS (step 2 report)

```python
resp = agent_process(
    mode="ANALYTICS",
    payload={"metrics": metrics, "leader_message": "Дай общий статус спринта..."},
    backend_context={},
    client=client, api_url=API_URL, api_key=KEY, model=MODEL,
)
```

### FAQ

```python
resp = agent_process(
    mode="FAQ",
    payload={"message": "Что такое daily и зачем он нужен?"},
    backend_context={},
    client=client, api_url=API_URL, api_key=KEY, model=MODEL,
)
```

### DIGEST

```python
resp = agent_process(
    mode="DIGEST",
    payload={"data": digest_data},
    backend_context={},
    client=client, api_url=API_URL, api_key=KEY, model=MODEL,
)
```

---

## 10) Типичные ошибки и ожидания backend

* LLM может вернуть невалидный JSON → backend делает 1–2 автоповтора.
* `needs_clarification=true` — backend обязан переспрашивать пользователя.
* user_id / author_id всегда живёт в backend и связывается с результатами там же.

---