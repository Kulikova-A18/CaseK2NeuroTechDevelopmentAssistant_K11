# handlers/docs_update.py
"""
Handler module for the 'docs_update' route.
This handler allows authenticated users to update existing documents by providing
a document ID and the fields to modify. It performs basic authentication and delegates
the actual update logic to the documents data module.
"""

from logger import get_logger
from modules.docs import update_doc

# Initialize a dedicated logger for this handler to record document update events and errors.
logger = get_logger("docs_update")


def _update_doc_core(doc_id, updates):
    """
    Internal helper function that delegates the document update operation to the data layer.

    This function wraps the `update_doc` function from `modules.docs` to encapsulate
    type conversion (e.g., string to integer for `doc_id`) and provide a stable interface
    for the main handler logic.

    :param doc_id: (str or int) The identifier of the document to update. Will be converted to `int`.
    :param updates: (dict) A dictionary of field names and new values to apply to the document.
                    Only keys present in `DOC_FIELDS` (from the docs module) will be updated.
                    Valid fields include: `"name"`, `"content"`.
    :return: (bool) `True` if a document with the given ID was found and updated;
             `False` if no matching document exists.
    :raises ValueError: If `doc_id` cannot be converted to an integer.
    """
    return update_doc(int(doc_id), updates)


def handle_request(data):
    """
    Handle an HTTP request to update an existing document.

    This function implements a basic security and validation workflow:
      1. Validates that the request includes both `telegram_user_id` and `id` (document ID).
      2. Authenticates the user by verifying their existence in the user registry.
      3. Extracts update fields (excluding authentication and routing keys).
      4. Delegates the update to the core logic and returns an appropriate response.

    The handler conforms to the standard interface expected by the application’s routing system:
    it accepts a single `data` dictionary (typically from a JSON request body or merged parameters)
    and returns a tuple `(response_body: dict, http_status_code: int)`.

    :param  (dict) A dictionary containing:
                 - `"telegram_user_id"` (str or int): ID of the user making the request.
                 - `"id"` (str or int): ID of the document to update.
                 - Optional: any other key-value pairs representing document fields to update,
                   such as `"name"` or `"content"`.
    :return: (tuple) A tuple containing:
             - (dict): Either a success object `{"status": "updated"}` or an error object
                       with an `"error"` key.
             - (int): HTTP status code:
                       - 200 OK (document successfully updated)
                       - 400 Bad Request (missing `telegram_user_id` or `id`)
                       - 401 Unauthorized (user not found in the system)
                       - 404 Not Found (document with the given ID does not exist)
                       - 500 Internal Server Error (unexpected exception during update)
    """
    try:
        # Step 1: Extract and validate required identifiers
        tid = data.get("telegram_user_id")
        doc_id = data.get("id")
        if not tid or not doc_id:
            return {"error": "Missing telegram_user_id or id"}, 400

        # Step 2: Authenticate the requesting user (existence check only)
        from modules.users import get_user_by_telegram_id
        if not get_user_by_telegram_id(tid):
            return {"error": "Unauthorized"}, 401

        # Step 3: Prepare update payload (exclude auth and routing fields)
        updates = {k: v for k, v in data.items() if k not in ("telegram_user_id", "id")}

        # Step 4: Perform the update
        success = _update_doc_core(doc_id, updates)
        if not success:
            return {"error": "Doc not found"}, 404

        # Optional: add audit logging here if needed (currently omitted per original code)
        return {"status": "updated"}, 200

    except Exception as e:
        # Log full exception details internally for debugging; do not expose to client
        logger.error(f"Doc update error: {e}", exc_info=True)
        return {"error": "Update failed"}, 500