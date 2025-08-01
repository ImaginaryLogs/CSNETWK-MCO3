"""
Message format definitions for LSNP file transfer functionality.
Defines FILE_OFFER, FILE_CHUNK, FILE_RECEIVED message structures and validation.
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ....utils.tokens import validate_token, TokenValidator
from ....utils.file_utils import FileUtils


@dataclass
class FileOfferMessage:
    """FILE_OFFER message structure."""
    from_user: str
    to_user: str
    filename: str
    filesize: int
    filetype: str
    fileid: str
    description: str
    timestamp: int
    token: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format for transmission."""
        return {
            'TYPE': 'FILE_OFFER',
            'FROM': self.from_user,
            'TO': self.to_user,
            'FILENAME': self.filename,
            'FILESIZE': str(self.filesize),
            'FILETYPE': self.filetype,
            'FILEID': self.fileid,
            'DESCRIPTION': self.description,
            'TIMESTAMP': str(self.timestamp),
            'TOKEN': self.token
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'FileOfferMessage':
        """Create FileOfferMessage from dictionary."""
        return cls(
            from_user=data['FROM'],
            to_user=data['TO'],
            filename=data['FILENAME'],
            filesize=int(data['FILESIZE']),
            filetype=data['FILETYPE'],
            fileid=data['FILEID'],
            description=data.get('DESCRIPTION', ''),
            timestamp=int(data['TIMESTAMP']),
            token=data['TOKEN']
        )
    
    def validate(self) -> Dict[str, Any]:
        """Validate FILE_OFFER message."""
        errors = []
        
        # Required fields validation
        if not self.from_user:
            errors.append("FROM field is required")
        if not self.to_user:
            errors.append("TO field is required")
        if not self.filename:
            errors.append("FILENAME field is required")
        if not self.fileid:
            errors.append("FILEID field is required")
        if not self.token:
            errors.append("TOKEN field is required")
        
        # File size validation
        if self.filesize <= 0:
            errors.append("FILESIZE must be positive")
        
        # Token validation
        token_validator = TokenValidator()
        if not token_validator.validate_token_format(self.token):
            errors.append("Invalid token format")
        
        # Check token scope
        try:
            scope = token_validator.extract_scope(self.token)
            if scope != 'file':
                errors.append(f"Invalid token scope: expected 'file', got '{scope}'")
        except Exception:
            errors.append("Could not extract token scope")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }


@dataclass
class FileChunkMessage:
    """FILE_CHUNK message structure."""
    from_user: str
    to_user: str
    fileid: str
    chunk_index: int
    total_chunks: int
    chunk_size: int
    token: str
    data: str  # Base64 encoded
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format for transmission."""
        return {
            'TYPE': 'FILE_CHUNK',
            'FROM': self.from_user,
            'TO': self.to_user,
            'FILEID': self.fileid,
            'CHUNK_INDEX': str(self.chunk_index),
            'TOTAL_CHUNKS': str(self.total_chunks),
            'CHUNK_SIZE': str(self.chunk_size),
            'TOKEN': self.token,
            'DATA': self.data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'FileChunkMessage':
        """Create FileChunkMessage from dictionary."""
        return cls(
            from_user=data['FROM'],
            to_user=data['TO'],
            fileid=data['FILEID'],
            chunk_index=int(data['CHUNK_INDEX']),
            total_chunks=int(data['TOTAL_CHUNKS']),
            chunk_size=int(data['CHUNK_SIZE']),
            token=data['TOKEN'],
            data=data['DATA']
        )
    
    def validate(self) -> Dict[str, Any]:
        """Validate FILE_CHUNK message."""
        errors = []
        
        # Required fields validation
        if not self.from_user:
            errors.append("FROM field is required")
        if not self.to_user:
            errors.append("TO field is required")
        if not self.fileid:
            errors.append("FILEID field is required")
        if not self.token:
            errors.append("TOKEN field is required")
        if not self.data:
            errors.append("DATA field is required")
        
        # Numeric field validation
        if self.chunk_index < 0:
            errors.append("CHUNK_INDEX must be non-negative")
        if self.total_chunks <= 0:
            errors.append("TOTAL_CHUNKS must be positive")
        if self.chunk_size <= 0:
            errors.append("CHUNK_SIZE must be positive")
        if self.chunk_index >= self.total_chunks:
            errors.append("CHUNK_INDEX must be less than TOTAL_CHUNKS")
        
        # Base64 data validation
        try:
            decoded_data = FileUtils.decode_base64(self.data)
            if len(decoded_data) != self.chunk_size:
                errors.append(f"Data size mismatch: expected {self.chunk_size}, got {len(decoded_data)}")
        except Exception as e:
            errors.append(f"Invalid base64 data: {e}")
        
        # Token validation
        token_validator = TokenValidator()
        if not token_validator.validate_token_format(self.token):
            errors.append("Invalid token format")
        
        # Check token scope
        try:
            scope = token_validator.extract_scope(self.token)
            if scope != 'file':
                errors.append(f"Invalid token scope: expected 'file', got '{scope}'")
        except Exception:
            errors.append("Could not extract token scope")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }


@dataclass
class FileReceivedMessage:
    """FILE_RECEIVED message structure."""
    from_user: str
    to_user: str
    fileid: str
    status: str
    timestamp: int
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format for transmission."""
        return {
            'TYPE': 'FILE_RECEIVED',
            'FROM': self.from_user,
            'TO': self.to_user,
            'FILEID': self.fileid,
            'STATUS': self.status,
            'TIMESTAMP': str(self.timestamp)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'FileReceivedMessage':
        """Create FileReceivedMessage from dictionary."""
        return cls(
            from_user=data['FROM'],
            to_user=data['TO'],
            fileid=data['FILEID'],
            status=data['STATUS'],
            timestamp=int(data['TIMESTAMP'])
        )
    
    def validate(self) -> Dict[str, Any]:
        """Validate FILE_RECEIVED message."""
        errors = []
        
        # Required fields validation
        if not self.from_user:
            errors.append("FROM field is required")
        if not self.to_user:
            errors.append("TO field is required")
        if not self.fileid:
            errors.append("FILEID field is required")
        if not self.status:
            errors.append("STATUS field is required")
        
        # Status validation
        valid_statuses = ['COMPLETE', 'FAILED', 'CANCELLED']
        if self.status not in valid_statuses:
            errors.append(f"Invalid status: {self.status} (must be one of {valid_statuses})")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }


@dataclass
class ProfileMessage:
    """PROFILE message structure with avatar support."""
    user_id: str
    display_name: str
    status: str
    avatar_type: Optional[str] = None
    avatar_encoding: Optional[str] = None
    avatar_data: Optional[str] = None
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format for transmission."""
        data = {
            'TYPE': 'PROFILE',
            'USER_ID': self.user_id,
            'DISPLAY_NAME': self.display_name,
            'STATUS': self.status
        }
        
        # Add avatar fields if present
        if self.avatar_type:
            data['AVATAR_TYPE'] = self.avatar_type
        if self.avatar_encoding:
            data['AVATAR_ENCODING'] = self.avatar_encoding
        if self.avatar_data:
            data['AVATAR_DATA'] = self.avatar_data
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'ProfileMessage':
        """Create ProfileMessage from dictionary."""
        return cls(
            user_id=data['USER_ID'],
            display_name=data['DISPLAY_NAME'],
            status=data['STATUS'],
            avatar_type=data.get('AVATAR_TYPE'),
            avatar_encoding=data.get('AVATAR_ENCODING'),
            avatar_data=data.get('AVATAR_DATA')
        )
    
    def validate(self) -> Dict[str, Any]:
        """Validate PROFILE message."""
        errors = []
        
        # Required fields validation
        if not self.user_id:
            errors.append("USER_ID field is required")
        if not self.display_name:
            errors.append("DISPLAY_NAME field is required")
        if not self.status:
            errors.append("STATUS field is required")
        
        # Avatar validation (if present)
        has_avatar_fields = any([self.avatar_type, self.avatar_encoding, self.avatar_data])
        
        if has_avatar_fields:
            # If any avatar field is present, all must be present
            if not all([self.avatar_type, self.avatar_encoding, self.avatar_data]):
                errors.append("All avatar fields (AVATAR_TYPE, AVATAR_ENCODING, AVATAR_DATA) must be present together")
            else:
                # Validate avatar encoding
                if self.avatar_encoding.lower() != 'base64':
                    errors.append(f"Unsupported avatar encoding: {self.avatar_encoding}")
                
                # Validate avatar type
                if self.avatar_type not in FileUtils.SUPPORTED_AVATAR_FORMATS:
                    errors.append(f"Unsupported avatar type: {self.avatar_type}")
                
                # Validate avatar data
                try:
                    decoded_data = FileUtils.decode_base64(self.avatar_data)
                    if len(decoded_data) > FileUtils.MAX_AVATAR_SIZE:
                        errors.append(f"Avatar too large: {len(decoded_data)} bytes (max: {FileUtils.MAX_AVATAR_SIZE})")
                    
                    if not FileUtils.validate_avatar_image(decoded_data, self.avatar_type):
                        errors.append("Invalid avatar image format")
                        
                except Exception as e:
                    errors.append(f"Invalid avatar data: {e}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'has_avatar': has_avatar_fields and len(errors) == 0
        }


class FileMessageFactory:
    """Factory class for creating file transfer messages."""
    
    @staticmethod
    def create_file_offer(from_user: str, to_user: str, filename: str, 
                         filesize: int, filetype: str, fileid: str, 
                         description: str, token: str) -> FileOfferMessage:
        """Create a FILE_OFFER message."""
        return FileOfferMessage(
            from_user=from_user,
            to_user=to_user,
            filename=filename,
            filesize=filesize,
            filetype=filetype,
            fileid=fileid,
            description=description,
            timestamp=int(time.time()),
            token=token
        )
    
    @staticmethod
    def create_file_chunk(from_user: str, to_user: str, fileid: str,
                         chunk_index: int, total_chunks: int, chunk_size: int,
                         token: str, data: str) -> FileChunkMessage:
        """Create a FILE_CHUNK message."""
        return FileChunkMessage(
            from_user=from_user,
            to_user=to_user,
            fileid=fileid,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            chunk_size=chunk_size,
            token=token,
            data=data
        )
    
    @staticmethod
    def create_file_received(from_user: str, to_user: str, fileid: str,
                           status: str) -> FileReceivedMessage:
        """Create a FILE_RECEIVED message."""
        return FileReceivedMessage(
            from_user=from_user,
            to_user=to_user,
            fileid=fileid,
            status=status,
            timestamp=int(time.time())
        )
    
    @staticmethod
    def create_profile_with_avatar(user_id: str, display_name: str, status: str,
                                  avatar_type: Optional[str] = None,
                                  avatar_encoding: Optional[str] = None,
                                  avatar_data: Optional[str] = None) -> ProfileMessage:
        """Create a PROFILE message with optional avatar."""
        return ProfileMessage(
            user_id=user_id,
            display_name=display_name,
            status=status,
            avatar_type=avatar_type,
            avatar_encoding=avatar_encoding,
            avatar_data=avatar_data
        )
    
    @staticmethod
    def parse_message(message_data: Dict[str, str]):
        """
        Parse a message dictionary into appropriate message object.
        
        Args:
            message_data: Dictionary containing message fields
            
        Returns:
            Appropriate message object or None if invalid
        """
        message_type = message_data.get('TYPE')
        
        try:
            if message_type == 'FILE_OFFER':
                return FileOfferMessage.from_dict(message_data)
            elif message_type == 'FILE_CHUNK':
                return FileChunkMessage.from_dict(message_data)
            elif message_type == 'FILE_RECEIVED':
                return FileReceivedMessage.from_dict(message_data)
            elif message_type == 'PROFILE':
                return ProfileMessage.from_dict(message_data)
            else:
                return None
        except (KeyError, ValueError) as e:
            print(f"Error parsing {message_type} message: {e}")
            return None
    
    @staticmethod
    def validate_message(message) -> Dict[str, Any]:
        """
        Validate any file transfer message.
        
        Args:
            message: Message object to validate
            
        Returns:
            Validation result dictionary
        """
        if hasattr(message, 'validate'):
            return message.validate()
        else:
            return {'valid': False, 'errors': ['Unknown message type']}


class FileMessageValidator:
    """Validator for file transfer messages."""
    
    def __init__(self, token_validator: Optional[TokenValidator] = None):
        """
        Initialize validator.
        
        Args:
            token_validator: Token validator instance
        """
        self.token_validator = token_validator or TokenValidator()
    
    def validate_file_offer(self, message: FileOfferMessage, 
                           sender_ip: str) -> Dict[str, Any]:
        """
        Comprehensive validation of FILE_OFFER message.
        
        Args:
            message: FileOfferMessage to validate
            sender_ip: IP address of sender
            
        Returns:
            Validation result with detailed information
        """
        # Basic message validation
        basic_validation = message.validate()
        if not basic_validation['valid']:
            return basic_validation
        
        errors = []
        warnings = []
        
        # Validate sender IP matches FROM field
        expected_ip = message.from_user.split('@')[-1]
        if sender_ip != expected_ip:
            errors.append(f"Sender IP mismatch: expected {expected_ip}, got {sender_ip}")
        
        # Token validation with expiration and scope
        try:
            if not self.token_validator.is_token_valid(message.token, 'file'):
                errors.append("Token is invalid or expired")
        except Exception as e:
            errors.append(f"Token validation error: {e}")
        
        # File size warnings
        if message.filesize > 100 * 1024 * 1024:  # 100MB
            warnings.append(f"Large file size: {FileUtils.format_file_size(message.filesize)}")
        
        # Filename validation
        sanitized_filename = FileUtils.sanitize_filename(message.filename)
        if sanitized_filename != message.filename:
            warnings.append(f"Filename will be sanitized: {sanitized_filename}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'sanitized_filename': sanitized_filename
        }
    
    def validate_file_chunk(self, message: FileChunkMessage,
                           sender_ip: str, expected_fileid: str) -> Dict[str, Any]:
        """
        Comprehensive validation of FILE_CHUNK message.
        
        Args:
            message: FileChunkMessage to validate
            sender_ip: IP address of sender
            expected_fileid: Expected file ID for this transfer
            
        Returns:
            Validation result with detailed information
        """
        # Basic message validation
        basic_validation = message.validate()
        if not basic_validation['valid']:
            return basic_validation
        
        errors = []
        warnings = []
        
        # Validate sender IP matches FROM field
        expected_ip = message.from_user.split('@')[-1]
        if sender_ip != expected_ip:
            errors.append(f"Sender IP mismatch: expected {expected_ip}, got {sender_ip}")
        
        # Validate file ID matches expected
        if message.fileid != expected_fileid:
            errors.append(f"File ID mismatch: expected {expected_fileid}, got {message.fileid}")
        
        # Token validation
        try:
            if not self.token_validator.is_token_valid(message.token, 'file'):
                errors.append("Token is invalid or expired")
        except Exception as e:
            errors.append(f"Token validation error: {e}")
        
        # Chunk size validation
        if message.chunk_size > FileUtils.MAX_CHUNK_SIZE:
            errors.append(f"Chunk size too large: {message.chunk_size} (max: {FileUtils.MAX_CHUNK_SIZE})")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def validate_profile_with_avatar(self, message: ProfileMessage,
                                   sender_ip: str) -> Dict[str, Any]:
        """
        Comprehensive validation of PROFILE message with avatar.
        
        Args:
            message: ProfileMessage to validate
            sender_ip: IP address of sender
            
        Returns:
            Validation result with detailed information
        """
        # Basic message validation
        basic_validation = message.validate()
        if not basic_validation['valid']:
            return basic_validation
        
        errors = []
        warnings = []
        
        # Validate sender IP matches USER_ID
        expected_ip = message.user_id.split('@')[-1]
        if sender_ip != expected_ip:
            errors.append(f"Sender IP mismatch: expected {expected_ip}, got {sender_ip}")
        
        # Avatar-specific validations
        if basic_validation.get('has_avatar'):
            try:
                decoded_data = FileUtils.decode_base64(message.avatar_data)
                
                # Additional avatar size check
                if len(decoded_data) > FileUtils.MAX_AVATAR_SIZE * 0.9:  # 90% of max
                    warnings.append(f"Avatar is close to size limit: {FileUtils.format_file_size(len(decoded_data))}")
                
                # Format-specific warnings
                if message.avatar_type == 'image/gif':
                    warnings.append("Animated GIFs may not display properly in all clients")
                
            except Exception as e:
                errors.append(f"Avatar data processing error: {e}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'has_avatar': basic_validation.get('has_avatar', False)
        }