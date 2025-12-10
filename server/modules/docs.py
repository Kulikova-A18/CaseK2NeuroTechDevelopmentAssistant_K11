"""
Document management module that provides basic CRUD operations for storing and updating
text-based documents in a CSV file. Each document has a name, content, creator, and timestamps
for creation and last modification.
"""

import csv
import time
import os
import json
from config import CSV_FILES

# Define the schema (column names) for the documents CSV file.
# These fields must match the structure used when reading from and writing to the file.
DOC_FIELDS = ["doc_id", "name", "content", "creator_user_id", "created_at", "updated_at"]


def _ensure_file():
    """
    Ensure the documents CSV file exists; if not, create it with a header row.

    This internal utility function is automatically called by other public functions
    to guarantee the file is present before performing any read or write operation.
    The file path is obtained from the application configuration dictionary `CSV_FILES`
    under the key `"docs"`.

    :return: None
    """
    path = CSV_FILES["docs"]
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=DOC_FIELDS)
            w.writeheader()


def list_docs():
    """
    Retrieve all documents from the CSV file.

    This function reads the entire documents file and returns a list of dictionaries,
    where each dictionary represents one document row (excluding the header).

    :return: (list[dict]) A list of document records. Each dictionary uses keys from `DOC_FIELDS`.
             If the file is empty or newly created, returns an empty list.
    """
    _ensure_file()
    with open(CSV_FILES["docs"], "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def create_doc(data):
    """
    Create a new document and append it to the CSV file.

    Assigns a new unique `doc_id` by incrementing the highest existing ID.
    Sets both `created_at` and `updated_at` to the current timestamp.

    Required fields in `data`:
        - `"name"`: (str) The display name or title of the document.
        - `"creator_user_id"`: (str or int) ID of the user who created the document.

    Optional fields:
        - `"content"`: (str) The body or text content of the document. Defaults to an empty string.

    :param  (dict) A dictionary containing document attributes. Must include
                   the required fields listed above.
    :return: (int) The newly assigned `doc_id`.
    :raises KeyError: If required fields (`name`, `creator_user_id`) are missing in `data`.
    """
    _ensure_file()
    docs = list_docs()
    # Generate a new doc_id by finding the max existing ID, or start at 1
    doc_id = max([int(d["doc_id"]) for d in docs], default=0) + 1
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    # Construct the new document record
    row = {
        "doc_id": doc_id,
        "name": data["name"],
        "content": data.get("content", ""),  # optional; default to empty string
        "creator_user_id": data["creator_user_id"],
        "created_at": now,
        "updated_at": now
    }

    # Append the new document to the CSV file
    with open(CSV_FILES["docs"], "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DOC_FIELDS)
        w.writerow(row)

    return doc_id


def update_doc(doc_id, updates):
    """
    Update an existing document by its ID with the provided field changes.

    Only fields that are present in `DOC_FIELDS` are updated. The `updated_at` timestamp
    is automatically refreshed to the current time upon any successful update.

    :param doc_id: (int) The numeric identifier of the document to update.
    :param updates: (dict) A dictionary of field names and new values to apply.
                    Only keys that exist in `DOC_FIELDS` are considered.
                    Commonly updated fields include `"name"` and `"content"`.
    :return: (bool) `True` if a document with the given `doc_id` was found and updated;
             `False` if no matching document exists.
    """
    docs = list_docs()
    found = False
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    # Search for the document by ID
    for d in docs:
        if int(d["doc_id"]) == doc_id:
            # Apply updates only to valid fields
            for k, v in updates.items():
                if k in DOC_FIELDS:
                    d[k] = v
            # Always update the modification timestamp
            d["updated_at"] = now
            found = True
            break

    # If a document was updated, rewrite the entire file
    if found:
        with open(CSV_FILES["docs"], "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=DOC_FIELDS)
            w.writeheader()
            w.writerows(docs)

    return found