"""
File-related utility functions for LSNP file transfer.
Handles Base64 encoding/decoding, file type detection, and MIME type operations.
"""

import base64
import mimetypes
import os
import hashlib
from typing import Optional, Tuple, Dict, Any
from pathlib import Path


class FileUtils:
    """Utility class for file operations in LSNP."""
    
    # Supported image formats for avatars
    SUPPORTED_AVATAR_FORMATS = {
        'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 
        'image/bmp', 'image/webp'
    }
    
    # Maximum avatar size in bytes (~20KB as per RFC)
    MAX_AVATAR_SIZE = 20 * 1024
    
    # Default chunk size for file transfers (can be configured)
    DEFAULT_CHUNK_SIZE = 1024  # 1KB chunks
    MAX_CHUNK_SIZE = 8192     # 8KB max chunk size
    
    @staticmethod
    def encode_base64(data: bytes) -> str:
        """
        Encode binary data to base64 string.
        
        Args:
            data: Binary data to encode
            
        Returns:
            Base64 encoded string
        """
        return base64.b64encode(data).decode('utf-8')
    
    @staticmethod
    def decode_base64(encoded_data: str) -> bytes:
        """
        Decode base64 string to binary data.
        
        Args:
            encoded_data: Base64 encoded string
            
        Returns:
            Decoded binary data
            
        Raises:
            ValueError: If base64 data is invalid
        """
        try:
            return base64.b64decode(encoded_data)
        except Exception as e:
            raise ValueError(f"Invalid base64 data: {e}")
    
    @staticmethod
    def get_mime_type(file_path: str) -> str:
        """
        Get MIME type of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MIME type string, defaults to 'application/octet-stream'
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'
    
    @staticmethod
    def validate_avatar_image(data: bytes, mime_type: str) -> bool:
        """
        Validate avatar image data and format.
        
        Args:
            data: Image binary data
            mime_type: MIME type of the image
            
        Returns:
            True if valid, False otherwise
        """
        # Check MIME type
        if mime_type not in FileUtils.SUPPORTED_AVATAR_FORMATS:
            return False
        
        # Check size
        if len(data) > FileUtils.MAX_AVATAR_SIZE:
            return False
        
        # Basic format validation (check magic bytes)
        return FileUtils._validate_image_format(data, mime_type)
    
    @staticmethod
    def _validate_image_format(data: bytes, mime_type: str) -> bool:
        """
        Validate image format by checking magic bytes.
        
        Args:
            data: Image binary data
            mime_type: Expected MIME type
            
        Returns:
            True if format matches MIME type
        """
        if len(data) < 8:
            return False
        
        # Check magic bytes for different formats
        magic_bytes = {
            'image/png': b'\x89PNG\r\n\x1a\n',
            'image/jpeg': b'\xff\xd8\xff',
            'image/jpg': b'\xff\xd8\xff',
            'image/gif': b'GIF8',
            'image/bmp': b'BM',
            'image/webp': b'RIFF'
        }
        
        expected_magic = magic_bytes.get(mime_type)
        if not expected_magic:
            return True  # Unknown format, allow it
        
        return data.startswith(expected_magic)
    
    @staticmethod
    def calculate_optimal_chunk_size(file_size: int, target_chunks: int = 50) -> int:
        """
        Calculate optimal chunk size for file transfer.
        
        Args:
            file_size: Size of file in bytes
            target_chunks: Target number of chunks
            
        Returns:
            Optimal chunk size in bytes
        """
        if file_size <= 0:
            return FileUtils.DEFAULT_CHUNK_SIZE
        
        # Calculate ideal chunk size
        ideal_size = file_size // target_chunks
        
        # Clamp to min/max bounds
        chunk_size = max(FileUtils.DEFAULT_CHUNK_SIZE, 
                        min(ideal_size, FileUtils.MAX_CHUNK_SIZE))
        
        return chunk_size
    
    @staticmethod
    def calculate_total_chunks(file_size: int, chunk_size: int) -> int:
        """
        Calculate total number of chunks needed for a file.
        
        Args:
            file_size: Size of file in bytes
            chunk_size: Size of each chunk in bytes
            
        Returns:
            Total number of chunks needed
        """
        if chunk_size <= 0:
            raise ValueError("Chunk size must be positive")
        
        return (file_size + chunk_size - 1) // chunk_size
    
    @staticmethod
    def generate_file_id(file_path: str, timestamp: int) -> str:
        """
        Generate unique file ID for transfer.
        
        Args:
            file_path: Path to the file
            timestamp: Unix timestamp
            
        Returns:
            Unique file ID (8 character hex string)
        """
        # Create hash from file path and timestamp
        data = f"{file_path}:{timestamp}".encode('utf-8')
        hash_digest = hashlib.md5(data).hexdigest()
        return hash_digest[:8]  # Return first 8 characters
    
    @staticmethod
    def validate_file_path(file_path: str) -> bool:
        """
        Validate if file path exists and is readable.
        
        Args:
            file_path: Path to validate
            
        Returns:
            True if valid and readable
        """
        try:
            path = Path(file_path)
            return path.exists() and path.is_file() and os.access(file_path, os.R_OK)
        except (OSError, ValueError):
            return False
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename for safe storage.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove or replace dangerous characters
        dangerous_chars = '<>:"/\\|?*'
        sanitized = filename
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip(' .')
        
        # Ensure it's not empty
        if not sanitized:
            sanitized = "unnamed_file"
        
        # Limit length
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:250 - len(ext)] + ext
        
        return sanitized
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string (e.g., "1.5 KB", "2.3 MB")
        """
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"
    
    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, Any]:
        """
        Get comprehensive file information.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file information
        """
        try:
            path = Path(file_path)
            stat = path.stat()
            
            return {
                'filename': path.name,
                'size': stat.st_size,
                'mime_type': FileUtils.get_mime_type(file_path),
                'modified_time': stat.st_mtime,
                'readable': os.access(file_path, os.R_OK),
                'formatted_size': FileUtils.format_file_size(stat.st_size)
            }
        except (OSError, ValueError) as e:
            return {'error': str(e)}