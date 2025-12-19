DAILY_CASES = [
    {
        "name": "clean_daily_two_tasks",
        "input": {
            "message": "Вчера закрыл TASK-1, сегодня начну TASK-2. Блокеров нет.",
            "role": "DEV",
            "daily_state": {"mode": "INITIAL", "quality_retries": 0},
        },
        "tracker_tasks": {"TASK-1", "TASK-2"},
        "expected": {"needs_clarification": False},
    },
    {
        "name": "single_task_progress",
        "input": {
            "message": "Вчера и сегодня работаю над TASK-3, блокеров нет.",
            "role": "DEV",
            "daily_state": {"mode": "INITIAL", "quality_retries": 0},
        },
        "tracker_tasks": {"TASK-3"},
        "expected": {"needs_clarification": False},
    },
    {
        "name": "vague_daily",
        "input": {
            "message": "Работал над задачами, сегодня продолжу.",
            "role": "DEV",
            "daily_state": {"mode": "INITIAL", "quality_retries": 0},
        },
        "tracker_tasks": {"TASK-10"},
        "expected": {"needs_clarification": True},
    },
    {
        "name": "daily_with_blocker_access",
        "input": {
            "message": "Вчера TASK-4, сегодня TASK-5. Блокер: жду доступы.",
            "role": "DEV",
            "daily_state": {"mode": "INITIAL", "quality_retries": 0},
        },
        "tracker_tasks": {"TASK-4", "TASK-5"},
        "expected": {"needs_clarification": False},
    },
    {
        "name": "daily_with_blocker_dependency",
        "input": {
            "message": "Вчера TASK-6, сегодня TASK-7. Заблокирован, жду апрув.",
            "role": "DEV",
            "daily_state": {"mode": "INITIAL", "quality_retries": 0},
        },
        "tracker_tasks": {"TASK-6", "TASK-7"},
        "expected": {"needs_clarification": False},
    },
    {
        "name": "unknown_task_id",
        "input": {
            "message": "Вчера TASK-999, сегодня продолжу.",
            "role": "DEV",
            "daily_state": {"mode": "INITIAL", "quality_retries": 0},
        },
        "tracker_tasks": {"TASK-1", "TASK-2"},
        "expected": {"needs_clarification": False},
    },
    {
        "name": "no_tasks_mentioned",
        "input": {
            "message": "Вчера изучал код, сегодня продолжу.",
            "role": "DEV",
            "daily_state": {"mode": "INITIAL", "quality_retries": 0},
        },
        "tracker_tasks": {"TASK-11"},
        "expected": {"needs_clarification": True},
    },
    {
        "name": "multiple_tasks_with_status",
        "input": {
            "message": "Вчера TASK-8 почти закончил, сегодня доделаю TASK-8 и начну TASK-9.",
            "role": "DEV",
            "daily_state": {"mode": "INITIAL", "quality_retries": 0},
        },
        "tracker_tasks": {"TASK-8", "TASK-9"},
        "expected": {"needs_clarification": False},
    },
    {
        "name": "qa_daily",
        "input": {
            "message": "Вчера тестировал TASK-12, сегодня продолжаю регресс.",
            "role": "QA",
            "daily_state": {"mode": "INITIAL", "quality_retries": 0},
        },
        "tracker_tasks": {"TASK-12"},
        "expected": {"needs_clarification": False},
    },
    {
        "name": "empty_daily",
        "input": {
            "message": "",
            "role": "DEV",
            "daily_state": {"mode": "INITIAL", "quality_retries": 0},
        },
        "tracker_tasks": {"TASK-13"},
        "expected": {"needs_clarification": True},
    },
    {
        "name": "daily_with_risk_phrase",
        "input": {
            "message": "Вчера TASK-14, сегодня TASK-15. Есть риск не успеть.",
            "role": "DEV",
            "daily_state": {"mode": "INITIAL", "quality_retries": 0},
        },
        "tracker_tasks": {"TASK-14", "TASK-15"},
        "expected": {"needs_clarification": False},
    },
    {
        "name": "daily_with_nonblocking_issue",
        "input": {
            "message": "Вчера TASK-16, сегодня TASK-17. Есть мелкие вопросы.",
            "role": "DEV",
            "daily_state": {"mode": "INITIAL", "quality_retries": 0},
        },
        "tracker_tasks": {"TASK-16", "TASK-17"},
        "expected": {"needs_clarification": False},
    },
    {
        "name": "daily_only_today",
        "input": {
            "message": "Сегодня начну TASK-18.",
            "role": "DEV",
            "daily_state": {"mode": "INITIAL", "quality_retries": 0},
        },
        "tracker_tasks": {"TASK-18"},
        "expected": {"needs_clarification": True},
    },
    {
        "name": "daily_only_yesterday",
        "input": {
            "message": "Вчера работал над TASK-19.",
            "role": "DEV",
            "daily_state": {"mode": "INITIAL", "quality_retries": 0},
        },
        "tracker_tasks": {"TASK-19"},
        "expected": {"needs_clarification": True},
    },
    {
        "name": "daily_with_multiple_blockers",
        "input": {
            "message": "Вчера TASK-20, сегодня TASK-21. Блокеры: жду доступы и апрув.",
            "role": "DEV",
            "daily_state": {"mode": "INITIAL", "quality_retries": 0},
        },
        "tracker_tasks": {"TASK-20", "TASK-21"},
        "expected": {"needs_clarification": False},
    },
    {
        "name": "daily_manager_style",
        "input": {
            "message": "Вчера созвоны и планирование, сегодня уточняю требования.",
            "role": "PM",
            "daily_state": {"mode": "INITIAL", "quality_retries": 0},
        },
        "tracker_tasks": {"TASK-22"},
        "expected": {"needs_clarification": True},
    },
]
