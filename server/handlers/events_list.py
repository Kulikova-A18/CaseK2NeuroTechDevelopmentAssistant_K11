# handlers/events_list.py
"""
Handler module for the 'events_list' route.
This handler retrieves a list of all calendar events stored in the system.
It enforces basic authentication by verifying that the requester is a registered user
via their Telegram user ID. No role-based restrictions are applied—any authenticated
user may view all events.
"""

from logger import get_logger
from modules.events import list_events

# Initialize a dedicated logger for this handler to record operational events and errors.
logger = get_logger("events_list")


def _list_events_core():
    """
    Internal helper function that retrieves all events from persistent storage.

    This function wraps the `list_events` function from the `modules.events` module
    to provide a stable abstraction layer. This design allows future enhancements
    (e.g., filtering by date range, pagination, or performance optimization)
    without modifying the main request-handling logic.

    :return: (list[dict]) A list of event records. Each dictionary contains all fields
             defined in `EVENT_FIELDS` from the events module:
             - `event_id` (str)
             - `title` (str)
             - `start` (str)
             - `end` (str, possibly empty)
             - `creator_user_id` (str)
             - `created_at` (str, ISO-like timestamp)
    """
    return list_events()


def handle_request(data):
    """
    Handle an HTTP request to list all calendar events.

    This function implements a minimal authentication workflow:
      1. Validates that the request includes a `telegram_user_id`.
      2. Verifies that the user exists in the system.
      3. Retrieves and returns the full list of events.

    The handler follows the standard interface expected by the application’s routing system:
    it accepts a single `data` dictionary (typically derived from request JSON or path parameters)
    and returns a tuple `(response_body: list or dict, http_status_code: int)`.

    :param  (dict) A dictionary containing request context. Must include:
                 - `"telegram_user_id"` (str or int): The Telegram ID of the requesting user.
    :return: (tuple) A tuple containing:
             - (list or dict): Either:
                                 - A list of event dictionaries on success, or
                                 - An error object with an `"error"` key on failure.
             - (int): HTTP status code:
                       - 200 OK (events successfully retrieved)
                       - 401 Unauthorized (missing or unregistered `telegram_user_id`)
                       - 500 Internal Server Error (unexpected exception during data retrieval)
    """
    try:
        # Step 1: Extract and validate the requester's Telegram ID
        telegram_user_id = data.get("telegram_user_id")
        if not telegram_user_id:
            return {"error": "Missing telegram_user_id"}, 401

        # Step 2: Authenticate: ensure the user exists in the user registry
        from modules.users import get_user_by_telegram_id
        if not get_user_by_telegram_id(telegram_user_id):
            return {"error": "Unauthorized"}, 401

        # Step 3: Fetch all events
        events = _list_events_core()

        # Return the full list of events (no filtering or sanitization applied)
        return events, 200

    except Exception as e:
        # Log full exception details internally for debugging; do not expose to client
        logger.error(f"Events list error: {e}", exc_info=True)
        return {"error": "Failed to fetch events"}, 500