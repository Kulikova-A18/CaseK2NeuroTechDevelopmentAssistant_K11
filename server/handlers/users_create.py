# handlers/users_create.py
"""
Handler module for the 'users_create' route.
This handler allows authenticated administrators to manually create new user accounts.
It enforces role-based access control and validates required input fields before
delegating user creation to the underlying data module.
"""

from logger import get_logger
from modules.users import create_user_explicit, is_admin, get_user_by_telegram_id

# Initialize a dedicated logger for this handler to record creation events and errors.
logger = get_logger("users_create")


def _create_user_core(data):
    """
    Internal helper function that delegates user creation to the data layer.

    This function wraps the `create_user_explicit` function from `modules.users`
    to provide a stable interface for the handler and allow future enhancements
    (e.g., validation, hooks, or auditing) without modifying the main request logic.

    :param data: (dict) A dictionary containing user attributes to be stored.
                 Must include at least "telegram_user_id" and "role".
                 Optional fields: "telegram_username", "full_name".
    :return: (int) The newly assigned numeric `user_id`.
    :raises KeyError: If required fields are missing in `data`.
    :raises ValueError: If invalid values (e.g., unsupported role) are provided.
    """
    return create_user_explicit(data)


def handle_request(data):
    """
    Handle an HTTP request to create a new user account.

    This function implements a secure workflow for user creation:
      1. Verifies that the requester provides a `telegram_user_id`.
      2. Authenticates and authorizes the requester as an administrator.
      3. Validates that all required fields for the new user are present.
      4. Creates the new user and returns the generated ID.

    The function conforms to the standard handler interface: it accepts a single `data`
    dictionary (typically derived from the request payload) and returns a tuple
    `(response_body: dict, http_status_code: int)`.

    :param  (dict) A dictionary containing:
                 - `"telegram_user_id"` (str or int): ID of the **requesting admin**.
                 - `"role"` (str): Role for the **new user** (e.g., "admin" or "member").
                 - Optional: `"telegram_username"`, `"full_name"` for the new user.
    :return: (tuple) A tuple containing:
             - (dict): Either a success object `{"user_id": int}` or an error object
                       with an `"error"` key.
             - (int): HTTP status code:
                       - 201 Created (success)
                       - 400 Bad Request (missing required field)
                       - 401 Unauthorized (missing requester ID)
                       - 403 Forbidden (requester is not admin)
                       - 500 Internal Server Error (unexpected exception)
    """
    try:
        # The admin is identified by this field
        admin_telegram_id = data.get("admin_telegram_id")
        if not admin_telegram_id:
            return {"error": "Missing admin_telegram_id"}, 401

        from modules.users import get_user_by_telegram_id
        admin_user = get_user_by_telegram_id(admin_telegram_id)
        if not admin_user or not is_admin(admin_user):
            return {"error": "Admin access required"}, 403

        # New user data is in a nested object or flat with clear names
        new_telegram_id = data.get("new_telegram_user_id")
        role = data.get("role")
        if not new_telegram_id or not role:
            return {"error": "Missing new_telegram_user_id or role"}, 400

        # Build new user data
        new_user_data = {
            "telegram_user_id": new_telegram_id,
            "role": role,
            "telegram_username": data.get("telegram_username", ""),
            "full_name": data.get("full_name", "")
        }

        user_id = _create_user_core(new_user_data)
        logger.info(f"Admin {admin_telegram_id} created user {user_id}")
        return {"user_id": user_id}, 201

    except Exception as e:
        # Log unexpected errors with full stack trace for debugging
        logger.error(f"User create error: {e}", exc_info=True)
        return {"error": "Failed to create user"}, 500