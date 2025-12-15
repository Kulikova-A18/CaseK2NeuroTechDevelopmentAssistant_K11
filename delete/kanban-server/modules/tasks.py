# modules/tasks.py
from flask import jsonify, request

def make_tasks_handlers(storage, logger):
    """
    Creates handler functions for task-related HTTP endpoints.

    :param storage: Instance of InMemoryStorage for data operations.
    :param logger: Logger instance for audit and debugging.
    :return: Dictionary mapping action names to Flask view functions.
    """

    def list_tasks():
        """Returns a list of all tasks."""
        items = storage.get_all('tasks')
        logger.info("Listed all tasks")
        return jsonify(items)

    def create_task():
        """Creates a new task from JSON request body."""
        data = request.get_json() or {}
        item = storage.create('tasks', data)
        logger.info(f"Created task: {item}")
        return jsonify(item), 201

    def update_task(item_id: int):
        """
        Updates an existing task by ID.

        :param item_id: ID of the task to update.
        :return: Updated task or 404 error.
        """
        if not storage.get_by_id('tasks', item_id):
            logger.warning(f"Task {item_id} not found for update")
            return jsonify({'error': 'Not found'}), 404
        update_data = request.get_json() or {}
        storage.update('tasks', item_id, update_data)
        updated = storage.get_by_id('tasks', item_id)
        logger.info(f"Updated task {item_id}: {update_data}")
        return jsonify(updated)

    def delete_task(item_id: int):
        """
        Deletes a task by ID.

        :param item_id: ID of the task to delete.
        :return: 204 on success or 404 if not found.
        """
        if not storage.delete('tasks', item_id):
            logger.warning(f"Task {item_id} not found for deletion")
            return jsonify({'error': 'Not found'}), 404
        logger.info(f"Deleted task {item_id}")
        return '', 204

    return {
        'list': list_tasks,
        'create': create_task,
        'update': update_task,
        'delete': delete_task
    }