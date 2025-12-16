"""
Tests for CSV data manager.
"""

import unittest
import os
import tempfile
import csv
from modules.csv_manager import CSVDataManager


class TestCSVDataManager(unittest.TestCase):
    """Test CSV data manager."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary CSV file
        self.temp_dir = tempfile.mkdtemp()
        self.csv_path = os.path.join(self.temp_dir, 'test.csv')
        
        # Define schema
        self.schema = {
            'id': {'required': True, 'type': 'integer'},
            'name': {'required': True, 'type': 'string'},
            'value': {'required': False, 'type': 'string', 'default': 'default'},
            'created_at': {'required': False, 'type': 'datetime'}
        }
        
        self.manager = CSVDataManager(self.csv_path, self.schema)
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_file_creation(self):
        """Test file creation with headers."""
        self.assertTrue(os.path.exists(self.csv_path))
        
        # Check headers
        with open(self.csv_path, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            self.assertEqual(headers, ['id', 'name', 'value', 'created_at'])
    
    def test_insert(self):
        """Test record insertion."""
        # Insert test record
        test_data = {'id': 1, 'name': 'Test'}
        inserted = self.manager.insert(test_data)
        
        self.assertEqual(inserted['id'], '1')
        self.assertEqual(inserted['name'], 'Test')
        self.assertEqual(inserted['value'], 'default')  # Default value
        self.assertIn('created_at', inserted)  # Auto-generated timestamp
        
        # Verify record was written
        records = self.manager.read_all()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['name'], 'Test')
    
    def test_auto_id_generation(self):
        """Test automatic ID generation."""
        # Insert without ID
        test_data = {'name': 'Test1'}
        inserted1 = self.manager.insert(test_data)
        self.assertEqual(inserted1['id'], '1')
        
        # Insert another without ID
        test_data2 = {'name': 'Test2'}
        inserted2 = self.manager.insert(test_data2)
        self.assertEqual(inserted2['id'], '2')
    
    def test_find(self):
        """Test record finding."""
        # Insert test records
        self.manager.insert({'id': 1, 'name': 'Alice', 'value': 'A'})
        self.manager.insert({'id': 2, 'name': 'Bob', 'value': 'B'})
        self.manager.insert({'id': 3, 'name': 'Alice', 'value': 'C'})
        
        # Find by name
        results = self.manager.find(name='Alice')
        self.assertEqual(len(results), 2)
        
        # Find by id
        result = self.manager.find_one(id='2')
        self.assertEqual(result['name'], 'Bob')
    
    def test_update(self):
        """Test record update."""
        # Insert test record
        self.manager.insert({'id': 1, 'name': 'OldName', 'value': 'OldValue'})
        
        # Update record
        success = self.manager.update(
            {'id': '1'},
            {'name': 'NewName', 'value': 'NewValue'}
        )
        
        self.assertTrue(success)
        
        # Verify update
        updated = self.manager.find_one(id='1')
        self.assertEqual(updated['name'], 'NewName')
        self.assertEqual(updated['value'], 'NewValue')
    
    def test_delete(self):
        """Test record deletion."""
        # Insert test records
        self.manager.insert({'id': 1, 'name': 'ToDelete'})
        self.manager.insert({'id': 2, 'name': 'Keep'})
        
        # Delete record
        success = self.manager.delete(id='1')
        
        self.assertTrue(success)
        
        # Verify deletion
        records = self.manager.read_all()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['name'], 'Keep')


if __name__ == '__main__':
    unittest.main()