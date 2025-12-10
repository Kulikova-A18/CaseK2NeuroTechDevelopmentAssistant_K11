# modules/users.py
"""
User management module that handles user authentication, retrieval, and creation
using a CSV-based storage backend. This module is designed to work with Telegram user IDs
and supports role-based access control (e.g., admin vs. member).
"""

import csv
import time
import os
from config import CSV_FILES

# Define the schema (column order) for the users CSV file.
# These fields must match the actual data written to and read from the file.
USER_FIELDS = [
    "user_id", "telegram_user_id", "telegram_username", "full_name",
    "registration_timestamp", "last_login", "is_active", "role"
]


def _ensure_file():
    """
    Ensure that the users CSV file exists; if not, create it with a header row.

    This is an internal utility function used by other functions in this module
    to guarantee the file is present before attempting read or write operations.

    The file path is obtained from the `CSV_FILES` configuration dictionary
    under the key `"users"`.

    :return: None
    """
    path = CSV_FILES["users"]
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=USER_FIELDS)
            w.writeheader()


def get_user_by_telegram_id(tid):
    """
    Retrieve a user record by their Telegram user ID.

    This function scans the users CSV file row by row and returns the first user
    whose `telegram_user_id` matches the given ID (as a string).

    :param tid: (int or str) The Telegram user ID to search for.
    :return: (dict or None) A dictionary representing the user row if found;
             otherwise, `None`.
    """
    _ensure_file()
    with open(CSV_FILES["users"], "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["telegram_user_id"] == str(tid):
                return row
    return None


def is_admin(user_record):
    """
    Check whether a given user record corresponds to an administrator.

    :param user_record: (dict or None) A user dictionary as returned by `get_user_by_telegram_id`
                        or similar functions. If `None`, the function returns `False`.
    :return: (bool) `True` if the user exists and has role `"admin"`; otherwise, `False`.
    """
    return user_record and user_record.get("role") == "admin"


def authenticate_user(telegram_user_id):
    """
    Authenticate a user by their Telegram user ID.

    This function verifies that:
      - A user with the given Telegram ID exists.
      - The user's `is_active` field is `"True"`.

    If authentication succeeds, the user's `last_login` timestamp is updated
    to the current time, and the updated record is persisted to the CSV file.

    Note: This function does **not** create new users. It only authenticates existing,
    active users.

    :param telegram_user_id: (int or str) The Telegram user ID to authenticate.
    :return: (dict or None) The user dictionary if authentication succeeds;
             `None` if the user does not exist or is inactive.
    """
    user = get_user_by_telegram_id(telegram_user_id)
    if not user:
        return None
    if user.get("is_active") != "True":
        return None

    # Update the last_login timestamp for the authenticated user
    users = list_all_users()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    for u in users:
        if u["telegram_user_id"] == str(telegram_user_id):
            u["last_login"] = now
            break

    # Rewrite the entire file with the updated timestamp
    with open(CSV_FILES["users"], "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=USER_FIELDS)
        w.writeheader()
        w.writerows(users)

    return user


def list_all_users():
    """
    Retrieve all user records from the CSV file.

    This function returns a list of dictionaries, where each dictionary represents
    one row in the users CSV file (excluding the header).

    :return: (list[dict]) A list of user records. If the file is empty or doesn't exist,
             returns an empty list.
    """
    _ensure_file()
    with open(CSV_FILES["users"], "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def create_user_explicit(data):
    """
    Manually create a new user record. Typically used by administrators.

    This function assigns a new unique `user_id` (incremented from the highest existing ID),
    sets registration and last login timestamps, and marks the user as active.
    Missing optional fields in `data` are filled with defaults.

    :param data: (dict) A dictionary containing at least:
                   - `"telegram_user_id"` (required, int or str)
                 Optional keys:
                   - `"telegram_username"` (str)
                   - `"full_name"` (str)
                   - `"role"` (str, default: `"member"`)

    :return: (int) The newly assigned `user_id`.

    :raises KeyError: If `data` does not contain `"telegram_user_id"`.
    :raises ValueError: If `"telegram_user_id"` is not convertible to a string.
    """
    users = list_all_users()
    # Generate a new user_id by finding the max existing ID, or start at 1
    user_id = max([int(u["user_id"]) for u in users], default=0) + 1
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    # Construct the new user record
    row = {
        "user_id": user_id,
        "telegram_user_id": data["telegram_user_id"],  # required
        "telegram_username": data.get("telegram_username", ""),
        "full_name": data.get("full_name", ""),
        "registration_timestamp": now,
        "last_login": now,
        "is_active": "True",
        "role": data.get("role", "member")  # default role is "member"
    }

    # Append the new record to the CSV file
    with open(CSV_FILES["users"], "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=USER_FIELDS)
        w.writerow(row)

    return user_id