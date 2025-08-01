"""
File system operations and temporary storage for LSNP file transfers.
Creates temporary directories, manages file operations, and handles cleanup.
"""

import os
import shutil
import tempfile
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from ..utils.file_utils import FileUtils


class StorageStatus(Enum):
    """Status of file storage operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class StorageMetadata:
    """Metadata for stored files."""
    file_id: str
    original_filename: str
    stored_filename: str
    file_size: int
    mime_type: str
    checksum: str
    created_time: float
    completed_time: Optional[float] = None
    status: StorageStatus = StorageStatus.PENDING
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StorageMetadata':
        """Create from dictionary."""
        data['status'] = StorageStatus(data['status'])
        return cls(**data)


class FileStorage:
    """Manages file system operations for LSNP file transfers."""
    
    def __init__(self, base_dir: str = "lsnp_storage"):
        """
        Initialize file storage manager.
        
        Args:
            base_dir: Base directory for all file storage
        """
        self.base_dir = Path(base_dir)
        self.temp_dir = self.base_dir / "temp"
        self.completed_dir = self.base_dir / "completed"
        self.metadata_dir = self.base_dir / "metadata"
        
        # Create directories
        self._create_directories()
        
        # Metadata tracking
        self.metadata: Dict[str, StorageMetadata] = {}
        self._load_metadata()
    
    def _create_directories(self):
        """Create necessary storage directories."""
        for directory in [self.base_dir, self.temp_dir, self.completed_dir, self.metadata_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _load_metadata(self):
        """Load metadata from disk."""
        try:
            for metadata_file in self.metadata_dir.glob("*.json"):
                with open(metadata_file, 'r') as f:
                    data = json.load(f)
                    metadata = StorageMetadata.from_dict(data)
                    self.metadata[metadata.file_id] = metadata
        except Exception as e:
            print(f"Error loading metadata: {e}")
    
    def _save_metadata(self, file_id: str):
        """Save metadata for a file to disk."""
        if file_id not in self.metadata:
            return
        
        try:
            metadata_file = self.metadata_dir / f"{file_id}.json"
            with open(metadata_file, 'w') as f:
                json.dump(self.metadata[file_id].to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving metadata for {file_id}: {e}")
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of a file."""
        import hashlib
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def create_temp_file(self, file_id: str, original_filename: str, 
                        file_size: int, mime_type: str = "application/octet-stream") -> Optional[str]:
        """
        Create a temporary file for an incoming transfer.
        
        Args:
            file_id: Unique file transfer ID
            original_filename: Original name of the file
            file_size: Expected size of the file
            mime_type: MIME type of the file
            
        Returns:
            Path to temporary file if successful, None otherwise
        """
        try:
            # Sanitize filename
            safe_filename = FileUtils.sanitize_filename(original_filename)
            temp_filename = f"{file_id}_{safe_filename}"
            temp_path = self.temp_dir / temp_filename
            
            # Create empty temp file
            temp_path.touch()
            
            # Create metadata
            metadata = StorageMetadata(
                file_id=file_id,
                original_filename=original_filename,
                stored_filename=temp_filename,
                file_size=file_size,
                mime_type=mime_type,
                checksum="",
                created_time=time.time(),
                status=StorageStatus.IN_PROGRESS
            )
            
            self.metadata[file_id] = metadata
            self._save_metadata(file_id)
            
            return str(temp_path)
            
        except Exception as e:
            print(f"Error creating temp file: {e}")
            return None
    
    def write_chunk_to_temp_file(self, file_id: str, chunk_data: bytes, 
                                offset: int) -> bool:
        """
        Write chunk data to temporary file at specified offset.
        
        Args:
            file_id: File transfer ID
            chunk_data: Binary data to write
            offset: Byte offset where to write data
            
        Returns:
            True if successful, False otherwise
        """
        if file_id not in self.metadata:
            return False
        
        try:
            metadata = self.metadata[file_id]
            temp_path = self.temp_dir / metadata.stored_filename
            
            with open(temp_path, 'r+b') as f:
                f.seek(offset)
                f.write(chunk_data)
            
            return True
            
        except Exception as e:
            print(f"Error writing chunk to temp file: {e}")
            return False
    
    def finalize_temp_file(self, file_id: str, expected_size: Optional[int] = None) -> Optional[str]:
        """
        Finalize a temporary file and move it to completed storage.
        
        Args:
            file_id: File transfer ID
            expected_size: Expected file size for validation
            
        Returns:
            Path to finalized file if successful, None otherwise
        """
        if file_id not in self.metadata:
            return None
        
        try:
            metadata = self.metadata[file_id]
            temp_path = self.temp_dir / metadata.stored_filename
            
            if not temp_path.exists():
                return None
            
            # Validate file size
            actual_size = temp_path.stat().st_size
            expected = expected_size or metadata.file_size
            
            if actual_size != expected:
                print(f"File size mismatch: expected {expected}, got {actual_size}")
                return None
            
            # Calculate checksum
            checksum = self._calculate_checksum(temp_path)
            
            # Move to completed directory
            completed_filename = f"{file_id}_{FileUtils.sanitize_filename(metadata.original_filename)}"
            completed_path = self.completed_dir / completed_filename
            
            # Handle filename conflicts
            counter = 1
            original_completed_path = completed_path
            while completed_path.exists():
                name_stem = original_completed_path.stem
                suffix = original_completed_path.suffix
                completed_path = original_completed_path.parent / f"{name_stem}_{counter}{suffix}"
                counter += 1
            
            shutil.move(str(temp_path), str(completed_path))
            
            # Update metadata
            metadata.stored_filename = completed_path.name
            metadata.checksum = checksum
            metadata.completed_time = time.time()
            metadata.status = StorageStatus.COMPLETED
            
            self._save_metadata(file_id)
            
            return str(completed_path)
            
        except Exception as e:
            print(f"Error finalizing temp file: {e}")
            return None
    
    def store_complete_file(self, file_path: str, file_id: str, 
                           original_filename: Optional[str] = None) -> Optional[str]:
        """
        Store a complete file directly (for outgoing transfers).
        
        Args:
            file_path: Path to source file
            file_id: Unique file transfer ID
            original_filename: Original filename (uses source filename if None)
            
        Returns:
            Path to stored file if successful, None otherwise
        """
        try:
            source_path = Path(file_path)
            if not source_path.exists():
                return None
            
            # Get file info
            file_info = FileUtils.get_file_info(file_path)
            if 'error' in file_info:
                return None
            
            filename = original_filename or file_info['filename']
            safe_filename = FileUtils.sanitize_filename(filename)
            stored_filename = f"{file_id}_{safe_filename}"
            stored_path = self.completed_dir / stored_filename
            
            # Handle filename conflicts
            counter = 1
            original_stored_path = stored_path
            while stored_path.exists():
                name_stem = original_stored_path.stem
                suffix = original_stored_path.suffix
                stored_path = original_stored_path.parent / f"{name_stem}_{counter}{suffix}"
                counter += 1
            
            # Copy file
            shutil.copy2(file_path, stored_path)
            
            # Calculate checksum
            checksum = self._calculate_checksum(stored_path)
            
            # Create metadata
            metadata = StorageMetadata(
                file_id=file_id,
                original_filename=filename,
                stored_filename=stored_path.name,
                file_size=file_info['size'],
                mime_type=file_info['mime_type'],
                checksum=checksum,
                created_time=time.time(),
                completed_time=time.time(),
                status=StorageStatus.COMPLETED
            )
            
            self.metadata[file_id] = metadata
            self._save_metadata(file_id)
            
            return str(stored_path)
            
        except Exception as e:
            print(f"Error storing complete file: {e}")
            return None
    
    def get_file_path(self, file_id: str) -> Optional[str]:
        """
        Get the current path of a stored file.
        
        Args:
            file_id: File transfer ID
            
        Returns:
            File path if found, None otherwise
        """
        if file_id not in self.metadata:
            return None
        
        metadata = self.metadata[file_id]
        
        if metadata.status == StorageStatus.COMPLETED:
            path = self.completed_dir / metadata.stored_filename
        else:
            path = self.temp_dir / metadata.stored_filename
        
        return str(path) if path.exists() else None
    
    def get_file_metadata(self, file_id: str) -> Optional[StorageMetadata]:
        """Get metadata for a stored file."""
        return self.metadata.get(file_id)
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a stored file and its metadata.
        
        Args:
            file_id: File transfer ID
            
        Returns:
            True if deleted successfully, False otherwise
        """
        if file_id not in self.metadata:
            return False
        
        try:
            metadata = self.metadata[file_id]
            
            # Delete file from appropriate directory
            if metadata.status == StorageStatus.COMPLETED:
                file_path = self.completed_dir / metadata.stored_filename
            else:
                file_path = self.temp_dir / metadata.stored_filename
            
            if file_path.exists():
                file_path.unlink()
            
            # Delete metadata file
            metadata_file = self.metadata_dir / f"{file_id}.json"
            if metadata_file.exists():
                metadata_file.unlink()
            
            # Remove from memory
            del self.metadata[file_id]
            
            return True
            
        except Exception as e:
            print(f"Error deleting file {file_id}: {e}")
            return False
    
    def cleanup_failed_transfers(self, max_age_hours: int = 24):
        """
        Clean up failed or abandoned temporary files.
        
        Args:
            max_age_hours: Maximum age for temp files before cleanup
        """
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        to_cleanup = []
        
        for file_id, metadata in self.metadata.items():
            if (metadata.status in [StorageStatus.FAILED, StorageStatus.IN_PROGRESS] and
                current_time - metadata.created_time > max_age_seconds):
                to_cleanup.append(file_id)
        
        for file_id in to_cleanup:
            self.delete_file(file_id)
            print(f"Cleaned up abandoned transfer: {file_id}")
    
    def cleanup_old_completed_files(self, max_age_days: int = 30):
        """
        Clean up old completed files.
        
        Args:
            max_age_days: Maximum age for completed files before cleanup
        """
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 3600
        
        to_cleanup = []
        
        for file_id, metadata in self.metadata.items():
            if (metadata.status == StorageStatus.COMPLETED and
                metadata.completed_time and
                current_time - metadata.completed_time > max_age_seconds):
                to_cleanup.append(file_id)
        
        for file_id in to_cleanup:
            self.delete_file(file_id)
            print(f"Cleaned up old completed file: {file_id}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        stats = {
            'total_files': len(self.metadata),
            'pending_files': 0,
            'in_progress_files': 0,
            'completed_files': 0,
            'failed_files': 0,
            'total_size': 0,
            'temp_size': 0,
            'completed_size': 0
        }
        
        for metadata in self.metadata.values():
            stats[f"{metadata.status.value}_files"] += 1
            stats['total_size'] += metadata.file_size
            
            if metadata.status == StorageStatus.COMPLETED:
                stats['completed_size'] += metadata.file_size
            else:
                stats['temp_size'] += metadata.file_size
        
        # Format sizes
        stats['total_size_formatted'] = FileUtils.format_file_size(stats['total_size'])
        stats['temp_size_formatted'] = FileUtils.format_file_size(stats['temp_size'])
        stats['completed_size_formatted'] = FileUtils.format_file_size(stats['completed_size'])
        
        return stats
    
    def list_files(self, status_filter: Optional[StorageStatus] = None) -> List[StorageMetadata]:
        """
        List stored files, optionally filtered by status.
        
        Args:
            status_filter: Only return files with this status
            
        Returns:
            List of file metadata
        """
        files = list(self.metadata.values())
        
        if status_filter:
            files = [f for f in files if f.status == status_filter]
        
        # Sort by creation time (newest first)
        files.sort(key=lambda x: x.created_time, reverse=True)
        
        return files
    
    def verify_file_integrity(self, file_id: str) -> Dict[str, Any]:
        """
        Verify integrity of a stored file.
        
        Args:
            file_id: File transfer ID
            
        Returns:
            Dictionary with verification results
        """
        if file_id not in self.metadata:
            return {'error': 'File not found'}
        
        metadata = self.metadata[file_id]
        file_path = self.get_file_path(file_id)
        
        if not file_path or not Path(file_path).exists():
            return {'error': 'File does not exist on disk'}
        
        try:
            # Check file size
            actual_size = Path(file_path).stat().st_size
            size_valid = actual_size == metadata.file_size
            
            # Check checksum if available
            checksum_valid = True
            if metadata.checksum:
                actual_checksum = self._calculate_checksum(Path(file_path))
                checksum_valid = actual_checksum == metadata.checksum
            
            return {
                'file_id': file_id,
                'file_exists': True,
                'size_valid': size_valid,
                'expected_size': metadata.file_size,
                'actual_size': actual_size,
                'checksum_valid': checksum_valid,
                'expected_checksum': metadata.checksum,
                'valid': size_valid and checksum_valid
            }
            
        except Exception as e:
            return {'error': f'Verification failed: {e}'}
    
    def export_file(self, file_id: str, destination_path: str) -> bool:
        """
        Export a stored file to a destination path.
        
        Args:
            file_id: File transfer ID
            destination_path: Where to copy the file
            
        Returns:
            True if exported successfully, False otherwise
        """
        source_path = self.get_file_path(file_id)
        if not source_path:
            return False
        
        try:
            # Ensure destination directory exists
            dest_path = Path(destination_path)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(source_path, destination_path)
            return True
            
        except Exception as e:
            print(f"Error exporting file: {e}")
            return False