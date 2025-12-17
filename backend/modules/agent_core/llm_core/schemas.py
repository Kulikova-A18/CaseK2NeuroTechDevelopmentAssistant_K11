from typing import TypedDict, List, Optional, Dict, Literal, Union


# =========================
# DAILY
# =========================

class Blocker(TypedDict):
    task_id: Optional[str]
    description: str


class DailyReport(TypedDict):
    yesterday: List[str]
    today: List[str]
    blockers: List[Blocker]


# =========================
# FAQ
# =========================

FAQIntentType = Literal["GENERAL_FAQ", "RAG_FAQ", "NOT_FAQ"]


class FAQIntent(TypedDict):
    intent: FAQIntentType


# =========================
# ANALYTICS
# =========================

class AnalyticsIntent(TypedDict):
    intent: str
    params: Dict[str, Union[str, int, float, bool]]


# =========================
# BLOCKERS (classified)
# =========================

BlockerSeverity = Literal["low", "medium", "high", "critical"]


class ClassifiedBlocker(Blocker):
    severity: BlockerSeverity


# =========================
# DIGEST / REPORT INPUTS
# =========================

class TeamDigestData(TypedDict):
    team_name: Optional[str]
    sprint: Optional[str]
    progress: Dict[str, Union[int, float, str]]
    blockers: List[ClassifiedBlocker]
    risks: List[str]


class PersonalDigestData(TypedDict):
    user_id: str
    tasks: List[str]
    blockers: List[ClassifiedBlocker]
    reminders: List[str]


# =========================
# AGENT CORE RESPONSE
# =========================

AgentResponseType = Literal["json", "text", "error"]


class AgentResponse(TypedDict):
    type: AgentResponseType
    data: Union[dict, str]
