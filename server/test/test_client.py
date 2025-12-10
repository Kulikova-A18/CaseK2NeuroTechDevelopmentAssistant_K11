# test_client.py
"""
Integration test client for the Flask-based backend API.

This script simulates a real user interacting with the system via Telegram authentication
and performs end-to-end operations on tasks, documents, and calendar events.
It verifies that all core CRUD routes are functional and return expected responses.

Note: This client assumes the server is running at `http://localhost:5000`.
"""

import requests
import json
import time

# Base URL of the running Flask application
BASE_URL = "http://localhost:5000"


def run_test_client():
    """
    Execute a sequence of API calls to test core functionality of the application.

    The test flow includes:
      1. Authenticating a Telegram user (triggers user creation if needed in real system;
         in this mock, assumes user exists or auth passes).
      2. Creating, reading, updating, and deleting tasks.
      3. Creating, reading, and updating documents.
      4. Creating and listing calendar events.
      5. Sending a mock Telegram notification.

    Each step logs the request sent and the response received for debugging.

    :return: None
    """

    # -------------------------------------------------------------------------
    # Step 1: Authenticate a Telegram user
    # -------------------------------------------------------------------------
    print("Step 1: Authenticate via Telegram")
    # What is sent:
    #   POST /api/telegram/auth
    #   JSON body: { "user_id": 111111111, "telegram_username": "...", "full_name": "..." }
    # Note: In your current handler, only `user_id` (or `telegram_user_id`) is used.
    #       Other fields are ignored unless the auth handler is modified to support registration.
    auth_data = {
        "user_id": 111111111,
        "telegram_username": "new_test_user",
        "full_name": "Test User"
    }
    resp = requests.post(f"{BASE_URL}/api/telegram/auth", json=auth_data)
    print("→ Sent:", json.dumps(auth_data, indent=2))
    print("→ Response status:", resp.status_code)
    print("→ Response body:", json.dumps(resp.json(), indent=2) if resp.content else "{}")

    if resp.status_code != 200:
        print("Authentication failed. Test aborted.")
        return

    user = resp.json()
    telegram_user_id = user.get("telegram_user_id") or auth_data["user_id"]

    print("\n" + "=" * 50 + "\n")

    # -------------------------------------------------------------------------
    # Step 2: Create a new task
    # -------------------------------------------------------------------------
    print("Step 2: Create a task")
    # What is sent:
    #   POST /api/tasks
    #   JSON body: includes telegram_user_id, title, description, priority, tags
    task_data = {
        "telegram_user_id": telegram_user_id,
        "title": "Test Task",
        "description": "Created by automated test",
        "priority": "high",
        "tags": ["test", "automation"]
    }
    resp = requests.post(f"{BASE_URL}/api/tasks", json=task_data)
    print("→ Sent:", json.dumps(task_data, indent=2))
    print("→ Response status:", resp.status_code)
    print("→ Response body:", json.dumps(resp.json(), indent=2) if resp.content else "{}")

    task_id = None
    if resp.status_code == 201:
        task_id = resp.json().get("task_id")
    else:
        print("Failed to create task.")

    print("\n" + "=" * 50 + "\n")

    # -------------------------------------------------------------------------
    # Step 3: List all tasks
    # -------------------------------------------------------------------------
    print("Step 3: List all tasks")
    # What is sent:
    #   GET /api/tasks
    #   JSON body: { "telegram_user_id": ... } (passed in body, though GET typically uses query params)
    list_task_data = {"telegram_user_id": telegram_user_id}
    resp = requests.get(f"{BASE_URL}/api/tasks", json=list_task_data)
    print("→ Sent:", json.dumps(list_task_data, indent=2))
    print("→ Response status:", resp.status_code)
    if resp.status_code == 200:
        tasks = resp.json()
        print(f"→ Found {len(tasks)} task(s)")
        for t in tasks:
            print(f"  - ID: {t.get('task_id')}, Title: {t.get('title')}, Status: {t.get('status')}")
    else:
        print("→ Failed to fetch tasks")

    print("\n" + "=" * 50 + "\n")

    # -------------------------------------------------------------------------
    # Step 4: Update the created task
    # -------------------------------------------------------------------------
    if task_id is not None:
        print("Step 4: Update the task")
        # What is sent:
        #   PUT /api/tasks/<id>
        #   JSON body: telegram_user_id, id, status, description
        update_data = {
            "telegram_user_id": telegram_user_id,
            "id": task_id,
            "status": "in_progress",
            "description": "Updated by test client"
        }
        resp = requests.put(f"{BASE_URL}/api/tasks/{task_id}", json=update_data)
        print("→ Sent:", json.dumps(update_data, indent=2))
        print("→ Response status:", resp.status_code)
        print("→ Response body:", json.dumps(resp.json(), indent=2) if resp.content else "{}")

        print("\n" + "=" * 50 + "\n")

    # -------------------------------------------------------------------------
    # Step 5: Create a document
    # -------------------------------------------------------------------------
    print("Step 5: Create a document")
    # What is sent:
    #   POST /api/docs
    #   JSON body: telegram_user_id, name, content
    doc_data = {
        "telegram_user_id": telegram_user_id,
        "name": "Test Report.pdf",
        "content": "Content of the test document"
    }
    resp = requests.post(f"{BASE_URL}/api/docs", json=doc_data)
    print("→ Sent:", json.dumps(doc_data, indent=2))
    print("→ Response status:", resp.status_code)
    print("→ Response body:", json.dumps(resp.json(), indent=2) if resp.content else "{}")

    doc_id = None
    if resp.status_code == 201:
        doc_id = resp.json().get("doc_id")
    else:
        print("Failed to create document.")

    print("\n" + "=" * 50 + "\n")

    # -------------------------------------------------------------------------
    # Step 6: List all documents
    # -------------------------------------------------------------------------
    print("Step 6: List all documents")
    # What is sent:
    #   GET /api/docs
    #   JSON body: { "telegram_user_id": ... }
    list_doc_data = {"telegram_user_id": telegram_user_id}
    resp = requests.get(f"{BASE_URL}/api/docs", json=list_doc_data)
    print("→ Sent:", json.dumps(list_doc_data, indent=2))
    print("→ Response status:", resp.status_code)
    if resp.status_code == 200:
        docs = resp.json()
        print(f"→ Found {len(docs)} document(s)")
        for d in docs:
            print(f"  - ID: {d.get('doc_id')}, Name: {d.get('name')}")
    else:
        print("→ Failed to fetch documents")

    print("\n" + "=" * 50 + "\n")

    # -------------------------------------------------------------------------
    # Step 7: Update the created document
    # -------------------------------------------------------------------------
    if doc_id is not None:
        print("Step 7: Update the document")
        # What is sent:
        #   PUT /api/docs/<id>
        #   JSON body: telegram_user_id, id, content
        update_doc_data = {
            "telegram_user_id": telegram_user_id,
            "id": doc_id,
            "content": "Updated content from test client"
        }
        resp = requests.put(f"{BASE_URL}/api/docs/{doc_id}", json=update_doc_data)
        print("→ Sent:", json.dumps(update_doc_data, indent=2))
        print("→ Response status:", resp.status_code)
        print("→ Response body:", json.dumps(resp.json(), indent=2) if resp.content else "{}")

        print("\n" + "=" * 50 + "\n")

    # -------------------------------------------------------------------------
    # Step 8: Create a calendar event
    # -------------------------------------------------------------------------
    print("Step 8: Create a calendar event")
    # What is sent:
    #   POST /api/calendar/events
    #   JSON body: telegram_user_id, title, start, end
    event_data = {
        "telegram_user_id": telegram_user_id,
        "title": "Test Meeting",
        "start": "2025-12-15T10:00:00",
        "end": "2025-12-15T11:00:00"
    }
    resp = requests.post(f"{BASE_URL}/api/calendar/events", json=event_data)
    print("→ Sent:", json.dumps(event_data, indent=2))
    print("→ Response status:", resp.status_code)
    print("→ Response body:", json.dumps(resp.json(), indent=2) if resp.content else "{}")

    event_id = None
    if resp.status_code == 201:
        event_id = resp.json().get("event_id")
    else:
        print("Failed to create event.")

    print("\n" + "=" * 50 + "\n")

    # -------------------------------------------------------------------------
    # Step 9: List all events
    # -------------------------------------------------------------------------
    print("Step 9: List all events")
    # What is sent:
    #   GET /api/calendar/events
    #   JSON body: { "telegram_user_id": ... }
    list_event_data = {"telegram_user_id": telegram_user_id}
    resp = requests.get(f"{BASE_URL}/api/calendar/events", json=list_event_data)
    print("→ Sent:", json.dumps(list_event_data, indent=2))
    print("→ Response status:", resp.status_code)
    if resp.status_code == 200:
        events = resp.json()
        print(f"→ Found {len(events)} event(s)")
        for e in events:
            print(f"  - ID: {e.get('event_id')}, Title: {e.get('title')}, Start: {e.get('start')}")
    else:
        print("→ Failed to fetch events")

    print("\n" + "=" * 50 + "\n")

    # -------------------------------------------------------------------------
    # Step 10: Delete the task (if created)
    # -------------------------------------------------------------------------
    if task_id is not None:
        print("Step 10: Delete the task")
        # What is sent:
        #   DELETE /api/tasks/<id>
        #   JSON body: { "telegram_user_id": ... }
        delete_task_data = {"telegram_user_id": telegram_user_id}
        resp = requests.delete(f"{BASE_URL}/api/tasks/{task_id}", json=delete_task_data)
        print("→ Sent:", json.dumps(delete_task_data, indent=2))
        print("→ Response status:", resp.status_code)
        print("→ Response body:", json.dumps(resp.json(), indent=2) if resp.content else "{}")

        print("\n" + "=" * 50 + "\n")

    # -------------------------------------------------------------------------
    # Step 11: Send a mock Telegram notification
    # -------------------------------------------------------------------------
    print("Step 11: Send a Telegram notification (mocked)")
    # What is sent:
    #   POST /api/telegram/notify
    #   JSON body: { "chat_id": ..., "message": ... }
    notify_data = {
        "chat_id": 123456789,
        "message": "Test notification from server"
    }
    resp = requests.post(f"{BASE_URL}/api/telegram/notify", json=notify_data)
    print("→ Sent:", json.dumps(notify_data, indent=2))
    print("→ Response status:", resp.status_code)
    print("→ Response body:", json.dumps(resp.json(), indent=2) if resp.content else "{}")

    print("\nIntegration test completed. Check data CSV files and logs/server.log for details.")


if __name__ == "__main__":
    run_test_client()