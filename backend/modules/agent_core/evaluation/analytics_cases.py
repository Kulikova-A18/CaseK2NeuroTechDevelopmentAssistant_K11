ANALYTICS_CASES = [
    {
        "input": {
            "message": "Как в целом идёт текущий спринт?",
        },
        "expected": {
            "intent": "TEAM_OVERVIEW",
            "params": {"detail_level": "BASIC"},
        },
    },
    {
        "input": {
            "message": "Дай краткий статус по спринту.",
        },
        "expected": {
            "intent": "TEAM_OVERVIEW",
            "params": {"detail_level": "BASIC"},
        },
    },
    {
        "input": {
            "message": "Сводка по спринту без деталей.",
        },
        "expected": {
            "intent": "TEAM_OVERVIEW",
            "params": {"detail_level": "BASIC"},
        },
    },

    {
        "input": {
            "message": "Сделай подробный обзор спринта с рисками и прогнозом.",
        },
        "expected": {
            "intent": "TEAM_OVERVIEW",
            "params": {"detail_level": "EXTENDED"},
        },
    },
    {
        "input": {
            "message": "Нужен детальный отчёт по спринту: прогресс и узкие места.",
        },
        "expected": {
            "intent": "TEAM_OVERVIEW",
            "params": {"detail_level": "EXTENDED"},
        },
    },

    {
        "input": {
            "message": "Какие сейчас основные риски по спринту?",
        },
        "expected": {
            "intent": "TEAM_RISKS",
            "params": {},
        },
    },
    {
        "input": {
            "message": "Что может сорвать текущий спринт?",
        },
        "expected": {
            "intent": "TEAM_RISKS",
            "params": {},
        },
    },
    {
        "input": {
            "message": "Есть ли критичные блокеры у команды?",
        },
        "expected": {
            "intent": "TEAM_RISKS",
            "params": {},
        },
    },

    {
        "input": {
            "message": "Как распределена нагрузка по участникам спринта?",
        },
        "expected": {
            "intent": "WORKLOAD",
            "params": {},
        },
    },
    {
        "input": {
            "message": "Кто сейчас перегружен задачами?",
        },
        "expected": {
            "intent": "WORKLOAD",
            "params": {},
        },
    },
    {
        "input": {
            "message": "Есть ли перекос по workload в команде?",
        },
        "expected": {
            "intent": "WORKLOAD",
            "params": {},
        },
    },

    {
        "input": {
            "message": "Какие задачи блокируют релиз в этом спринте?",
        },
        "expected": {
            "intent": "RELEASE_BLOCKERS",
            "params": {},
        },
    },
    {
        "input": {
            "message": "Что не даёт закрыть цели спринта?",
        },
        "expected": {
            "intent": "RELEASE_BLOCKERS",
            "params": {},
        },
    },

    {
        "input": {
            "message": "Кого лучше нанять: разработчика или QA?",
        },
        "expected": {
            "intent": "UNSUPPORTED",
        },
    },
    {
        "input": {
            "message": "Как нам улучшить процессы разработки?",
        },
        "expected": {
            "intent": "UNSUPPORTED",
        },
    },
    {
        "input": {
            "message": "Сколько времени займёт новая фича?",
        },
        "expected": {
            "intent": "UNSUPPORTED",
        },
    },
    {
        "input": {
            "message": "Как мотивировать команду работать быстрее?",
        },
        "expected": {
            "intent": "UNSUPPORTED",
        },
    },
    {
        "input": {
            "message": "Предложи стратегию развития команды на квартал.",
        },
        "expected": {
            "intent": "UNSUPPORTED",
        },
    },
]
