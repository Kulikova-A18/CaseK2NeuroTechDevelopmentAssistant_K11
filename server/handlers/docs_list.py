# handlers/docs_list.py
"""
Handler module for the 'docs_list' route.
This handler retrieves a list of all documents stored in the system.
It enforces basic authentication by verifying that the requester is a registered user
via their Telegram user ID. No access restrictions based on ownership or role are applied—
any authenticated user can view all documents.
"""

from logger import get_logger
from modules.docs import list_docs

# Initialize a dedicated logger for this handler to record operational events and errors.
logger = get_logger("docs_list")


def _list_docs_core():
    """
    Internal helper function that retrieves all documents from persistent storage.

    This function wraps the `list_docs` function from the `modules.docs` module
    to provide a stable abstraction layer. This design allows future enhancements
    (e.g., filtering, pagination, or performance optimizations) without modifying
    the main request-handling logic.

    :return: (list[dict]) A list of document records. Each dictionary contains all fields
             defined in `DOC_FIELDS` from the docs module:
             - `doc_id` (str)
             - `name` (str)
             - `content` (str)
             - `creator_user_id` (str)
             - `created_at` (str, ISO-like timestamp)
             - `updated_at` (str, ISO-like timestamp)
    """
    return list_docs()


def handle_request(data):
    """
    Handle an HTTP request to list all documents.

    This function implements a minimal authentication workflow:
      1. Validates that the request includes a `telegram_user_id`.
      2. Verifies that the user exists in the system.
      3. Retrieves and returns the full list of documents.

    The handler conforms to the standard interface expected by the application’s routing system:
    it accepts a single `data` dictionary (typically derived from request JSON or merged parameters)
    and returns a tuple `(response_body: list or dict, http_status_code: int)`.

    :param  (dict) A dictionary containing request context. Must include:
                 - `"telegram_user_id"` (str or int): The Telegram ID of the requesting user.
    :return: (tuple) A tuple containing:
             - (list or dict): Either:
                                 - A list of document dictionaries on success, or
                                 - An error object with an `"error"` key on failure.
             - (int): HTTP status code:
                       - 200 OK (documents successfully retrieved)
                       - 401 Unauthorized (missing or unregistered `telegram_user_id`)
                       - 500 Internal Server Error (unexpected exception during data retrieval)
    """
    try:
        # Step 1: Extract and validate the requester's Telegram ID
        tid = data.get("telegram_user_id")
        if not tid:
            return {"error": "Missing telegram_user_id"}, 401

        # Step 2: Authenticate: ensure the user exists in the user registry
        from modules.users import get_user_by_telegram_id
        if not get_user_by_telegram_id(tid):
            return {"error": "Unauthorized"}, 401

        # Step 3: Fetch all documents
        docs = _list_docs_core()

        # Return the full list of documents (no filtering or sanitization applied)
        return docs, 200

    except Exception as e:
        # Log full exception details internally for debugging; do not expose to client
        logger.error(f"Docs list error: {e}", exc_info=True)
        return {"error": "Failed to fetch docs"}, 500