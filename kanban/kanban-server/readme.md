# README.md

If you have problem (`app_gui.py`)

```commandline
sudo apt install python3-tk python3-dev
```
## requirements.txt

```txt
Flask==3.0.3
PyYAML==6.0.1
requests==2.31.0
```
These versions are compatible as of 2025 and support Python 3.8+.

## Quick Start

1. Clone or create the project directory
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the server:
   ```bash
   python app.py
   ```
   The server starts on `http://0.0.0.0:5000`.

4. Test an endpoint:
   ```bash
   curl -X POST http://localhost:5000/api/tasks \
        -H "Content-Type: application/json" \
        -d '{"title":"Write README"}'
   ```

---

## Configuration (`routes.yaml`)

All API routes are defined in `routes.yaml`.  
You can:

- Add new endpoints
- Change paths or methods
- Extend to new entities (e.g., `users`, `projects`)

**No code changes needed** for routing modifications!

See the [routes.yaml](routes.yaml) file for full documentation on allowed parameters.

---

## Logging

- Logs are written to:
  - Console (real-time)
  - File: `app.log` (persistent)
- Log format:
  ```
  2025-04-05 12:00:00,123 [INFO] ConfigLoader: Registered route: GET /api/tasks → tasks.list
  ```

---

## Supported Endpoints (Default)

| Method | Path                          | Action                     |
|--------|-------------------------------|----------------------------|
| GET    | `/api/tasks`                  | List all tasks             |
| POST   | `/api/tasks`                  | Create a new task          |
| PUT    | `/api/tasks/<int:id>`         | Update task by ID          |
| DELETE | `/api/tasks/<int:id>`         | Delete task by ID          |
| GET    | `/api/docs`                   | List all documents         |
| POST   | `/api/docs`                   | Create a new document      |
| PUT    | `/api/docs/<int:id>`          | Update document by ID      |
| GET    | `/api/calendar/events`        | List calendar events       |
| POST   | `/api/calendar/events`        | Create a new event         |
| POST   | `/api/telegram/auth`          | Authenticate via Telegram  |
| POST   | `/api/telegram/notify`        | Send Telegram notification |

All request bodies must be **JSON**.

---

## Extending the System

### Add a New Entity (e.g., `notes`)

1. Create `modules/notes.py` with `make_notes_handlers(storage, logger)`.
2. Register it in `config_loader.py`:
   ```python
   from modules.notes import make_notes_handlers
   # ...
   handlers['notes'] = make_notes_handlers(storage, logger)
   ```
3. Add routes to `routes.yaml`.

---

## Testing

Use `curl`, `httpie`, or tools like **Postman**:

```bash
# Create a task
curl -X POST http://localhost:5000/api/tasks -H "Content-Type: application/json" -d '{"title":"Test"}'

# List tasks
curl http://localhost:5000/api/tasks
```
