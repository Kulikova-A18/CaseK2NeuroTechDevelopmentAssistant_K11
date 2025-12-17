"""
CSV data manager for thread-safe reading and writing.
Manages CSV files with schema validation, automatic ID generation,
and file integrity verification using SHA-256 hashes.
"""

import os
import csv
import json
import threading
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from .file_hash_manager import FileHashManager


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CSVDataManager:
    """
    Manager for working with CSV files.
    Provides thread-safe data reading and writing with file integrity verification.
    
    @param file_path: Path to CSV file
    @param schema: Data schema with types and validation
    @param hash_manager: FileHashManager instance for integrity verification
    """
    
    def __init__(self, file_path: str, schema: Dict[str, Any], 
                 hash_manager: Optional[FileHashManager] = None):
        self.file_path = file_path
        self.schema = schema
        self.hash_manager = hash_manager or FileHashManager("hashes.json")
        
        self._ensure_file_exists()
        self._lock = threading.Lock()
        
        # Verify file integrity on initialization
        self._verify_file_integrity("initialization")
    
    def _ensure_file_exists(self):
        """Create file with headers if it doesn't exist."""
        if not os.path.exists(self.file_path):
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.schema.keys())
                writer.writeheader()
            # Update hash for newly created file
            self._update_file_hash("file_created")
    
    def _verify_file_integrity(self, operation: str):
        """
        Verify file integrity before operations.
        
        @param operation: Name of operation for logging
        """
        if not self.hash_manager:
            return
        
        try:
            result = self.hash_manager.verify_file(self.file_path)
            
            if not result['valid']:
                logger.warning(f"File integrity check failed during {operation}:")
                logger.warning(f"  File: {self.file_path}")
                logger.warning(f"  Message: {result['message']}")
                logger.warning(f"  Stored hash: {result['stored_hash']}")
                logger.warning(f"  Current hash: {result['current_hash']}")
                
                # Don't block execution, just log the warning
                # Continue with normal operation
            else:
                logger.debug(f"File integrity verified for {operation}: {self.file_path}")
                
        except Exception as e:
            logger.error(f"Error during file integrity verification for {operation}: {e}")
    
    def _update_file_hash(self, reason: str):
        """
        Update file hash after modifications.
        
        @param reason: Reason for hash update
        """
        if not self.hash_manager:
            return
        
        try:
            new_hash = self.hash_manager.update_hash(self.file_path, reason)
            logger.debug(f"Hash updated for {self.file_path}: {new_hash[:16]}...")
        except Exception as e:
            logger.error(f"Error updating hash for {self.file_path}: {e}")
    
    def _perform_with_integrity_check(self, operation_name: str, operation_func, *args, **kwargs):
        """
        Perform operation with integrity check before and after.
        
        @param operation_name: Name of operation for logging
        @param operation_func: Function to execute
        @return: Result of operation
        """
        # Verify integrity before operation
        self._verify_file_integrity(f"pre_{operation_name}")
        
        # Perform the operation
        result = operation_func(*args, **kwargs)
        
        # Update hash after successful operation
        self._update_file_hash(operation_name)
        
        # Verify integrity after operation
        self._verify_file_integrity(f"post_{operation_name}")
        
        return result
    
    def read_all(self) -> List[Dict[str, str]]:
        """
        Read all records from CSV file with integrity check.
        
        @return: List of all records
        """
        def _read_operation():
            with self._lock:
                # Verify file exists
                if not os.path.exists(self.file_path):
                    return []
                
                with open(self.file_path, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    return list(reader)
        
        return self._perform_with_integrity_check("read", _read_operation)
    
    def write_all(self, data: List[Dict[str, str]]):
        """
        Write all records to CSV file with integrity check.
        
        @param data: Data to write
        """
        def _write_operation():
            with self._lock:
                with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.schema.keys())
                    writer.writeheader()
                    writer.writerows(data)
        
        self._perform_with_integrity_check("write_all", _write_operation)
    
    def find(self, **kwargs) -> List[Dict[str, str]]:
        """
        Find records by criteria.
        
        @param **kwargs: Search criteria (field=value)
        @return: Found records
        """
        results = []
        for row in self.read_all():
            match = True
            for key, value in kwargs.items():
                if str(row.get(key)) != str(value):
                    match = False
                    break
            if match:
                results.append(row)
        return results
    
    def find_one(self, **kwargs) -> Optional[Dict[str, str]]:
        """
        Find one record by criteria.
        
        @param **kwargs: Search criteria
        @return: Found record or None
        """
        results = self.find(**kwargs)
        return results[0] if results else None
    
    def insert(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Insert new record into CSV with integrity check.
        
        @param data: Data to insert
        @return: Inserted record
        @raises ValueError: If required fields are missing
        """
        def _insert_operation():
            # Validate data against schema
            validated_data = {}
            for field, field_info in self.schema.items():
                if field_info.get('required', False) and field not in data:
                    # For timestamp fields add current time
                    if field in ['registered_at', 'created_at', 'updated_at']:
                        validated_data[field] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    elif 'default' in field_info:
                        validated_data[field] = str(field_info['default'])
                    else:
                        raise ValueError(f"Required field '{field}' is missing")
                elif field in data:
                    validated_data[field] = str(data[field])
                elif 'default' in field_info:
                    validated_data[field] = str(field_info['default'])
                else:
                    validated_data[field] = ''
            
            # Generate ID if required
            if 'id' in self.schema and 'id' not in validated_data:
                last_id = 0
                for row in self.read_all():
                    try:
                        row_id = int(row.get('id', 0))
                        last_id = max(last_id, row_id)
                    except:
                        pass
                validated_data['id'] = str(last_id + 1)
            
            # Add timestamp if required and not added earlier
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for field in ['created_at', 'updated_at', 'registered_at', 'last_login']:
                if field in self.schema and field not in validated_data:
                    validated_data[field] = current_time
            
            all_data = self.read_all()
            all_data.append(validated_data)
            
            with self._lock:
                with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.schema.keys())
                    writer.writeheader()
                    writer.writerows(all_data)
            
            return validated_data
        
        return self._perform_with_integrity_check("insert", _insert_operation)
    
    def update(self, filter_kwargs: Dict[str, Any], update_data: Dict[str, Any]) -> bool:
        """
        Update records by filter with integrity check.
        
        @param filter_kwargs: Criteria for finding records
        @param update_data: Data to update
        @return: True if update was successful
        """
        def _update_operation(filter_kwargs, update_data):
            all_data = self.read_all()
            updated = False
            
            for i, row in enumerate(all_data):
                match = True
                for key, value in filter_kwargs.items():
                    if str(row.get(key)) != str(value):
                        match = False
                        break
                
                if match:
                    updated = True
                    # Update fields
                    for key, value in update_data.items():
                        if key in self.schema:
                            all_data[i][key] = str(value)
                    
                    # Update updated_at if field exists
                    if 'updated_at' in self.schema:
                        all_data[i]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if updated:
                with self._lock:
                    with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=self.schema.keys())
                        writer.writeheader()
                        writer.writerows(all_data)
            
            return updated
        
        return self._perform_with_integrity_check("update", _update_operation, filter_kwargs, update_data)
    
    def delete(self, **kwargs) -> bool:
        """
        Delete records by criteria with integrity check.
        
        @param **kwargs: Deletion criteria
        @return: True if deletion was successful
        """
        def _delete_operation(**kwargs):
            all_data = self.read_all()
            new_data = []
            deleted = False
            
            for row in all_data:
                match = True
                for key, value in kwargs.items():
                    if str(row.get(key)) != str(value):
                        match = False
                        break
                
                if not match:
                    new_data.append(row)
                else:
                    deleted = True
            
            if deleted:
                with self._lock:
                    with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=self.schema.keys())
                        writer.writeheader()
                        writer.writerows(new_data)
            
            return deleted
        
        return self._perform_with_integrity_check("delete", _delete_operation, **kwargs)
    
    def get_file_integrity_status(self) -> Dict[str, any]:
        """
        Get current file integrity status.
        
        @return: Dictionary with integrity information
        """
        if not self.hash_manager:
            return {'has_integrity_check': False}
        
        try:
            return self.hash_manager.verify_file(self.file_path)
        except Exception as e:
            logger.error(f"Error getting integrity status: {e}")
            return {'has_integrity_check': True, 'error': str(e)}
    
    def force_hash_update(self, reason: str = "manual_update"):
        """
        Force update of file hash.
        
        @param reason: Reason for hash update
        """
        self._update_file_hash(reason)