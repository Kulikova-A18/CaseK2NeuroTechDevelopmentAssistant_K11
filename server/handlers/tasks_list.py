# handlers/tasks_list.py
"""
Handler module for the 'tasks_list' route.
This handler retrieves a list of all tasks stored in the system.
It enforces basic authentication by verifying that the requester is a registered user
via their Telegram user ID. No role-based authorization is applied—any registered user
may view all tasks (suitable for team-wide visibility).
"""

from logger import get_logger
from modules.tasks import list_tasks

# Initialize a dedicated logger for this handler to record operational events and errors.
logger = get_logger("tasks_list")


def _list_tasks_core():
    """
    Internal helper function that retrieves all tasks from persistent storage.

    This function wraps the `list_tasks` function from the `modules.tasks` module
    to provide a stable abstraction layer. This allows future enhancements
    (e.g., filtering, pagination, or performance optimizations) without modifying
    the main request-handling logic.

    :return: (list[dict]) A list of task records. Each dictionary contains all fields
             defined in `TASK_FIELDS` (e.g., `task_id`, `title`, `status`, `tags`, etc.).
             The `tags` field is automatically deserialized from JSON into a Python list.
    """
    return list_tasks()


def handle_request(data):
    """
    Handle an HTTP request to list all tasks.

    This function implements a simple authentication workflow:
      1. Validates that the request includes a `telegram_user_id`.
      2. Verifies that the user exists in the system.
      3. Retrieves and returns the full list of tasks.

    The handler conforms to the standard interface expected by the application’s routing layer:
    it accepts a single `data` dictionary and returns a tuple
    `(response_body: list or dict, http_status_code: int)`.

    :param  (dict) A dictionary containing request context. Must include:
                 - `"telegram_user_id"` (str or int): The Telegram ID of the requesting user.
    :return: (tuple) A tuple containing:
             - (list or dict): Either:
                                 - A list of task dictionaries on success, or
                                 - An error object with an `"error"` key on failure.
             - (int): HTTP status code:
                       - 200 OK (tasks successfully retrieved)
                       - 401 Unauthorized (missing or unregistered `telegram_user_id`)
                       - 500 Internal Server Error (unexpected exception during data retrieval)
    """
    try:
        # Step 1: Extract and validate the requester's Telegram ID
        telegram_user_id = data.get("telegram_user_id")
        if not telegram_user_id:
            return {"error": "Missing telegram_user_id"}, 401

        # Step 2: Authenticate: ensure the user exists in the system
        from modules.users import get_user_by_telegram_id
        if not get_user_by_telegram_id(telegram_user_id):
            return {"error": "Unauthorized"}, 401

        # Step 3: Fetch all tasks
        tasks = _list_tasks_core()

        # Return the full task list (caller or middleware may apply further filtering if needed)
        return tasks, 200

    except Exception as e:
        # Log full exception details internally for debugging, but do not expose them to the client
        logger.error(f"List tasks error: {e}", exc_info=True)
        return {"error": "Failed to fetch tasks"}, 500