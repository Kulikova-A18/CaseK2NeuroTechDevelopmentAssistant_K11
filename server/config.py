import os

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

CSV_FILES = {
    "users": os.path.join(DATA_DIR, "users.csv"),
    "tasks": os.path.join(DATA_DIR, "tasks.csv"),
    "docs": os.path.join(DATA_DIR, "docs.csv"),
    "events": os.path.join(DATA_DIR, "events.csv"),
}

ALLOWED_ROLES = {"admin", "manager", "member", "viewer"}
TASK_STATUSES = {"todo", "in_progress", "done"}
PRIORITIES = {"low", "medium", "high", "urgent"}