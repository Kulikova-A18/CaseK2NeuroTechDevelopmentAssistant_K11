"""
CSV data manager for thread-safe reading and writing.
Manages CSV files with schema validation and automatic ID generation.
"""

import os
import csv
import json
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional


class CSVDataManager:
    """
    Manager for working with CSV files.
    Provides thread-safe data reading and writing.
    
    @param file_path: Path to CSV file
    @param schema: Data schema with types and validation
    """
    
    def __init__(self, file_path: str, schema: Dict[str, Any]):
        self.file_path = file_path
        self.schema = schema
        self._ensure_file_exists()
        self._lock = threading.Lock()
    
    def _ensure_file_exists(self):
        """Create file with headers if it doesn't exist."""
        if not os.path.exists(self.file_path):
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.schema.keys())
                writer.writeheader()
    
    def read_all(self) -> List[Dict[str, str]]:
        """
        Read all records from CSV file.
        
        @return: List of all records
        """
        with self._lock:
            with open(self.file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)
    
    def write_all(self, data: List[Dict[str, str]]):
        """
        Write all records to CSV file.
        
        @param data: Data to write
        """
        with self._lock:
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.schema.keys())
                writer.writeheader()
                writer.writerows(data)
    
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
        Insert new record into CSV.
        
        @param data: Data to insert
        @return: Inserted record
        @raises ValueError: If required fields are missing
        """
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
        self.write_all(all_data)
        
        return validated_data
    
    def update(self, filter_kwargs: Dict[str, Any], update_data: Dict[str, Any]) -> bool:
        """
        Update records by filter.
        
        @param filter_kwargs: Criteria for finding records
        @param update_data: Data to update
        @return: True if update was successful
        """
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
            self.write_all(all_data)
        
        return updated
    
    def delete(self, **kwargs) -> bool:
        """
        Delete records by criteria.
        
        @param **kwargs: Deletion criteria
        @return: True if deletion was successful
        """
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
            self.write_all(new_data)
        
        return deleted