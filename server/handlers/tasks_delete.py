# handlers/tasks_delete.py
"""
Handler module for the 'tasks_delete' route.
This handler allows authenticated users to delete an existing task by its ID.
It performs basic authentication (verifies the requester is a registered user)
and delegates the deletion logic to the tasks data module.
No additional authorization (e.g., ownership or admin check) is enforced.
"""

from logger import get_logger
from modules.tasks import delete_task

# Initialize a dedicated logger for this handler to record deletion events and errors.
logger = get_logger("tasks_delete")


def _delete_task_core(task_id):
    """
    Internal helper function that delegates the task deletion operation to the data layer.

    This function wraps the `delete_task` function from `modules.tasks` to encapsulate
    type conversion (string to integer) and provide a stable interface for the handler.

    :param task_id: (str or int) The identifier of the task to delete. Will be converted to `int`.
    :return: (bool) `True` if a task with the given ID was found and successfully deleted;
             `False` if no task with that ID exists.
    :raises ValueError: If `task_id` cannot be converted to an integer.
    """
    return delete_task(int(task_id))


def handle_request(data):
    """
    Handle an HTTP request to delete a task.

    This function implements a basic security and validation workflow:
      1. Validates that the request includes both `telegram_user_id` and `id` (task ID).
      2. Authenticates the user by verifying their existence in the user registry.
      3. Attempts to delete the specified task.
      4. Returns an appropriate response based on the outcome.

    The handler conforms to the standard interface used by the application’s routing system:
    it accepts a single `data` dictionary and returns a tuple
    `(response_body: dict, http_status_code: int)`.

    :param  (dict) A dictionary containing:
                 - `"telegram_user_id"` (str or int): ID of the user making the deletion request.
                 - `"id"` (str or int): ID of the task to delete.
    :return: (tuple) A tuple containing:
             - (dict): Either a success object `{"status": "deleted"}` or an error object
                       with an `"error"` key.
             - (int): HTTP status code:
                       - 200 OK (task successfully deleted)
                       - 400 Bad Request (missing `telegram_user_id` or `id`)
                       - 401 Unauthorized (user not found in the system)
                       - 404 Not Found (task with the given ID does not exist)
                       - 500 Internal Server Error (unexpected exception during deletion)
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

        # Step 3: Attempt to delete the task
        success = _delete_task_core(task_id)
        if not success:
            return {"error": "Task not found"}, 404

        # Step 4: Log successful deletion for audit purposes
        logger.info(f"Task {task_id} deleted by {telegram_user_id}")

        return {"status": "deleted"}, 200

    except Exception as e:
        # Log full exception details internally for debugging; do not expose to client
        logger.error(f"Task delete error: {e}", exc_info=True)
        return {"error": "Delete failed"}, 500