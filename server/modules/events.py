"""
Event management module that provides basic CRUD-like operations for calendar-style events
stored in a CSV file. Each event has a title, start/end times, creator, and creation timestamp.
This module supports event creation and listing. Deletion and update operations can be added later if needed.
"""

import csv
import time
import os
from config import CSV_FILES

# Define the schema (column names) for the events CSV file.
# The order of fields must match how data is read and written.
EVENT_FIELDS = ["event_id", "title", "start", "end", "creator_user_id", "created_at"]


def _ensure_file():
    """
    Ensure the events CSV file exists; if not, create it with a header row.

    This internal utility function is called by other functions in the module
    to guarantee that the file is present before performing read or write operations.
    The file path is obtained from the application configuration dictionary `CSV_FILES`
    under the key `"events"`.

    :return: None
    """
    path = CSV_FILES["events"]
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=EVENT_FIELDS)
            w.writeheader()


def list_events():
    """
    Retrieve all events from the CSV file.

    This function reads the entire events file and returns a list of dictionaries,
    where each dictionary corresponds to one event row (excluding the header).

    :return: (list[dict]) A list of event records. Each dictionary uses the keys defined
             in `EVENT_FIELDS`. If the file is empty or does not exist (but is created),
             returns an empty list.
    """
    _ensure_file()
    with open(CSV_FILES["events"], "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def create_event(data):
    """
    Create a new event and append it to the CSV file.

    Assigns a new unique `event_id` by incrementing the highest existing ID.
    Sets the `created_at` timestamp to the current time.

    Required fields in `data`:
        - `"title"`: (str) The title or name of the event.
        - `"start"`: (str) The start time of the event (format is not enforced,
                     but ISO 8601 like "2025-12-10T15:00:00" is recommended).
        - `"creator_user_id"`: (str or int) ID of the user who created the event.

    Optional fields:
        - `"end"`: (str) The end time of the event. Defaults to an empty string if omitted.

    :param  (dict) A dictionary containing event attributes. Must include
                   required fields as specified above.
    :return: (int) The newly assigned `event_id`.
    :raises KeyError: If any required field (`title`, `start`, `creator_user_id`) is missing.
    """
    _ensure_file()
    events = list_events()
    # Generate a new event_id by finding the max existing ID, or start at 1
    event_id = max([int(e["event_id"]) for e in events], default=0) + 1
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    # Construct the new event record
    row = {
        "event_id": event_id,
        "title": data["title"],
        "start": data["start"],
        "end": data.get("end", ""),  # optional; default to empty string
        "creator_user_id": data["creator_user_id"],
        "created_at": now
    }

    # Append the new event to the CSV file
    with open(CSV_FILES["events"], "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=EVENT_FIELDS)
        w.writerow(row)

    return event_id