"""
Task management module that provides CRUD operations for tasks stored in a CSV file.
Tasks support metadata such as status, priority, assignee, due date, and tags (stored as JSON).
This module enforces data validation against predefined status and priority lists from config.
"""

import time
import json
import csv
from config import CSV_FILES, TASK_STATUSES, PRIORITIES

# Define the schema (column names) for the tasks CSV file.
# The order must match how data is written and read.
TASK_FIELDS = [
    "task_id", "title", "description", "status", "assignee_user_id",
    "creator_user_id", "created_at", "updated_at", "due_date",
    "completed_at", "priority", "tags"
]


def _ensure_file():
    """
    Ensure the tasks CSV file exists; if not, create it with a header row.

    This internal utility function is called by other public functions to guarantee
    that the file is present before performing read or write operations.

    The file path is retrieved from the application configuration via `CSV_FILES["tasks"]`.

    :return: None
    """
    import os
    path = CSV_FILES["tasks"]
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=TASK_FIELDS)
            w.writeheader()


def list_tasks():
    """
    Retrieve all tasks from the CSV file and parse structured fields.

    This function reads the entire tasks file, converts the `tags` field from a JSON string
    back into a Python list, and returns a list of task dictionaries.

    If the `tags` field is malformed or empty, it defaults to an empty list.

    :return: (list[dict]) A list of task records. Each record is a dictionary with keys
             matching `TASK_FIELDS`. The `tags` value is always a list.
    """
    _ensure_file()
    with open(CSV_FILES["tasks"], "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        for r in rows:
            try:
                r["tags"] = json.loads(r["tags"])
            except (json.JSONDecodeError, TypeError):
                r["tags"] = []
        return rows


def create_task(data):
    """
    Create a new task and append it to the CSV file.

    Validates the `status` and `priority` fields against allowed values from the config.
    Assigns a new unique `task_id`, sets timestamps, and serializes the `tags` field to JSON.

    Required fields in `data`:
        - `"title"` (str)
        - `"creator_user_id"` (str or int)

    Optional fields (with defaults if omitted):
        - `"description"` → `""`
        - `"status"` → `"todo"`
        - `"priority"` → `"medium"`
        - `"assignee_user_id"` → `""`
        - `"due_date"` → `""`
        - `"tags"` → `[]`

    :param data: (dict) A dictionary containing task attributes.
    :return: (int) The newly assigned `task_id`.
    :raises ValueError: If `status` or `priority` is not in the allowed set.
    :raises KeyError: If required fields (`title`, `creator_user_id`) are missing.
    """
    if data.get("status", "todo") not in TASK_STATUSES:
        raise ValueError("Invalid status")
    if data.get("priority", "medium") not in PRIORITIES:
        raise ValueError("Invalid priority")

    _ensure_file()
    rows = list_tasks()
    task_id = max([int(r["task_id"]) for r in rows], default=0) + 1
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    row = {
        "task_id": task_id,
        "title": data["title"],
        "description": data.get("description", ""),
        "status": data.get("status", "todo"),
        "assignee_user_id": data.get("assignee_user_id", ""),
        "creator_user_id": data["creator_user_id"],
        "created_at": now,
        "updated_at": now,
        "due_date": data.get("due_date", ""),
        "completed_at": "",
        "priority": data.get("priority", "medium"),
        "tags": data.get("tags", [])
    }

    # Serialize list fields (e.g., tags) to JSON strings before writing
    with open(CSV_FILES["tasks"], "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TASK_FIELDS)
        serialized_row = {k: json.dumps(v) if isinstance(v, list) else v for k, v in row.items()}
        w.writerow(serialized_row)

    return task_id


def update_task(task_id, updates):
    """
    Update an existing task by its ID with provided field changes.

    Only fields in `TASK_FIELDS` are updated. The function validates `status` and `priority`
    if they are included in `updates`—invalid values are silently ignored (not applied).

    If the `status` is updated to `"done"` and `completed_at` was previously empty,
    the current timestamp is recorded in `completed_at`.

    The `updated_at` field is always refreshed on any successful update.

    :param task_id: (int) The numeric ID of the task to update.
    :param updates: (dict) A dictionary of field names and new values to apply.
                    Only keys present in `TASK_FIELDS` are considered.
    :return: (bool) `True` if a task with the given ID was found and updated;
             `False` if no matching task exists.
    """
    rows = list_tasks()
    found = False
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    for r in rows:
        if int(r["task_id"]) == task_id:
            # Apply valid updates
            for k, v in updates.items():
                if k in TASK_FIELDS:
                    if k == "status" and v not in TASK_STATUSES:
                        continue  # skip invalid status
                    if k == "priority" and v not in PRIORITIES:
                        continue  # skip invalid priority
                    r[k] = v

            r["updated_at"] = now
            # Auto-set completion timestamp if status becomes 'done'
            if updates.get("status") == "done" and not r["completed_at"]:
                r["completed_at"] = now

            found = True
            break

    if found:
        # Rewrite the entire file with updated data
        with open(CSV_FILES["tasks"], "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=TASK_FIELDS)
            w.writeheader()
            # Serialize list fields (e.g., tags) before writing
            serialized_rows = [
                {k: json.dumps(v) if isinstance(v, list) else v for k, v in r.items()}
                for r in rows
            ]
            w.writerows(serialized_rows)

    return found


def delete_task(task_id):
    """
    Delete a task by its ID from the CSV file.

    The function reads all tasks, filters out the one with the matching `task_id`,
    and writes the remaining tasks back to the file.

    :param task_id: (int) The numeric ID of the task to delete.
    :return: (bool) `True` if a task was found and deleted;
             `False` if no task with the given ID exists.
    """
    rows = list_tasks()
    filtered = [r for r in rows if int(r["task_id"]) != task_id]

    if len(filtered) == len(rows):
        # No task was removed
        return False

    # Rewrite the file without the deleted task
    with open(CSV_FILES["tasks"], "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TASK_FIELDS)
        w.writeheader()
        serialized_rows = [
            {k: json.dumps(v) if isinstance(v, list) else v for k, v in r.items()}
            for r in filtered
        ]
        w.writerows(serialized_rows)

    return True