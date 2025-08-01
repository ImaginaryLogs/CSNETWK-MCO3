from typing import List
"""
Avatar/profile picture handling for LSNP PROFILE messages.
Processes AVATAR_TYPE, AVATAR_ENCODING, and AVATAR_DATA fields.
"""

import os
import hashlib
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass

from ....utils.file_utils import FileUtils


@dataclass
class Avatar:
    """Represents a user's avatar/profile picture."""
    user_id: str
    mime_type: str
    encoding: str
    data: bytes
    size: int
    hash: str
    
    @property
    def is_valid(self) -> bool:
        """Check if avatar data is valid."""
        return FileUtils.validate_avatar_image(self.data, self.mime_type)
    
    @property
    def file_extension(self) -> str:
        """Get appropriate file extension for the avatar."""
        extensions = {
            'image/png': '.png',
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/gif': '.gif',
            'image/bmp': '.bmp',
            'image/webp': '.webp'
        }
        return extensions.get(self.mime_type, '.img')


class AvatarHandler:
    """Handles avatar processing for LSNP PROFILE messages."""
    
    def __init__(self, avatar_cache_dir: Optional[str] = None):
        """
        Initialize avatar handler.
        
        Args:
            avatar_cache_dir: Directory to cache avatar images
        """
        self.avatar_cache_dir = avatar_cache_dir or "avatars"
        self.avatars: Dict[str, Avatar] = {}
        self._ensure_cache_directory()
    
    def _ensure_cache_directory(self):
        """Ensure avatar cache directory exists."""
        if self.avatar_cache_dir:
            Path(self.avatar_cache_dir).mkdir(parents=True, exist_ok=True)
    
    def _calculate_hash(self, data: bytes) -> str:
        """Calculate hash of avatar data for caching."""
        return hashlib.md5(data).hexdigest()[:8]
    
    def process_avatar_from_profile(self, user_id: str, profile_data: Dict[str, str]) -> Optional[Avatar]:
        """
        Process avatar data from a PROFILE message.
        
        Args:
            user_id: User ID of the profile owner
            profile_data: Dictionary containing profile message fields
            
        Returns:
            Avatar object if valid, None otherwise
        """
        # Check if avatar fields are present
        avatar_type = profile_data.get('AVATAR_TYPE')
        avatar_encoding = profile_data.get('AVATAR_ENCODING')
        avatar_data = profile_data.get('AVATAR_DATA')
        
        if not all([avatar_type, avatar_encoding, avatar_data]):
            return None
        
        # Currently only base64 encoding is supported
        if avatar_encoding.lower() != 'base64':
            print(f"Unsupported avatar encoding: {avatar_encoding}")
            return None
        
        try:
            # Decode base64 data
            decoded_data = FileUtils.decode_base64(avatar_data)
            data_size = len(decoded_data)
            
            # Validate avatar
            if not FileUtils.validate_avatar_image(decoded_data, avatar_type):
                print(f"Invalid avatar image for user {user_id}")
                return None
            
            # Create avatar object
            avatar = Avatar(
                user_id=user_id,
                mime_type=avatar_type,
                encoding=avatar_encoding,
                data=decoded_data,
                size=data_size,
                hash=self._calculate_hash(decoded_data)
            )
            
            # Cache the avatar
            self.avatars[user_id] = avatar
            self._cache_avatar_to_disk(avatar)
            
            return avatar
            
        except Exception as e:
            print(f"Error processing avatar for user {user_id}: {e}")
            return None
    
    def _cache_avatar_to_disk(self, avatar: Avatar):
        """
        Cache avatar to disk for persistent storage.
        
        Args:
            avatar: Avatar object to cache
        """
        if not self.avatar_cache_dir:
            return
        
        try:
            # Create safe filename
            safe_user_id = FileUtils.sanitize_filename(avatar.user_id.replace('@', '_at_'))
            filename = f"{safe_user_id}_{avatar.hash}{avatar.file_extension}"
            filepath = Path(self.avatar_cache_dir) / filename
            
            # Write avatar data to file
            with open(filepath, 'wb') as f:
                f.write(avatar.data)
                
        except Exception as e:
            print(f"Error caching avatar to disk: {e}")
    
    def load_avatar_from_file(self, user_id: str, file_path: str) -> Optional[Avatar]:
        """
        Load an avatar from a file for sending in PROFILE messages.
        
        Args:
            user_id: User ID who will own this avatar
            file_path: Path to the avatar image file
            
        Returns:
            Avatar object if successful, None otherwise
        """
        if not FileUtils.validate_file_path(file_path):
            print(f"Avatar file not found or not readable: {file_path}")
            return None
        
        try:
            # Get file info
            file_info = FileUtils.get_file_info(file_path)
            if 'error' in file_info:
                print(f"Error reading avatar file: {file_info['error']}")
                return None
            
            # Check file size
            if file_info['size'] > FileUtils.MAX_AVATAR_SIZE:
                print(f"Avatar file too large: {file_info['formatted_size']} (max: {FileUtils.format_file_size(FileUtils.MAX_AVATAR_SIZE)})")
                return None
            
            # Check MIME type
            mime_type = file_info['mime_type']
            if mime_type not in FileUtils.SUPPORTED_AVATAR_FORMATS:
                print(f"Unsupported avatar format: {mime_type}")
                return None
            
            # Read file data
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Validate image format
            if not FileUtils.validate_avatar_image(data, mime_type):
                print("Invalid avatar image format")
                return None
            
            # Create avatar object
            avatar = Avatar(
                user_id=user_id,
                mime_type=mime_type,
                encoding='base64',
                data=data,
                size=len(data),
                hash=self._calculate_hash(data)
            )
            
            # Cache the avatar
            self.avatars[user_id] = avatar
            return avatar
            
        except Exception as e:
            print(f"Error loading avatar from file: {e}")
            return None
    
    def get_avatar(self, user_id: str) -> Optional[Avatar]:
        """
        Get cached avatar for a user.
        
        Args:
            user_id: User ID to get avatar for
            
        Returns:
            Avatar object if found, None otherwise
        """
        return self.avatars.get(user_id)
    
    def remove_avatar(self, user_id: str) -> bool:
        """
        Remove cached avatar for a user.
        
        Args:
            user_id: User ID to remove avatar for
            
        Returns:
            True if avatar was removed, False if not found
        """
        if user_id in self.avatars:
            del self.avatars[user_id]
            self._remove_avatar_from_disk(user_id)
            return True
        return False
    
    def _remove_avatar_from_disk(self, user_id: str):
        """
        Remove avatar files from disk cache.
        
        Args:
            user_id: User ID whose avatar files to remove
        """
        if not self.avatar_cache_dir:
            return
        
        try:
            cache_dir = Path(self.avatar_cache_dir)
            if not cache_dir.exists():
                return
            
            # Find and remove files matching the user ID pattern
            safe_user_id = FileUtils.sanitize_filename(user_id.replace('@', '_at_'))
            pattern = f"{safe_user_id}_*"
            
            for file_path in cache_dir.glob(pattern):
                if file_path.is_file():
                    file_path.unlink()
                    
        except Exception as e:
            print(f"Error removing avatar from disk: {e}")
    
    def create_profile_avatar_fields(self, user_id: str) -> Dict[str, str]:
        """
        Create avatar fields for inclusion in a PROFILE message.
        
        Args:
            user_id: User ID to create avatar fields for
            
        Returns:
            Dictionary with AVATAR_* fields or empty dict if no avatar
        """
        avatar = self.get_avatar(user_id)
        if not avatar:
            return {}
        
        return {
            'AVATAR_TYPE': avatar.mime_type,
            'AVATAR_ENCODING': avatar.encoding,
            'AVATAR_DATA': FileUtils.encode_base64(avatar.data)
        }
    
    def get_avatar_info(self, user_id: str) -> Dict[str, Any]:
        """
        Get information about a user's avatar.
        
        Args:
            user_id: User ID to get info for
            
        Returns:
            Dictionary with avatar information
        """
        avatar = self.get_avatar(user_id)
        if not avatar:
            return {'has_avatar': False}
        
        return {
            'has_avatar': True,
            'user_id': avatar.user_id,
            'mime_type': avatar.mime_type,
            'encoding': avatar.encoding,
            'size': avatar.size,
            'formatted_size': FileUtils.format_file_size(avatar.size),
            'hash': avatar.hash,
            'is_valid': avatar.is_valid,
            'file_extension': avatar.file_extension
        }
    
    def list_cached_avatars(self) -> List[str]:
        """
        Get list of user IDs with cached avatars.
        
        Returns:
            List of user IDs
        """
        return list(self.avatars.keys())
    
    def cleanup_old_avatars(self, max_age_days: int = 30):
        """
        Clean up old avatar cache files.
        
        Args:
            max_age_days: Maximum age in days for cached avatars
        """
        if not self.avatar_cache_dir:
            return
        
        try:
            import time
            cache_dir = Path(self.avatar_cache_dir)
            if not cache_dir.exists():
                return
            
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            for file_path in cache_dir.iterdir():
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        
        except Exception as e:
            print(f"Error cleaning up old avatars: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the avatar cache.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = {
            'cached_avatars': len(self.avatars),
            'total_size': sum(avatar.size for avatar in self.avatars.values()),
            'cache_directory': self.avatar_cache_dir
        }
        
        if self.avatar_cache_dir:
            try:
                cache_dir = Path(self.avatar_cache_dir)
                if cache_dir.exists():
                    files = [f for f in cache_dir.iterdir() if f.is_file()]
                    stats['disk_files'] = len(files)
                    stats['disk_size'] = sum(f.stat().st_size for f in files)
                else:
                    stats['disk_files'] = 0
                    stats['disk_size'] = 0
            except Exception:
                stats['disk_files'] = 'unknown'
                stats['disk_size'] = 'unknown'
        
        return stats