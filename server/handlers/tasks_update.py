# handlers/tasks_update.py
"""
Handler module for the 'tasks_update' route.
This handler allows authenticated users to update existing tasks by providing
a task ID and the fields to modify. It performs basic authentication and delegates
the actual update logic to the tasks data module.
"""

from logger import get_logger
from modules.tasks import update_task

# Initialize a dedicated logger for this handler to record update events and errors.
logger = get_logger("tasks_update")


def _update_task_core(task_id, updates):
    """
    Internal helper function that delegates the task update operation to the data layer.

    This function wraps the `update_task` function from `modules.tasks` to provide
    a stable interface and encapsulate type conversion (e.g., string to int for `task_id`).

    :param task_id: (str or int) The identifier of the task to update. Will be converted to `int`.
    :param updates: (dict) A dictionary of field names and new values to apply to the task.
                    Only fields present in `TASK_FIELDS` (from the tasks module) will be updated.
                    Invalid `status` or `priority` values are silently ignored.
    :return: (bool) `True` if a task with the given ID was found and updated;
             `False` if no matching task exists.
    :raises ValueError: If `task_id` cannot be converted to an integer.
    """
    return update_task(int(task_id), updates)


def handle_request(data):
    """
    Handle an HTTP request to update an existing task.

    This function implements a basic security and validation workflow:
      1. Validates that the request includes both `telegram_user_id` and `id` (task ID).
      2. Authenticates the user by verifying their existence in the user registry.
      3. Extracts update fields (excluding authentication and routing keys).
      4. Delegates the update to the core logic and returns an appropriate response.

    The handler conforms to the standard interface: it accepts a single `data` dictionary
    (typically from a JSON request body or merged path/query parameters) and returns
    a tuple `(response_body: dict, http_status_code: int)`.

    :param  (dict) A dictionary containing:
                 - `"telegram_user_id"` (str or int): ID of the user making the request.
                 - `"id"` (str or int): ID of the task to update.
                 - Optional: any other key-value pairs representing task fields to update
                   (e.g., `"status"`, `"priority"`, `"title"`, `"assignee_user_id"`, etc.).
    :return: (tuple) A tuple containing:
             - (dict): Either a success object `{"status": "updated"}` or an error object
                       with an `"error"` key.
             - (int): HTTP status code:
                       - 200 OK (task successfully updated)
                       - 400 Bad Request (missing `telegram_user_id` or `id`)
                       - 401 Unauthorized (user not found)
                       - 404 Not Found (task does not exist)
                       - 500 Internal Server Error (unexpected exception during update)
    """
    try:
        # Step 1: Extract and validate required identifiers
        telegram_user_id = data.get("telegram_user_id")
        task_id = data.get("id")
        if not telegram_user_id or not task_id:
            return {"error": "Missing telegram_user_id or task ID"}, 400

        # Step 2: Authenticate the requesting user (existence check only)
        from modules.users import get_user_by_telegram_id
        if not get_user_by_telegram_id(telegram_user_id):
            return {"error": "Unauthorized"}, 401

        # Step 3: Prepare update payload (exclude auth and routing fields)
        updates = {k: v for k, v in data.items() if k not in ("telegram_user_id", "id")}

        # Step 4: Perform the update
        success = _update_task_core(task_id, updates)
        if not success:
            return {"error": "Task not found"}, 404

        # Log successful update for audit purposes
        logger.info(f"Task {task_id} updated by {telegram_user_id}")

        return {"status": "updated"}, 200

    except Exception as e:
        # Log full exception details internally, but return a generic error to the client
        logger.error(f"Task update error: {e}", exc_info=True)
        return {"error": "Update failed"}, 500