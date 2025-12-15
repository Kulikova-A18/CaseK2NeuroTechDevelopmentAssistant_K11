# modules/docs.py
from flask import jsonify, request

def make_docs_handlers(storage, logger):
    """
    Creates handler functions for document-related HTTP endpoints.

    :param storage: Instance of InMemoryStorage for data operations.
    :param logger: Logger instance for audit and debugging.
    :return: Dictionary mapping action names to Flask view functions.
    """

    def list_docs():
        """Returns a list of all documents."""
        items = storage.get_all('docs')
        logger.info("Listed all documents")
        return jsonify(items)

    def create_doc():
        """Creates a new document from JSON request body."""
        data = request.get_json() or {}
        item = storage.create('docs', data)
        logger.info(f"Created document: {item}")
        return jsonify(item), 201

    def update_doc(item_id: int):
        """
        Updates an existing document by ID.

        :param item_id: ID of the document to update.
        :return: Updated document or 404 error.
        """
        if not storage.get_by_id('docs', item_id):
            logger.warning(f"Document {item_id} not found for update")
            return jsonify({'error': 'Not found'}), 404
        update_data = request.get_json() or {}
        storage.update('docs', item_id, update_data)
        updated = storage.get_by_id('docs', item_id)
        logger.info(f"Updated document {item_id}: {update_data}")
        return jsonify(updated)

    def delete_doc(item_id: int):
        """
        Deletes a document by ID.

        :param item_id: ID of the document to delete.
        :return: 204 on success or 404 if not found.
        """
        if not storage.delete('docs', item_id):
            logger.warning(f"Document {item_id} not found for deletion")
            return jsonify({'error': 'Not found'}), 404
        logger.info(f"Deleted document {item_id}")
        return '', 204

    return {
        'list': list_docs,
        'create': create_doc,
        'update': update_doc,
        'delete': delete_doc
    }