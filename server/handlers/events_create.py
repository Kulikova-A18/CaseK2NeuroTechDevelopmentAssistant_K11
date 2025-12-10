# handlers/events_create.py
"""
Handler module for the 'events_create' route.
This handler allows authenticated users to create new calendar events.
It verifies that the requester is a registered user, ensures required event fields are present,
injects the internal user ID as the event creator, and delegates event creation to the data layer.
"""

from logger import get_logger
from modules.events import create_event

# Initialize a dedicated logger for this handler to record event creation events and errors.
logger = get_logger("events_create")


def _create_event_core(data):
    """
    Internal helper function that delegates event creation to the data module.

    This function wraps the `create_event` function from `modules.events` to provide
    a stable interface and allow future enhancements (e.g., validation, hooks, or auditing)
    without modifying the main request logic.

    :param data: (dict) A dictionary containing event attributes. Must include:
                 - `"title"` (str): The event title.
                 - `"start"` (str): The start time of the event (format not enforced,
                                    but ISO 8601 like "2025-12-10T15:00:00" is recommended).
                 - `"creator_user_id"` (str): Internal ID of the user creating the event
                                              (injected by the handler).
                 - Optional: `"end"` (str): End time of the event.
    :return: (int) The newly assigned numeric `event_id`.
    :raises KeyError: If required fields (`"title"`, `"start"`, `"creator_user_id"`) are missing.
    """
    return create_event(data)


def handle_request(data):
    """
    Handle an HTTP request to create a new calendar event.

    This function implements a secure workflow for event creation:
      1. Validates that the request includes a `telegram_user_id`.
      2. Authenticates the user by looking up their record.
      3. Ensures required event fields (`title`, `start`) are provided.
      4. Injects the internal `user_id` (from the user record) as `creator_user_id`.
      5. Delegates creation to the core logic and returns the new event ID.

    The handler conforms to the standard interface expected by the application’s routing system:
    it accepts a single `data` dictionary and returns a tuple
    `(response_body: dict, http_status_code: int)`.

    :param data: (dict) A dictionary containing:
                 - `"telegram_user_id"` (str or int): Telegram ID of the requesting user.
                 - `"title"` (str): Title of the new event (required).
                 - `"start"` (str): Start time of the event (required).
                 - Optional: `"end"` (str): End time of the event.
    :return: (tuple) A tuple containing:
             - (dict): Either:
                         - `{"event_id": int}` on success, or
                         - An error object with an `"error"` key on failure.
             - (int): HTTP status code:
                       - 201 Created (event successfully created)
                       - 400 Bad Request (missing required field)
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

        # Step 3: Validate required event fields
        required = ["title", "start"]
        for field in required:
            if field not in data:
                return {"error": f"Missing required field: {field}"}, 400

        # Step 4: Enrich data with internal creator ID (not the Telegram ID)
        # This ensures consistency with the users/events data model
        data["creator_user_id"] = user["user_id"]

        # Step 5: Create the event
        event_id = _create_event_core(data)

        # Log successful creation for audit and monitoring
        logger.info(f"Event {event_id} created by user {telegram_user_id}")

        return {"event_id": event_id}, 201

    except Exception as e:
        # Log full exception details internally; return generic error to client
        logger.error(f"Event create error: {e}", exc_info=True)
        return {"error": "Failed to create event"}, 500