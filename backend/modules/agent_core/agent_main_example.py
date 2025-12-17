import httpx

# from modules.agent_core.llm_core.agent_process import agent_process
# from modules.agent_core.llm_core.blockers import process_blockers

from llm_core.agent_process import agent_process
from llm_core.blockers import process_blockers

API_URL = "https://qwen3-8b.product.nova.neurotech.k2.cloud/v1/chat/completions"
API_KEY = "YOUR_API_KEY_HERE"
MODEL = "Qwen/Qwen3-8B"


client = httpx.Client(
    timeout=httpx.Timeout(
        connect=10.0,
        read=120.0,
        write=10.0,
        pool=10.0
    ),
    verify=False ##ВАЖНО
)


# -----------------------
# DAILY example
# -----------------------

daily_resp = agent_process(
    mode="DAILY",
    payload={
        "message": (
            "Вчера доделал интеграцию платежей по TASK-12. "
            "Сегодня начинаю TASK-15. "
            "Есть блокер — жду доступы к тестовому стенду."
        ),
        "role": "DEV",
        "daily_state": {
            "mode": "INITIAL",
            "quality_retries": 0,
        },
    },
    backend_context={},
    client=client,
    api_url=API_URL,
    api_key=API_KEY,
    model=MODEL,
)

print("DAILY RESPONSE:\n", daily_resp)


# -----------------------
# BLOCKERS example
# -----------------------

if daily_resp["type"] == "json":
    daily_json = daily_resp["data"]["daily"]

    known_tasks = {"TASK-12", "TASK-15"}
    existing_blockers = set()

    events, escalations = process_blockers(
        daily_json=daily_json,
        known_tasks=known_tasks,
        existing_blockers=existing_blockers,
    )

    print("BLOCKER EVENTS:\n", events)
    print("ESCALATIONS:\n", escalations)


# -----------------------
# ANALYTICS example
# -----------------------

# step 1 — intent
intent_resp = agent_process(
    mode="ANALYTICS",
    payload={
        "message": "Покажи общий статус спринта, но подробно, с прогнозом."
    },
    backend_context={},
    client=client,
    api_url=API_URL,
    api_key=API_KEY,
    model=MODEL,
)

print("ANALYTICS INTENT:\n", intent_resp)

# step 2 — report (if supported)
if intent_resp["type"] == "json":
    metrics = {
        "completed_tasks": 12,
        "total_tasks": 20,
        "velocity_trend": "down",
        "blockers": 2,
    }

    report_resp = agent_process(
        mode="ANALYTICS",
        payload={
            "message": "Покажи общий статус спринта, но подробно, с прогнозом."
        },
        backend_context={"metrics": metrics},
        client=client,
        api_url=API_URL,
        api_key=API_KEY,
        model=MODEL,
    )

    print("ANALYTICS REPORT:\n", report_resp)
