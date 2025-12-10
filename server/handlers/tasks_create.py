# handlers/tasks_create.py
"""
Handler module for the 'tasks_create' route.
This handler allows authenticated users to create new tasks.
It verifies that the requester is a registered user, injects the internal user ID
as the task creator, and delegates task creation to the data layer.
"""

from logger import get_logger
from modules.tasks import create_task

# Initialize a dedicated logger for this handler to record task creation events and errors.
logger = get_logger("tasks_create")


def _create_task_core(data):
    """
    Internal helper function that delegates task creation to the data module.

    This function wraps the `create_task` function from `modules.tasks` to provide
    a stable interface and allow future enhancements (e.g., validation, hooks, or auditing)
    without modifying the main request logic.

    :param  (dict) A dictionary containing task attributes. Must include:
                 - `"title"` (str): The task title.
                 - Optional fields: `"description"`, `"status"`, `"priority"`,
                   `"assignee_user_id"`, `"due_date"`, `"tags"` (list).
                 - Note: `"creator_user_id"` must already be set (typically by the handler).
    :return: (int) The newly assigned numeric `task_id`.
    :raises ValueError: If `"status"` or `"priority"` is not in the allowed set (from config).
    :raises KeyError: If required fields (`"title"`, `"creator_user_id"`) are missing.
    """
    return create_task(data)


def handle_request(data):
    """
    Handle an HTTP request to create a new task.

    This function implements a secure workflow for task creation:
      1. Validates that the request includes a `telegram_user_id`.
      2. Authenticates the user by looking up their record.
      3. Ensures the task has a `title`.
      4. Injects the internal `user_id` (from user record) as `creator_user_id`.
      5. Delegates creation to the core logic and returns the new task ID.

    The handler conforms to the standard interface expected by the application’s routing system:
    it accepts a single `data` dictionary and returns a tuple
    `(response_body: dict, http_status_code: int)`.

    :param  (dict) A dictionary containing:
                 - `"telegram_user_id"` (str or int): Telegram ID of the requesting user.
                 - `"title"` (str): Title of the new task (required).
                 - Optional: `"description"`, `"status"`, `"priority"`, `"assignee_user_id"`,
                   `"due_date"`, `"tags"` (list of strings).
    :return: (tuple) A tuple containing:
             - (dict): Either:
                         - `{"task_id": int}` on success, or
                         - An error object with an `"error"` key on failure.
             - (int): HTTP status code:
                       - 201 Created (task successfully created)
                       - 400 Bad Request (missing `title` or invalid task data)
                       - 401 Unauthorized (missing or unregistered `telegram_user_id`)
                       - 500 Internal Server Error (unexpected exception during creation)
    """
    try:
        # Step 1: Extract and validate the requester's Telegram ID
        telegram_user_id = data.get("telegram_user_id")
        if not telegram_user_id:
            return {"error": "Missing telegram_user_id"}, 401

        # Step 2: Authenticate the user and retrieve their internal record
        from modules.users import get_user_by_telegram_id
        user = get_user_by_telegram_id(telegram_user_id)
        if not user:
            return {"error": "Unauthorized"}, 401

        # Step 3: Validate required task field
        if "title" not in data:
            return {"error": "Missing title"}, 400

        # Step 4: Enrich data with internal creator ID (not the Telegram ID)
        # This ensures referential integrity with the users CSV schema
        data["creator_user_id"] = user["user_id"]

        # Step 5: Create the task
        task_id = _create_task_core(data)

        # Log successful creation for audit and monitoring
        logger.info(f"Task {task_id} created by {telegram_user_id}")

        return {"task_id": task_id}, 201

    except Exception as e:
        # Log full exception details internally; return generic error to client
        logger.error(f"Task create error: {e}", exc_info=True)
        return {"error": "Failed to create task"}, 500