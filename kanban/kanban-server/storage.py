# storage.py

class InMemoryStorage:
    """
    A simple in-memory data store for demonstration purposes.
    Supports basic CRUD operations for predefined entity types.
    Not suitable for production without persistence.
    """

    def __init__(self):
        """
        Initializes storage with empty collections for 'tasks', 'docs', and 'events',
        and sets up ID counters.
        """
        self.data = {
            'tasks': {},
            'docs': {},
            'events': []
        }
        self.counters = {
            'tasks': 1,
            'docs': 1,
            'events': 1
        }

    def get_next_id(self, entity: str) -> int:
        """
        Generates and returns the next unique ID for a given entity.

        :param entity: Entity type (e.g., 'tasks', 'docs', 'events').
        :return: Next available integer ID.
        """
        current_id = self.counters[entity]
        self.counters[entity] += 1
        return current_id

    def get_all(self, entity: str) -> list:
        """
        Returns all items for the given entity.

        :param entity: Entity type.
        :return: List of all items (dicts).
        """
        if entity == 'events':
            return self.data[entity]
        else:
            return list(self.data[entity].values())

    def get_by_id(self, entity: str, item_id: int):
        """
        Retrieves an item by its ID.

        :param entity: Entity type.
        :param item_id: ID of the item to retrieve.
        :return: Item dict if found, otherwise None.
        """
        if entity == 'events':
            for item in self.data[entity]:
                if item.get('id') == item_id:
                    return item
            return None
        return self.data[entity].get(item_id)

    def create(self, entity: str, item: dict) -> dict:
        """
        Creates a new item in the specified entity collection.

        :param entity: Entity type.
        :param item: Dictionary with item data (ID will be assigned).
        :return: The created item with assigned 'id'.
        """
        item_id = self.get_next_id(entity)
        item['id'] = item_id
        if entity == 'events':
            self.data[entity].append(item)
        else:
            self.data[entity][item_id] = item
        return item

    def update(self, entity: str, item_id: int, update_data: dict) -> bool:
        """
        Updates an existing item with new data.

        :param entity: Entity type.
        :param item_id: ID of the item to update.
        :param update_data: Dictionary of fields to update.
        :return: True if item was found and updated, False otherwise.
        """
        item = self.get_by_id(entity, item_id)
        if item is None:
            return False
        item.update(update_data)
        return True

    def delete(self, entity: str, item_id: int) -> bool:
        """
        Deletes an item by ID.

        :param entity: Entity type.
        :param item_id: ID of the item to delete.
        :return: True if item was found and deleted, False otherwise.
        """
        if entity == 'events':
            initial_count = len(self.data[entity])
            self.data[entity] = [e for e in self.data[entity] if e.get('id') != item_id]
            return len(self.data[entity]) < initial_count
        if item_id in self.data[entity]:
            del self.data[entity][item_id]
            return True
        return False