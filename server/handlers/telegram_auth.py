# handlers/telegram_auth.py
"""
Handler module for the 'telegram_auth' route.
This handler authenticates a user based on their Telegram user ID.
It checks whether the user exists in the system and is marked as active.
If successful, it returns the full user record (excluding sensitive handling elsewhere).
The handler supports both 'user_id' and 'telegram_user_id' as input field names for flexibility.
"""

from logger import get_logger
from modules.users import authenticate_user

# Initialize a dedicated logger for this handler to record authentication attempts and errors.
logger = get_logger("telegram_auth")


def handle_request(data):
    """
    Handle an HTTP request to authenticate a Telegram user.

    This function attempts to authenticate a user by their Telegram ID.
    It accepts the ID under either the key `"user_id"` or `"telegram_user_id"`
    to accommodate different client implementations.

    The function delegates authentication logic to `authenticate_user` from the `modules.users`
    module, which verifies existence and active status, and updates the `last_login` timestamp
    upon success.

    The handler conforms to the standard interface: it takes a single `data` dictionary
    and returns a tuple `(response_body: dict, http_status_code: int)`.

    :param  (dict) A dictionary containing the request payload. Must include one of:
                 - `"user_id"` (str or int), or
                 - `"telegram_user_id"` (str or int)
                 representing the Telegram user identifier.
    :return: (tuple) A tuple containing:
             - (dict): Either:
                       - The full user record (as stored in the backend) on success, or
                       - An error object with an `"error"` key on failure.
             - (int): HTTP status code:
                       - 200 OK (authentication successful)
                       - 400 Bad Request (missing user ID in request)
                       - 404 Not Found (user does not exist or is inactive)
                       - 500 Internal Server Error (unexpected exception)
    """
    try:
        # Accept either 'user_id' or 'telegram_user_id' for compatibility
        telegram_user_id = data.get("user_id") or data.get("telegram_user_id")
        if not telegram_user_id:
            return {"error": "user_id required"}, 400

        # Attempt to authenticate the user (checks existence and active status)
        user = authenticate_user(telegram_user_id)

        if not user:
            # Log failed attempt (useful for monitoring brute-force or misconfigurations)
            logger.warning(f"Auth failed for telegram_user_id={telegram_user_id}")
            return {"error": "User not found or inactive"}, 404

        # Log successful authentication
        logger.info(f"Authenticated user: {telegram_user_id}")

        # Return the user record as-is (caller or middleware should sanitize if needed)
        return user, 200

    except Exception as e:
        # Log full exception details internally for debugging
        logger.error(f"Auth error: {e}", exc_info=True)
        return {"error": "Authentication failed"}, 500