DIGEST_CASES = [
    {
        "name": "basic_team_digest",
        "input": {
            "data": {
                "task_counts": {
                    "todo": 2,
                    "in_progress": 3,
                    "done": 5,
                },
                "current_tasks": [
                    {
                        "id": "TASK-1",
                        "title": "Fix login bug",
                    },
                    {
                        "id": "TASK-2",
                        "title": "Add analytics",
                    },
                ],
                "blockers": [
                    {
                        "task_id": "TASK-3",
                        "text": "Ждём доступы",
                        "severity": "high",
                    }
                ],
                "notes": [
                    "Риск сдвига сроков по TASK-3",
                ],
            }
        },
    }
]
