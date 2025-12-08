# modules/events.py
from flask import jsonify, request

def make_events_handlers(storage, logger):
    """
    Creates handler functions for calendar event-related HTTP endpoints.

    :param storage: Instance of InMemoryStorage for data operations.
    :param logger: Logger instance for audit and debugging.
    :return: Dictionary mapping action names to Flask view functions.
    """

    def list_events():
        """Returns a list of all calendar events."""
        items = storage.get_all('events')
        logger.info("Listed all calendar events")
        return jsonify(items)

    def create_event():
        """Creates a new calendar event from JSON request body."""
        data = request.get_json() or {}
        item = storage.create('events', data)
        logger.info(f"Created calendar event: {item}")
        return jsonify(item), 201

    return {
        'list': list_events,
        'create': create_event
    }