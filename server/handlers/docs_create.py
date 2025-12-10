# handlers/docs_create.py
"""
Handler module for the 'docs_create' route.
This handler allows authenticated users to create new documents.
It verifies that the requester is a registered user, injects the internal user ID
as the document creator, and delegates document creation to the data layer.
"""

from logger import get_logger
from modules.docs import create_doc

# Initialize a dedicated logger for this handler to record document creation events and errors.
logger = get_logger("docs_create")


def _create_doc_core(data):
    """
    Internal helper function that delegates document creation to the data module.

    This function wraps the `create_doc` function from `modules.docs` to provide
    a stable interface and allow future enhancements (e.g., validation, hooks, or auditing)
    without modifying the main request logic.

    :param  (dict) A dictionary containing document attributes. Must include:
                 - `"name"` (str): The display name or title of the document.
                 - `"creator_user_id"` (str or int): Internal ID of the user creating the document
                                                    (injected by the handler).
                 - Optional: `"content"` (str): The body text of the document (defaults to empty string).
    :return: (int) The newly assigned numeric `doc_id`.
    :raises KeyError: If required fields (`"name"`, `"creator_user_id"`) are missing in `data`.
    """
    return create_doc(data)


def handle_request(data):
    """
    Handle an HTTP request to create a new document.

    This function implements a secure workflow for document creation:
      1. Validates that the request includes a `telegram_user_id`.
      2. Authenticates the user by looking up their record.
      3. Injects the internal `user_id` (from the user record) as `creator_user_id`.
      4. Delegates creation to the core logic and returns the new document ID.

    The handler conforms to the standard interface expected by the application’s routing system:
    it accepts a single `data` dictionary and returns a tuple
    `(response_body: dict, http_status_code: int)`.

    :param  (dict) A dictionary containing:
                 - `"telegram_user_id"` (str or int): Telegram ID of the requesting user.
                 - `"name"` (str): Title of the new document (required).
                 - Optional: `"content"` (str): Full text content of the document.
    :return: (tuple) A tuple containing:
             - (dict): Either:
                         - `{"doc_id": int}` on success, or
                         - An error object with an `"error"` key on failure.
             - (int): HTTP status code:
                       - 201 Created (document successfully created)
                       - 401 Unauthorized (missing or unregistered `telegram_user_id`)
                       - 500 Internal Server Error (unexpected exception during creation,
                         e.g., file write error or missing required field)
    """
    try:
        # Step 1: Extract and validate the requester's Telegram ID
        tid = data.get("telegram_user_id")
        if not tid:
            return {"error": "Missing telegram_user_id"}, 401

        # Step 2: Authenticate the user and retrieve their internal record
        from modules.users import get_user_by_telegram_id
        user = get_user_by_telegram_id(tid)
        if not user:
            return {"error": "Unauthorized"}, 401

        # Step 3: Enrich data with internal creator ID (not the Telegram ID)
        # This ensures referential integrity with the users/docs data model
        data["creator_user_id"] = user["user_id"]

        # Step 4: Create the document
        doc_id = _create_doc_core(data)

        # Log successful creation for audit and monitoring
        logger.info(f"Doc {doc_id} created by {tid}")

        return {"doc_id": doc_id}, 201

    except Exception as e:
        # Log full exception details internally; return generic error to client
        logger.error(f"Doc create error: {e}", exc_info=True)
        return {"error": "Create failed"}, 500