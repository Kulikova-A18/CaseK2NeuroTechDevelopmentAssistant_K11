# handlers/users_list.py
"""
Handler module for the 'users_list' route.
This handler allows authenticated administrators to retrieve a list of all registered users,
with sensitive fields (e.g., Telegram user ID) removed from the response for privacy.
"""

from logger import get_logger
from modules.users import list_all_users, is_admin, get_user_by_telegram_id

# Initialize a dedicated logger for this handler to facilitate debugging and auditing.
logger = get_logger("users_list")


def _list_users_core():
    """
    Internal helper function that retrieves all user records from persistent storage.

    This function wraps the `list_all_users` function from the `modules.users` module
    to allow potential future modifications (e.g., filtering, pagination) without
    changing the public handler interface.

    :return: (list[dict]) A list of user dictionaries, each containing all user fields
             as stored in the backend (including sensitive data like `telegram_user_id`).
    """
    return list_all_users()


def handle_request(data):
    """
    Handle an HTTP request to list all system users.

    This function implements a secure, role-based access control flow:
      1. Validates that the request includes a `telegram_user_id`.
      2. Authenticates the user by looking up their record.
      3. Authorizes the action by verifying the user has the `"admin"` role.
      4. Retrieves all user records and removes sensitive fields before returning them.

    The function conforms to the expected handler interface: it accepts a single `data`
    dictionary (typically from the Flask request JSON or URL parameters) and returns
    a tuple `(response_body: dict or list, http_status_code: int)`.

    :param data: (dict) A dictionary containing request context. Must include:
                 - `"telegram_user_id"` (str or int): The Telegram ID of the requesting user.
    :return: (tuple) A tuple containing:
             - (dict or list): Either a list of sanitized user records (on success)
               or an error object with a `"error"` key (on failure).
             - (int): HTTP status code (e.g., 200, 401, 403, 500).
    """
    try:
        # Extract and validate the Telegram user ID from the request data
        telegram_user_id = data.get("telegram_user_id")
        if not telegram_user_id:
            return {"error": "Missing telegram_user_id"}, 401

        # Authenticate: check if the user exists
        user = get_user_by_telegram_id(telegram_user_id)
        if not user:
            return {"error": "Unauthorized"}, 401

        # Authorize: only admins may list users
        if not is_admin(user):
            logger.warning(f"Non-admin {telegram_user_id} tried to access user list")
            return {"error": "Access denied"}, 403

        # Retrieve all user records
        users = _list_users_core()

        # Sanitize: remove sensitive fields before sending to client
        sanitized = [
            {k: v for k, v in u.items() if k not in ["telegram_user_id"]}
            for u in users
        ]

        return sanitized, 200

    except Exception as e:
        # Log unexpected errors with full traceback for debugging
        logger.error(f"Users list error: {e}", exc_info=True)
        return {"error": "Failed to fetch users"}, 500