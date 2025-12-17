"""
PostgreSQL data manager for thread-safe reading and writing.
Manages database tables with schema validation, automatic ID generation,
and connection pooling.
"""

import os
import json
import threading
import logging
import contextlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict, field
import uuid

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor, Json
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ConnectionConfig:
    """Configuration for PostgreSQL connection"""
    host: str = field(default_factory=lambda: os.getenv('PG_HOST', 'localhost'))
    port: str = field(default_factory=lambda: os.getenv('PG_PORT', '5432'))
    database: str = field(default_factory=lambda: os.getenv('PG_DATABASE', 'postgres'))
    user: str = field(default_factory=lambda: os.getenv('PG_USER', 'postgres'))
    password: str = field(default_factory=lambda: os.getenv('PG_PASSWORD', ''))
    min_connections: int = 1
    max_connections: int = 10
    schema: str = field(default_factory=lambda: os.getenv('PG_SCHEMA', 'public'))


class PostgresDataManager:
    """
    Manager for working with PostgreSQL database.
    Provides thread-safe data reading and writing with connection pooling.

    param table_name: Name of the table to manage
    param schema: Data schema with types and validation
    param config: Connection configuration
    """

    def __init__(self, table_name: str, schema: Dict[str, Any],
                 config: Optional[ConnectionConfig] = None):
        self.table_name = table_name
        self.schema = schema
        self.config = config or ConnectionConfig()

        # Initialize connection pool
        self._connection_pool = None
        self._initialize_pool()

        # Ensure table exists with correct schema
        self._ensure_table_exists()

        # Thread lock for operations that need synchronization
        self._lock = threading.Lock()

    def _initialize_pool(self):
        """Initialize PostgreSQL connection pool."""
        try:
            self._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self.config.min_connections,
                maxconn=self.config.max_connections,
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password
            )
            logger.info(f"PostgreSQL connection pool initialized for table '{self.table_name}'")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connection pool: {e}")
            raise

    @contextlib.contextmanager
    def _get_connection(self):
        """Context manager for getting database connection from pool."""
        conn = None
        try:
            conn = self._connection_pool.getconn()
            yield conn
        except Exception as e:
            logger.error(f"Error getting connection: {e}")
            raise
        finally:
            if conn:
                self._connection_pool.putconn(conn)

    @contextlib.contextmanager
    def _get_cursor(self, connection=None):
        """Context manager for getting database cursor.

        param connection: Optional existing connection to use
        """
        if connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                yield cursor
        else:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    yield cursor

    def _ensure_table_exists(self):
        """Create table with specified schema if it doesn't exist."""
        try:
            with self._get_cursor() as cursor:
                # Check if table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = %s 
                        AND table_name = %s
                    );
                """, (self.config.schema, self.table_name))

                table_exists = cursor.fetchone()['exists']

                if not table_exists:
                    # Create table with schema
                    columns = []
                    for column_name, column_info in self.schema.items():
                        pg_type = self._python_type_to_pg(column_info.get('type', 'text'))
                        nullable = '' if column_info.get('required', False) else 'NULL'

                        # Handle special columns
                        if column_name == 'id':
                            if pg_type == 'serial':
                                columns.append(f'id SERIAL PRIMARY KEY')
                            else:
                                columns.append(f'{column_name} {pg_type} PRIMARY KEY {nullable}')
                        else:
                            columns.append(f'{column_name} {pg_type} {nullable}')

                    create_table_sql = f"""
                        CREATE TABLE {self.config.schema}.{self.table_name} (
                            {', '.join(columns)}
                        );
                    """

                    cursor.execute(create_table_sql)
                    logger.info(f"Table '{self.table_name}' created successfully")

                    # Create indexes for common search fields
                    for column_name, column_info in self.schema.items():
                        if column_info.get('indexed', False):
                            self._create_index(column_name)

                    cursor.connection.commit()
                    logger.info(f"Indexes created for table '{self.table_name}'")
                else:
                    logger.debug(f"Table '{self.table_name}' already exists")

        except Exception as e:
            logger.error(f"Error ensuring table exists: {e}")
            raise

    def _python_type_to_pg(self, python_type: Union[str, type]) -> str:
        """Convert Python type to PostgreSQL type.

        param python_type: Python type name or type object
        return: PostgreSQL type string
        """
        type_mapping = {
            'int': 'INTEGER',
            'integer': 'INTEGER',
            'str': 'TEXT',
            'text': 'TEXT',
            'string': 'TEXT',
            'bool': 'BOOLEAN',
            'boolean': 'BOOLEAN',
            'float': 'REAL',
            'double': 'DOUBLE PRECISION',
            'datetime': 'TIMESTAMP',
            'date': 'DATE',
            'time': 'TIME',
            'json': 'JSONB',
            'jsonb': 'JSONB',
            'uuid': 'UUID',
            'serial': 'SERIAL',
        }

        if isinstance(python_type, type):
            python_type = python_type.__name__

        return type_mapping.get(python_type.lower(), 'TEXT')

    def _create_index(self, column_name: str):
        """Create index on specified column.

        param column_name: Name of column to index
        """
        try:
            with self._get_cursor() as cursor:
                index_name = f"idx_{self.table_name}_{column_name}"
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON {self.config.schema}.{self.table_name} ({column_name});
                """)
                cursor.connection.commit()
                logger.debug(f"Index '{index_name}' created")
        except Exception as e:
            logger.warning(f"Failed to create index on '{column_name}': {e}")

    def read_all(self) -> List[Dict[str, Any]]:
        """
        Read all records from table.

        return: List of all records
        """
        try:
            with self._get_cursor() as cursor:
                cursor.execute(f"""
                    SELECT * FROM {self.config.schema}.{self.table_name}
                    ORDER BY id;
                """)
                results = cursor.fetchall()

                # Convert RealDictRow to regular dict
                return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error reading all records: {e}")
            return []

    def find(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Find records by criteria.

        param **kwargs: Search criteria (field=value)
        return: Found records
        """
        try:
            with self._get_cursor() as cursor:
                conditions = []
                values = []

                for key, value in kwargs.items():
                    if '__' in key:  # Support for operators like field__gt, field__like
                        field, operator = key.split('__')
                        if operator == 'gt':
                            conditions.append(f"{field} > %s")
                        elif operator == 'lt':
                            conditions.append(f"{field} < %s")
                        elif operator == 'gte':
                            conditions.append(f"{field} >= %s")
                        elif operator == 'lte':
                            conditions.append(f"{field} <= %s")
                        elif operator == 'like':
                            conditions.append(f"{field} LIKE %s")
                        elif operator == 'ilike':
                            conditions.append(f"{field} ILIKE %s")
                        elif operator == 'in':
                            if isinstance(value, (list, tuple)):
                                placeholders = ', '.join(['%s'] * len(value))
                                conditions.append(f"{field} IN ({placeholders})")
                                values.extend(value)
                                continue
                        else:
                            conditions.append(f"{field} = %s")
                    else:
                        conditions.append(f"{key} = %s")

                    values.append(value)

                where_clause = " AND ".join(conditions) if conditions else "1=1"

                cursor.execute(f"""
                    SELECT * FROM {self.config.schema}.{self.table_name}
                    WHERE {where_clause}
                    ORDER BY id;
                """, tuple(values))

                results = cursor.fetchall()
                return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error finding records: {e}")
            return []

    def find_one(self, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Find one record by criteria.

        param **kwargs: Search criteria
        return: Found record or None
        """
        results = self.find(**kwargs)
        return results[0] if results else None

    def insert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert new record into table.

        param data: Data to insert
        return: Inserted record with ID
        raises ValueError: If required fields are missing
        """
        def _insert_operation():
            # Validate data against schema
            validated_data = {}

            for field, field_info in self.schema.items():
                if field_info.get('required', False) and field not in data:
                    # For timestamp fields add current time
                    if field in ['registered_at', 'created_at', 'updated_at']:
                        validated_data[field] = datetime.now()
                    elif 'default' in field_info:
                        validated_data[field] = field_info['default']
                    else:
                        raise ValueError(f"Required field '{field}' is missing")
                elif field in data:
                    validated_data[field] = data[field]
                elif 'default' in field_info:
                    validated_data[field] = field_info['default']
                elif field_info.get('type') == 'json':
                    validated_data[field] = {}
                else:
                    validated_data[field] = None

            # Handle UUID generation
            if 'id' in self.schema and self.schema['id'].get('type') == 'uuid':
                if 'id' not in validated_data or not validated_data['id']:
                    validated_data['id'] = str(uuid.uuid4())

            # Add timestamps if needed
            current_time = datetime.now()
            timestamp_fields = ['created_at', 'updated_at', 'registered_at', 'last_login']
            for field in timestamp_fields:
                if field in self.schema and field not in validated_data:
                    validated_data[field] = current_time

            # Prepare SQL for insertion
            columns = []
            placeholders = []
            values = []

            for column, value in validated_data.items():
                if value is not None:
                    columns.append(column)
                    placeholders.append('%s')

                    # Handle JSON data
                    if isinstance(value, (dict, list)):
                        values.append(Json(value))
                    else:
                        values.append(value)

            columns_str = ', '.join(columns)
            placeholders_str = ', '.join(placeholders)

            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(f"""
                        INSERT INTO {self.config.schema}.{self.table_name} ({columns_str})
                        VALUES ({placeholders_str})
                        RETURNING *;
                    """, tuple(values))

                    result = cursor.fetchone()
                    conn.commit()

                    if result:
                        return dict(result)
                    else:
                        return validated_data

        # Use lock for thread-safe insertion
        with self._lock:
            return _insert_operation()

    def update(self, filter_kwargs: Dict[str, Any], update_data: Dict[str, Any]) -> bool:
        """
        Update records by filter.

        param filter_kwargs: Criteria for finding records
        param update_data: Data to update
        return: True if update was successful
        """
        def _update_operation(filter_kwargs, update_data):
            # Prepare WHERE clause
            where_conditions = []
            where_values = []

            for key, value in filter_kwargs.items():
                where_conditions.append(f"{key} = %s")
                where_values.append(value)

            # Prepare SET clause
            set_clauses = []
            set_values = []

            for key, value in update_data.items():
                if key in self.schema:
                    set_clauses.append(f"{key} = %s")

                    # Handle JSON data
                    if isinstance(value, (dict, list)):
                        set_values.append(Json(value))
                    else:
                        set_values.append(value)

            # Update updated_at if field exists
            if 'updated_at' in self.schema:
                set_clauses.append("updated_at = %s")
                set_values.append(datetime.now())

            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            set_clause = ", ".join(set_clauses)

            all_values = set_values + where_values

            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        UPDATE {self.config.schema}.{self.table_name}
                        SET {set_clause}
                        WHERE {where_clause};
                    """, tuple(all_values))

                    rows_updated = cursor.rowcount
                    conn.commit()

                    return rows_updated > 0

        # Use lock for thread-safe update
        with self._lock:
            return _update_operation(filter_kwargs, update_data)

    def delete(self, **kwargs) -> bool:
        """
        Delete records by criteria.

        param **kwargs: Deletion criteria
        return: True if deletion was successful
        """
        def _delete_operation(**kwargs):
            conditions = []
            values = []

            for key, value in kwargs.items():
                conditions.append(f"{key} = %s")
                values.append(value)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        DELETE FROM {self.config.schema}.{self.table_name}
                        WHERE {where_clause};
                    """, tuple(values))

                    rows_deleted = cursor.rowcount
                    conn.commit()

                    return rows_deleted > 0

        # Use lock for thread-safe deletion
        with self._lock:
            return _delete_operation(**kwargs)

    def count(self, **kwargs) -> int:
        """
        Count records matching criteria.

        param **kwargs: Optional filter criteria
        return: Number of matching records
        """
        try:
            with self._get_cursor() as cursor:
                if kwargs:
                    conditions = []
                    values = []

                    for key, value in kwargs.items():
                        conditions.append(f"{key} = %s")
                        values.append(value)

                    where_clause = " WHERE " + " AND ".join(conditions)
                    cursor.execute(f"""
                        SELECT COUNT(*) as count 
                        FROM {self.config.schema}.{self.table_name}
                        {where_clause};
                    """, tuple(values))
                else:
                    cursor.execute(f"""
                        SELECT COUNT(*) as count 
                        FROM {self.config.schema}.{self.table_name};
                    """)

                result = cursor.fetchone()
                return result['count'] if result else 0

        except Exception as e:
            logger.error(f"Error counting records: {e}")
            return 0

    def execute_raw_sql(self, sql: str, params: Tuple = None) -> List[Dict[str, Any]]:
        """
        Execute raw SQL query.

        param sql: SQL query string
        param params: Query parameters
        return: Query results
        """
        try:
            with self._get_cursor() as cursor:
                cursor.execute(sql, params or ())

                if sql.strip().upper().startswith(('SELECT', 'WITH')):
                    results = cursor.fetchall()
                    return [dict(row) for row in results]
                else:
                    cursor.connection.commit()
                    return []

        except Exception as e:
            logger.error(f"Error executing raw SQL: {e}")
            raise

    def batch_insert(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Insert multiple records in batch.

        param data_list: List of data dictionaries
        return: List of inserted records
        """
        inserted_records = []

        with self._lock:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    for data in data_list:
                        # Validate and prepare data (similar to single insert)
                        validated_data = {}

                        for field, field_info in self.schema.items():
                            if field_info.get('required', False) and field not in data:
                                if field in ['registered_at', 'created_at', 'updated_at']:
                                    validated_data[field] = datetime.now()
                                elif 'default' in field_info:
                                    validated_data[field] = field_info['default']
                                else:
                                    raise ValueError(f"Required field '{field}' is missing")
                            elif field in data:
                                validated_data[field] = data[field]
                            elif 'default' in field_info:
                                validated_data[field] = field_info['default']
                            else:
                                validated_data[field] = None

                        # Handle UUID generation
                        if 'id' in self.schema and self.schema['id'].get('type') == 'uuid':
                            if 'id' not in validated_data or not validated_data['id']:
                                validated_data['id'] = str(uuid.uuid4())

                        # Prepare columns and values
                        columns = []
                        placeholders = []
                        values = []

                        for column, value in validated_data.items():
                            if value is not None:
                                columns.append(column)
                                placeholders.append('%s')

                                if isinstance(value, (dict, list)):
                                    values.append(Json(value))
                                else:
                                    values.append(value)

                        columns_str = ', '.join(columns)
                        placeholders_str = ', '.join(placeholders)

                        cursor.execute(f"""
                            INSERT INTO {self.config.schema}.{self.table_name} ({columns_str})
                            VALUES ({placeholders_str})
                            RETURNING *;
                        """, tuple(values))

                        result = cursor.fetchone()
                        if result:
                            inserted_records.append(dict(result))

                    conn.commit()

        return inserted_records

    def get_table_info(self) -> Dict[str, Any]:
        """
        Get information about the table.

        return: Dictionary with table information
        """
        try:
            with self._get_cursor() as cursor:
                # Get column information
                cursor.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_schema = %s 
                    AND table_name = %s
                    ORDER BY ordinal_position;
                """, (self.config.schema, self.table_name))

                columns = cursor.fetchall()

                # Get index information
                cursor.execute("""
                    SELECT 
                        indexname,
                        indexdef
                    FROM pg_indexes
                    WHERE schemaname = %s 
                    AND tablename = %s;
                """, (self.config.schema, self.table_name))

                indexes = cursor.fetchall()

                # Get row count
                count = self.count()

                return {
                    'table_name': self.table_name,
                    'schema': self.config.schema,
                    'row_count': count,
                    'columns': [dict(col) for col in columns],
                    'indexes': [dict(idx) for idx in indexes]
                }

        except Exception as e:
            logger.error(f"Error getting table info: {e}")
            return {}

    def close(self):
        """Close the connection pool."""
        if self._connection_pool:
            self._connection_pool.closeall()
            logger.info(f"PostgreSQL connection pool closed for table '{self.table_name}'")

    def __enter__(self):
        """Support context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close pool when exiting context."""
        self.close()


# Example usage function
def run_postgres_example():
    """
    Example usage of PostgresDataManager.

    Requires environment variables or .env file configuration:
    PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD
    """
    # Define schema for users table
    user_schema = {
        'id': {'type': 'serial', 'required': True, 'indexed': True},
        'username': {'type': 'text', 'required': True, 'indexed': True},
        'email': {'type': 'text', 'required': True, 'indexed': True},
        'full_name': {'type': 'text', 'required': False},
        'age': {'type': 'integer', 'required': False},
        'is_active': {'type': 'boolean', 'default': True},
        'preferences': {'type': 'json', 'default': {}},
        'created_at': {'type': 'datetime', 'required': True},
        'updated_at': {'type': 'datetime', 'required': True},
        'last_login': {'type': 'datetime', 'required': False}
    }

    # Create manager
    db_manager = PostgresDataManager(
        table_name='users',
        schema=user_schema,
        config=ConnectionConfig(
            host='localhost',
            port='5432',
            database='myapp',
            user='myuser',
            password='mypassword',
            schema='public'
        )
    )

    try:
        # 1. Insert data
        print("1. Inserting users...")
        user1 = db_manager.insert({
            'username': 'john_doe',
            'email': 'john@example.com',
            'full_name': 'John Doe',
            'age': 30,
            'preferences': {'theme': 'dark', 'notifications': True}
        })

        user2 = db_manager.insert({
            'username': 'jane_smith',
            'email': 'jane@example.com',
            'full_name': 'Jane Smith',
            'age': 25,
            'is_active': False
        })

        print(f"Inserted user 1: {user1['id']} - {user1['username']}")
        print(f"Inserted user 2: {user2['id']} - {user2['username']}")

        # 2. Read all data
        print("\n2. All users:")
        all_users = db_manager.read_all()
        for user in all_users:
            print(f"  {user['id']}: {user['username']} ({user['email']})")

        # 3. Search by criteria
        print("\n3. Finding active users:")
        active_users = db_manager.find(is_active=True)
        for user in active_users:
            print(f"  {user['username']} is active")

        # 4. Update data
        print("\n4. Updating user...")
        updated = db_manager.update(
            filter_kwargs={'username': 'john_doe'},
            update_data={'age': 31, 'preferences': {'theme': 'light'}}
        )
        print(f"Update successful: {updated}")

        # 5. Get single user
        print("\n5. Getting single user:")
        user = db_manager.find_one(username='john_doe')
        if user:
            print(f"  Found: {user['username']}, age: {user['age']}")

        # 6. Count records
        print("\n6. Counting users:")
        user_count = db_manager.count()
        print(f"  Total users: {user_count}")

        # 7. Table information
        print("\n7. Table information:")
        table_info = db_manager.get_table_info()
        print(f"  Table: {table_info['table_name']}")
        print(f"  Rows: {table_info['row_count']}")
        print(f"  Columns: {len(table_info['columns'])}")

        # 8. Batch insert
        print("\n8. Batch insert:")
        new_users = [
            {'username': 'bob_brown', 'email': 'bob@example.com'},
            {'username': 'alice_green', 'email': 'alice@example.com'},
        ]
        inserted = db_manager.batch_insert(new_users)
        print(f"  Inserted {len(inserted)} users in batch")

        # 9. Delete
        print("\n9. Deleting inactive users...")
        deleted = db_manager.delete(is_active=False)
        print(f"  Deleted inactive users: {deleted}")

    finally:
        # Close connection
        db_manager.close()


# Convenience function to create manager with default configuration
def create_postgres_manager(table_name: str, schema: Dict[str, Any]) -> PostgresDataManager:
    """
    Create PostgresDataManager with default configuration.

    param table_name: Name of the table
    param schema: Table schema definition
    return: PostgresDataManager instance
    """
    return PostgresDataManager(table_name=table_name, schema=schema)


# Function to test database connectivity
def test_connection(config: Optional[ConnectionConfig] = None) -> bool:
    """
    Test PostgreSQL database connection.

    param config: Connection configuration
    return: True if connection successful
    """
    config = config or ConnectionConfig()

    try:
        # Test basic connection
        conn = psycopg2.connect(
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.user,
            password=config.password
        )
        conn.close()
        print("Database connection successful")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


# if __name__ == "__main__":
#     # Run example when file is executed directly
#     # Before running, set environment variables or modify ConnectionConfig
#     print("PostgreSQL Data Manager Example")
#     print("=" * 50)
#
#     # Check for required environment variables
#     required_vars = ['PG_HOST', 'PG_DATABASE', 'PG_USER']
#     missing_vars = [var for var in required_vars if not os.getenv(var)]
#
#     if missing_vars:
#         print(f"Warning: Missing environment variables: {missing_vars}")
#         print("Using default values or you can create a .env file")
#         print()
#
#     # Test connection first
#     if test_connection():
#         run_postgres_example()
#     else:
#         print("Cannot run example due to connection issues")
