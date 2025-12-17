"""
Hash manager for file integrity verification.
Provides SHA-256 hash calculation, storage and verification for CSV files.
"""

import os
import json
import hashlib
import threading
from typing import Dict, Optional, List
from datetime import datetime

import logging

logger = logging.getLogger(__name__)

class FileHashManager:
    """
    Manager for file hash verification.
    Stores and verifies SHA-256 hashes for monitored files.

    @param hash_file_path: Path to JSON file storing hashes
    """

    def __init__(self, hash_file_path: str = "hashes.json"):
        self.hash_file_path = hash_file_path
        self._lock = threading.Lock()
        self._load_hashes()

    def _load_hashes(self) -> Dict[str, Dict[str, str]]:
        """Load hashes from JSON file or create empty dict."""
        if os.path.exists(self.hash_file_path):
            try:
                with open(self.hash_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_hashes(self, hashes: Dict[str, Dict[str, str]]):
        """Save hashes to JSON file."""
        with open(self.hash_file_path, 'w', encoding='utf-8') as f:
            json.dump(hashes, f, indent=2, ensure_ascii=False)

    def calculate_hash(self, file_path: str) -> str:
        """
        Calculate SHA-256 hash of a file.

        @param file_path: Path to file
        @return: SHA-256 hash as hex string
        @raises FileNotFoundError: If file doesn't exist
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, 'rb') as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()

    def get_file_hash(self, file_path: str) -> Optional[str]:
        """
        Get stored hash for a file.

        @param file_path: Path to file
        @return: Stored hash or None if not found
        """
        hashes = self._load_hashes()
        file_abs_path = os.path.abspath(file_path)

        if file_abs_path in hashes:
            return hashes[file_abs_path].get('hash')

        return None

    def verify_file(self, file_path: str) -> Dict[str, any]:
        """
        Verify file integrity by comparing current hash with stored hash.

        @param file_path: Path to file
        @return: Dictionary with verification results
        """
        if not os.path.exists(file_path):
            return {
                'valid': False,
                'message': f"File not found: {file_path}",
                'current_hash': None,
                'stored_hash': None,
                'timestamp': None
            }

        current_hash = self.calculate_hash(file_path)
        stored_hash_info = self.get_stored_hash_info(file_path)
        stored_hash = stored_hash_info.get('hash') if stored_hash_info else None

        return {
            'valid': current_hash == stored_hash,
            'message': 'Hash matches' if current_hash == stored_hash else 'Hash mismatch',
            'current_hash': current_hash,
            'stored_hash': stored_hash,
            'timestamp': stored_hash_info.get('timestamp') if stored_hash_info else None,
            'file_exists': True
        }

    def update_hash(self, file_path: str, reason: str = "automatic update") -> str:
        """
        Calculate and update hash for a file.

        @param file_path: Path to file
        @param reason: Reason for hash update
        @return: New hash value
        """
        with self._lock:
            current_hash = self.calculate_hash(file_path)
            file_abs_path = os.path.abspath(file_path)

            hashes = self._load_hashes()
            hashes[file_abs_path] = {
                'hash': current_hash,
                'timestamp': datetime.now().isoformat(),
                'reason': reason,
                'file_size': os.path.getsize(file_path),
                'last_modified': os.path.getmtime(file_path)
            }

            self._save_hashes(hashes)

            return current_hash

    def get_stored_hash_info(self, file_path: str) -> Optional[Dict[str, any]]:
        """
        Get detailed information about stored hash.

        @param file_path: Path to file
        @return: Dictionary with hash info or None
        """
        hashes = self._load_hashes()
        file_abs_path = os.path.abspath(file_path)

        return hashes.get(file_abs_path)

    def remove_hash(self, file_path: str) -> bool:
        """
        Remove stored hash for a file.

        @param file_path: Path to file
        @return: True if hash was removed
        """
        with self._lock:
            hashes = self._load_hashes()
            file_abs_path = os.path.abspath(file_path)

            if file_abs_path in hashes:
                del hashes[file_abs_path]
                self._save_hashes(hashes)
                return True

            return False

    def list_monitored_files(self) -> List[Dict[str, any]]:
        """
        Get list of all monitored files with their hash info.

        @return: List of file information dictionaries
        """
        hashes = self._load_hashes()
        result = []

        for file_path, info in hashes.items():
            file_exists = os.path.exists(file_path)
            current_hash = self.calculate_hash(file_path) if file_exists else None

            result.append({
                'file_path': file_path,
                'stored_hash': info.get('hash'),
                'current_hash': current_hash,
                'timestamp': info.get('timestamp'),
                'file_exists': file_exists,
                'valid': current_hash == info.get('hash') if file_exists else False,
                'reason': info.get('reason', 'unknown'),
                'file_size': info.get('file_size'),
                'last_modified_stored': info.get('last_modified')
            })

        return result

    def verify_all_files(self) -> Dict[str, List[Dict[str, any]]]:
        """
        Verify all monitored files.

        @return: Dictionary with valid and invalid files
        """
        monitored_files = self.list_monitored_files()
        valid_files = []
        invalid_files = []

        for file_info in monitored_files:
            if file_info['file_exists']:
                if file_info['valid']:
                    valid_files.append(file_info)
                else:
                    invalid_files.append(file_info)
            else:
                invalid_files.append(file_info)

        return {
            'valid': valid_files,
            'invalid': invalid_files,
            'total_monitored': len(monitored_files),
            'total_valid': len(valid_files),
            'total_invalid': len(invalid_files)
        }
