import httpx
from collections import Counter
from llm_core.agent_process import agent_process
import os

API_URL = os.getenv("LLM_API_URL")
API_KEY = os.getenv("LLM_API_KEY")
MODEL = os.getenv("LLM_MODEL", "Qwen/Qwen3-8B")

client = httpx.Client(
    timeout=httpx.Timeout(
        connect=10.0,
        write=10.0,
        read=300.0,
        pool=10.0,
    ),
    verify=False,
)

QUALITY_ORDER = ["EMPTY", "TOO_SHORT", "NO_TASKS_MENTIONED", "DETAIL_OK", "GREAT"]
FORBIDDEN_TERMS = ["в нашей команде", "обычно мы", "у вас принято", "jira", "trello"]


# =========================
# DAILY
# =========================
from collections import Counter


def run_daily_eval(cases):
    stats = Counter()
    quality_dist = Counter()

    for case in cases:
        # =========================
        # 1. CALL AGENT
        # =========================
        try:
            resp = agent_process(
                mode="DAILY",
                payload=case["input"],
                backend_context={"known_tasks": case["tracker_tasks"]},
                client=client,
                api_url=API_URL,
                api_key=API_KEY,
                model=MODEL,
            )
        except Exception:
            stats["runtime_error"] += 1
            continue

        # =========================
        # 2. TYPE CHECK
        # =========================
        if resp.get("type") != "json":
            stats["non_json"] += 1
            continue

        data = resp.get("data", {})
        next_action = data.get("next_action", "UNKNOWN")
        stats[f"action_{next_action.lower()}"] += 1

        # =========================
        # 3. GROUND TRUTH
        # =========================
        expected_need = case["expected"].get("needs_clarification")

        # =========================
        # 4. EXTRACT ACTUAL CLARIFICATION + DAILY
        # =========================
        actual_need = False
        clarification = None
        daily = None

        # ---- CASE A: AGENT ASKED FOR CLARIFICATION ----
        if next_action == "ASK_CLARIFICATION":
            actual_need = True

            prev = (
                data.get("daily_state", {})
                    .get("previous_daily", {})
            )

            clarification = prev.get("clarification") or {
                "needs_clarification": True
            }

            daily = prev.get("daily")

        # ---- CASE B: AGENT RETURNED SUCCESS ----
        elif next_action == "SUCCESS":
            clarification = data.get("clarification") or {
                "needs_clarification": False
            }

            actual_need = clarification.get("needs_clarification", False)
            daily = data.get("daily")

        # ---- CASE C: UNKNOWN / OTHER ----
        else:
            clarification = data.get("clarification") or {
                "needs_clarification": False
            }
            actual_need = clarification.get("needs_clarification", False)
            daily = data.get("daily")

        # =========================
        # 5. CLARIFICATION METRICS (ALWAYS)
        # =========================
        if expected_need is not None:
            if actual_need and expected_need:
                stats["clar_tp"] += 1
            elif actual_need and not expected_need:
                stats["clar_fp"] += 1
            elif not actual_need and expected_need:
                stats["clar_fn"] += 1
            else:
                stats["clar_tn"] += 1

        # =========================
        # 6. IF NO DAILY — STOP HERE
        # =========================
        if daily is None:
            stats["no_daily"] += 1
            continue

        # =========================
        # 7. FINAL DAILY METRICS
        # =========================
        stats["json_valid"] += 1

        # ---- QUALITY ----
        quality = daily.get("quality")
        if quality:
            quality_dist[quality] += 1
        else:
            stats["missing_quality"] += 1

        # =========================
        # 8. TASK ID CORRECTNESS
        # count only if SUCCESS
        # =========================
        if next_action == "SUCCESS":
            mentioned = {
                t.get("task_id")
                for t in daily.get("yesterday", []) + daily.get("today", [])
                if isinstance(t, dict) and "task_id" in t
            }
        
            if mentioned.issubset(case["tracker_tasks"]):
                stats["task_id_valid"] += 1
            else:
                stats["task_id_invalid"] += 1

    return stats, quality_dist


# =========================
# ANALYTICS
# =========================
def run_analytics_eval(cases):
    
    stats = Counter()

    for case in cases:
        try:
            resp = agent_process(
                mode="ANALYTICS",
                payload=case["input"],
                backend_context={},  
                client=client,
                api_url=API_URL,
                api_key=API_KEY,
                model=MODEL,
            )
        except Exception:
            stats["runtime_error"] += 1
            continue

        expected = case["expected"]
        expected_intent = expected.get("intent")
        expected_params = expected.get("params", None)

        # -------------------------
        # 1) Unsupported: 
        # -------------------------
        if expected_intent == "UNSUPPORTED":
            if resp.get("type") == "json":
                data = resp.get("data", {})
                if data.get("intent") == "UNSUPPORTED":
                    stats["unsupported_correct"] += 1
                else:
                    stats["unsupported_wrong"] += 1

                # params для UNSUPPORTED обычно {} — проверяем, если задано в expected
                if expected_params is not None:
                    if data.get("params", {}) == expected_params:
                        stats["params_correct"] += 1
                    else:
                        stats["params_wrong"] += 1

            elif resp.get("type") == "text":
                stats["unsupported_correct"] += 1
            else:
                stats["wrong_type"] += 1

            continue

        # -------------------------
        # 2) Supported intents:
        # -------------------------
        if resp.get("type") != "json":
            stats["wrong_type"] += 1
            continue

        data = resp.get("data", {})
        got_intent = data.get("intent")
        got_params = data.get("params", {})

        # intent correctness
        if got_intent == expected_intent:
            stats["intent_correct"] += 1
        else:
            stats["intent_wrong"] += 1
            

    return stats


# =========================
# FAQ / DIGEST
# =========================
def run_text_eval(cases, mode):
    stats = Counter()

    for case in cases:
        resp = agent_process(
            mode=mode,
            payload=case["input"],
            backend_context={},
            client=client,
            api_url=API_URL,
            api_key=API_KEY,
            model=MODEL,
        )

        if resp["type"] != "text":
            stats["wrong_type"] += 1
            continue

        stats["schema_ok"] += 1
        text = resp["data"].lower()

        hallucinated = False
        for term in FORBIDDEN_TERMS:
            if term in text:
                hallucinated = True
                break

        if hallucinated:
            stats["hallucination"] += 1
        else:
            stats["hallucination_free"] += 1

    return stats
    

if __name__ == "__main__":
    daily_stats, quality_dist = run_daily_eval(DAILY_CASES)
    analytics_stats = run_analytics_eval(ANALYTICS_CASES)
    faq_stats = run_text_eval(FAQ_CASES, mode="FAQ")
    digest_stats = run_text_eval(DIGEST_CASES, mode="DIGEST")

    print("=== DAILY ===")
    print(daily_stats)
    print("Quality distribution:", quality_dist)

    print("\n=== ANALYTICS ===")
    print(analytics_stats)

    print("\n=== FAQ ===")
    print(faq_stats)

    print("\n=== DIGEST ===")
    print(digest_stats)

