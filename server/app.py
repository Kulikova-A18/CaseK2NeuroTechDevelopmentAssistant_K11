import yaml
import importlib
from flask import Flask, request, jsonify
from logger import get_logger

# Initialize the main Flask application instance.
app = Flask(__name__)

# Set up a dedicated logger for this module using the centralized logger factory.
logger = get_logger("app")

# Load route definitions from an external YAML configuration file.
# The file is expected to contain a top-level key "routes" holding a list of route specifications.
with open("routes.yaml", "r", encoding="utf-8") as f:
    routes = yaml.safe_load(f)["routes"]

# Mapping from logical route names to Python module paths.
# Each route name follows the convention: {entity}_{action}
# This decouples route configuration from handler implementation and enables dynamic loading.
HANDLER_PATHS = {
    # Telegram-related handlers
    "telegram_auth": "handlers.telegram_auth",
    "telegram_notify": "handlers.telegram_notify",

    # Task management handlers
    "tasks_list": "handlers.tasks_list",
    "tasks_create": "handlers.tasks_create",
    "tasks_update": "handlers.tasks_update",
    "tasks_delete": "handlers.tasks_delete",

    # Document management handlers
    "docs_list": "handlers.docs_list",
    "docs_create": "handlers.docs_create",
    "docs_update": "handlers.docs_update",

    # Event management handlers
    "events_list": "handlers.events_list",
    "events_create": "handlers.events_create",

    # User management handlers (typically restricted to admin roles)
    "users_list": "handlers.users_list",
    "users_create": "handlers.users_create",
}


def get_handler_func(route_name):
    """
    Dynamically import and return the `handle_request` function from the appropriate handler module.

    This function uses the predefined `HANDLER_PATHS` mapping to locate the correct Python module
    based on the logical route name (e.g., "tasks_create"). It then imports the module and returns
    its `handle_request` function, which must conform to a standard interface.

    :param route_name: (str) Logical name of the route, formatted as "{entity}_{action}".
                       Must be a key in the `HANDLER_PATHS` dictionary.
    :return: (callable) The `handle_request` function from the corresponding handler module.
    :raises ValueError: If `route_name` is not found in `HANDLER_PATHS`.
    :raises ImportError: If the module specified in `HANDLER_PATHS` cannot be imported.
    :raises AttributeError: If the imported module does not define a `handle_request` function.
    """
    if route_name not in HANDLER_PATHS:
        raise ValueError(f"No handler defined for route: {route_name}")
    module = importlib.import_module(HANDLER_PATHS[route_name])
    return module.handle_request


# Dynamically register all routes defined in the `routes` list.
# Each route entry must specify: path, HTTP method, entity, and action.
for r in routes:
    path = r["path"]
    method = r["method"]
    entity = r["entity"]
    action = r["action"]
    route_name = f"{entity}_{action}"

    def make_view(handler_func):
        """
        Factory function that creates a Flask view function wrapping a handler.

        The returned view function:
        - Extracts JSON data from the incoming request (if any).
        - Merges URL path parameters (e.g., <int:id>) into the data dictionary.
        - Invokes the handler function with the combined data.
        - Returns a JSON response with an appropriate HTTP status code.
        - Catches and logs unhandled exceptions, returning a 500 error to the client.

        :param handler_func: (callable) A handler function that accepts a single dict argument
                             and returns a tuple `(response_data: dict, status_code: int)`.
        :return: (callable) A Flask-compatible view function.
        """
        def view(**kwargs):
            # Extract JSON payload; use empty dict if missing or invalid
            data = request.get_json(silent=True) or {}
            # Merge path parameters (e.g., task_id from /tasks/<int:task_id>)
            data.update(kwargs)

            try:
                # Call the business logic handler
                result, status_code = handler_func(data)
                return jsonify(result), status_code
            except Exception as e:
                # Log full traceback for debugging
                logger.error(f"Unhandled error in {handler_func.__module__}: {e}", exc_info=True)
                return jsonify({"error": "Internal server error"}), 500
        return view

    try:
        # Retrieve the actual handler function based on the route name
        handler = get_handler_func(route_name)
        # Register the route with Flask
        app.add_url_rule(
            path,
            endpoint=route_name,              # Unique identifier for the route
            view_func=make_view(handler),     # Wrapped view function
            methods=[method]                  # Allowed HTTP method(s)
        )
        logger.info(f"Registered route: {method} {path} → {route_name}")
    except ValueError as e:
        logger.error(f"Failed to register route {route_name}: {e}")
    # Note: ImportError or AttributeError from `get_handler_func` will propagate and crash
    # the application during startup—this is intentional to fail fast on misconfiguration.

# Entry point for running the Flask development server.
if __name__ == "__main__":
    # Bind to all interfaces (0.0.0.0) on port 5000 with debug mode enabled.
    # Warning: debug=True is unsafe for production use.
    app.run(host="0.0.0.0", port=5000, debug=True)