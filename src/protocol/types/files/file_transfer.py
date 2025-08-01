"""
Main file transfer manager for LSNP.
Handles the complete file transfer workflow including offers, chunking, and reconstruction.
"""

import time
import threading
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass, field

from .file_chunk_manager import FileChunkManager, ChunkedFile
from .avatar_handler import AvatarHandler
from ..messages.file_messages import (
    FileOfferMessage, FileChunkMessage, FileReceivedMessage, 
    ProfileMessage, FileMessageFactory, FileMessageValidator
)
from ....utils.file_utils import FileUtils
from ....utils.progress_tracker import ProgressTracker, TransferStatus
from ....utils.tokens import TokenGenerator


class TransferDirection(Enum):
    """Direction of file transfer."""
    OUTGOING = "outgoing"
    INCOMING = "incoming"


@dataclass
class ActiveTransfer:
    """Represents an active file transfer."""
    file_id: str
    direction: TransferDirection
    from_user: str
    to_user: str
    filename: str
    filesize: int
    filetype: str
    description: str
    status: TransferStatus
    created_time: float
    accepted_time: Optional[float] = None
    completed_time: Optional[float] = None
    token: Optional[str] = None
    local_file_path: Optional[str] = None
    
    @property
    def is_pending_acceptance(self) -> bool:
        """Check if transfer is pending user acceptance."""
        return (self.direction == TransferDirection.INCOMING and 
                self.status == TransferStatus.PENDING)
    
    @property
    def is_active(self) -> bool:
        """Check if transfer is currently active."""
        return self.status == TransferStatus.IN_PROGRESS


class FileTransferManager:
    """Main manager for LSNP file transfers."""
    
    def __init__(self, user_id: str, download_dir: str = "downloads",
                 avatar_cache_dir: str = "avatars"):
        """
        Initialize file transfer manager.
        
        Args:
            user_id: Current user's ID
            download_dir: Directory for downloaded files
            avatar_cache_dir: Directory for avatar cache
        """
        self.user_id = user_id
        self.download_dir = download_dir
        
        # Initialize components
        self.chunk_manager = FileChunkManager()
        self.avatar_handler = AvatarHandler(avatar_cache_dir)
        self.progress_tracker = ProgressTracker()
        self.message_validator = FileMessageValidator()
        self.token_generator = TokenGenerator()
        
        # Transfer tracking
        self.active_transfers: Dict[str, ActiveTransfer] = {}
        self.transfer_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Create directories
        from pathlib import Path
        Path(download_dir).mkdir(parents=True, exist_ok=True)
    
    def add_transfer_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add callback for transfer events."""
        self.transfer_callbacks.append(callback)
    
    def remove_transfer_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Remove transfer callback."""
        if callback in self.transfer_callbacks:
            self.transfer_callbacks.remove(callback)
    
    def _notify_callbacks(self, event: str, data: Dict[str, Any]):
        """Notify all registered callbacks of an event."""
        for callback in self.transfer_callbacks:
            try:
                callback(event, data)
            except Exception as e:
                print(f"Error in transfer callback: {e}")
    
    def offer_file(self, to_user: str, file_path: str, 
                   description: str = "") -> Optional[str]:
        """
        Offer a file to another user.
        
        Args:
            to_user: Recipient user ID
            file_path: Path to file to send
            description: Optional description
            
        Returns:
            File ID if successful, None otherwise
        """
        with self._lock:
            try:
                # Validate file
                if not FileUtils.validate_file_path(file_path):
                    self._notify_callbacks('error', {
                        'message': f"File not found or not readable: {file_path}"
                    })
                    return None
                
                # Get file info
                file_info = FileUtils.get_file_info(file_path)
                if 'error' in file_info:
                    self._notify_callbacks('error', {
                        'message': f"Error reading file: {file_info['error']}"
                    })
                    return None
                
                # Generate file ID and token
                timestamp = time.time()  # float with subsecond precision
                file_id = FileUtils.generate_file_id(file_path, timestamp)
                token = self.token_generator.generate_token(self.user_id, 'file')
                
                # Create chunked file
                chunked_file = self.chunk_manager.chunk_file(file_path, file_id)
                
                # Create transfer record
                transfer = ActiveTransfer(
                    file_id=file_id,
                    direction=TransferDirection.OUTGOING,
                    from_user=self.user_id,
                    to_user=to_user,
                    filename=file_info['filename'],
                    filesize=file_info['size'],
                    filetype=file_info['mime_type'],
                    description=description,
                    status=TransferStatus.PENDING,
                    created_time=time.time(),
                    token=token,
                    local_file_path=file_path
                )
                
                self.active_transfers[file_id] = transfer
                
                # Create FILE_OFFER message
                offer_message = FileMessageFactory.create_file_offer(
                    self.user_id, to_user, file_info['filename'],
                    file_info['size'], file_info['mime_type'],
                    file_id, description, token
                )
                
                self._notify_callbacks('file_offer_created', {
                    'file_id': file_id,
                    'message': offer_message.to_dict(),
                    'transfer': transfer
                })
                
                return file_id
                
            except Exception as e:
                self._notify_callbacks('error', {
                    'message': f"Error offering file: {e}"
                })
                return None
    
    def handle_file_offer(self, message_data: Dict[str, str], 
                         sender_ip: str) -> bool:
        """
        Handle incoming FILE_OFFER message.
        
        Args:
            message_data: Message dictionary
            sender_ip: IP address of sender
            
        Returns:
            True if handled successfully
        """
        with self._lock:
            try:
                # Parse message
                offer_message = FileOfferMessage.from_dict(message_data)
                
                # Validate message
                validation = self.message_validator.validate_file_offer(
                    offer_message, sender_ip)
                if not validation['valid']:
                    self._notify_callbacks('error', {
                        'message': f"Invalid file offer: {validation['errors']}"
                    })
                    return False
                
                # Check if we're the intended recipient
                if offer_message.to_user != self.user_id:
                    return False
                
                # Check for duplicate offers
                if offer_message.fileid in self.active_transfers:
                    return True  # Ignore duplicate
                
                # Create transfer record
                transfer = ActiveTransfer(
                    file_id=offer_message.fileid,
                    direction=TransferDirection.INCOMING,
                    from_user=offer_message.from_user,
                    to_user=offer_message.to_user,
                    filename=validation.get('sanitized_filename', offer_message.filename),
                    filesize=offer_message.filesize,
                    filetype=offer_message.filetype,
                    description=offer_message.description,
                    status=TransferStatus.PENDING,
                    created_time=time.time()
                )
                
                self.active_transfers[offer_message.fileid] = transfer
                
                self._notify_callbacks('file_offer_received', {
                    'file_id': offer_message.fileid,
                    'transfer': transfer,
                    'validation': validation
                })
                
                return True
                
            except Exception as e:
                self._notify_callbacks('error', {
                    'message': f"Error handling file offer: {e}"
                })
                return False
    
    def accept_file_offer(self, file_id: str) -> bool:
        """
        Accept an incoming file offer.
        
        Args:
            file_id: ID of file transfer to accept
            
        Returns:
            True if accepted successfully
        """
        with self._lock:
            if file_id not in self.active_transfers:
                return False
            
            transfer = self.active_transfers[file_id]
            
            if not transfer.is_pending_acceptance:
                return False
            
            # Update transfer status
            transfer.status = TransferStatus.IN_PROGRESS
            transfer.accepted_time = time.time()
            
            # Start progress tracking
            self.progress_tracker.start_transfer(
                file_id, transfer.filename, transfer.filesize,
                FileUtils.calculate_total_chunks(transfer.filesize, 1024)
            )
            
            self._notify_callbacks('file_offer_accepted', {
                'file_id': file_id,
                'transfer': transfer
            })
            
            return True
    
    def reject_file_offer(self, file_id: str) -> bool:
        """
        Reject an incoming file offer.
        
        Args:
            file_id: ID of file transfer to reject
            
        Returns:
            True if rejected successfully
        """
        with self._lock:
            if file_id not in self.active_transfers:
                return False
            
            transfer = self.active_transfers[file_id]
            
            if not transfer.is_pending_acceptance:
                return False
            
            # Update transfer status
            transfer.status = TransferStatus.CANCELLED
            
            # Clean up
            self.chunk_manager.cleanup_file(file_id)
            del self.active_transfers[file_id]
            
            self._notify_callbacks('file_offer_rejected', {
                'file_id': file_id,
                'transfer': transfer
            })
            
            return True
    
    def handle_file_chunk(self, message_data: Dict[str, str],
                         sender_ip: str) -> bool:
        """
        Handle incoming FILE_CHUNK message.
        
        Args:
            message_data: Message dictionary
            sender_ip: IP address of sender
            
        Returns:
            True if handled successfully
        """
        with self._lock:
            try:
                # Parse message
                chunk_message = FileChunkMessage.from_dict(message_data)
                
                # Check if we have an active transfer for this file
                if chunk_message.fileid not in self.active_transfers:
                    return False
                
                transfer = self.active_transfers[chunk_message.fileid]
                
                # Validate message
                validation = self.message_validator.validate_file_chunk(
                    chunk_message, sender_ip, chunk_message.fileid)
                if not validation['valid']:
                    self._notify_callbacks('error', {
                        'message': f"Invalid file chunk: {validation['errors']}"
                    })
                    return False
                
                # Check if transfer is active
                if not transfer.is_active:
                    return False
                
                # Add chunk to manager
                success = self.chunk_manager.add_received_chunk(
                    chunk_message.fileid,
                    transfer.filename,
                    transfer.filesize,
                    chunk_message.total_chunks,
                    chunk_message.chunk_index,
                    chunk_message.data,
                    chunk_message.chunk_size,
                    transfer.filetype
                )
                
                if success:
                    # Update progress
                    self.progress_tracker.receive_chunk(
                        chunk_message.fileid,
                        chunk_message.chunk_index,
                        chunk_message.chunk_size
                    )
                    
                    # Check if transfer is complete
                    file_info = self.chunk_manager.get_file_info(chunk_message.fileid)
                    if file_info and file_info['is_complete']:
                        self._complete_file_transfer(chunk_message.fileid)
                    
                    self._notify_callbacks('chunk_received', {
                        'file_id': chunk_message.fileid,
                        'chunk_index': chunk_message.chunk_index,
                        'progress': self.progress_tracker.get_progress(chunk_message.fileid)
                    })
                
                return success
                
            except Exception as e:
                self._notify_callbacks('error', {
                    'message': f"Error handling file chunk: {e}"
                })
                return False
    
    def _complete_file_transfer(self, file_id: str):
        """Complete an incoming file transfer."""
        if file_id not in self.active_transfers:
            return
        
        transfer = self.active_transfers[file_id]
        
        try:
            # Reconstruct file
            from pathlib import Path
            output_path = Path(self.download_dir) / FileUtils.sanitize_filename(transfer.filename)
            
            # Handle filename conflicts
            counter = 1
            original_path = output_path
            while output_path.exists():
                name_stem = original_path.stem
                suffix = original_path.suffix
                output_path = original_path.parent / f"{name_stem}_{counter}{suffix}"
                counter += 1
            
            success = self.chunk_manager.reconstruct_file(file_id, str(output_path))
            
            if success:
                transfer.status = TransferStatus.COMPLETED
                transfer.completed_time = time.time()
                transfer.local_file_path = str(output_path)
                
                # Send FILE_RECEIVED message
                received_message = FileMessageFactory.create_file_received(
                    self.user_id, transfer.from_user, file_id, "COMPLETE"
                )
                
                self._notify_callbacks('file_transfer_completed', {
                    'file_id': file_id,
                    'transfer': transfer,
                    'file_path': str(output_path),
                    'message': received_message.to_dict()
                })
            else:
                self._fail_transfer(file_id, "Failed to reconstruct file")
                
        except Exception as e:
            self._fail_transfer(file_id, f"Error completing transfer: {e}")
    
    def _fail_transfer(self, file_id: str, reason: str):
        """Mark a transfer as failed."""
        if file_id in self.active_transfers:
            transfer = self.active_transfers[file_id]
            transfer.status = TransferStatus.FAILED
            
            self.progress_tracker.fail_transfer(file_id, reason)
            
            self._notify_callbacks('file_transfer_failed', {
                'file_id': file_id,
                'transfer': transfer,
                'reason': reason
            })
    
    def get_chunks_for_sending(self, file_id: str) -> List[Dict[str, Any]]:
        """
        Get chunks ready for sending.
        
        Args:
            file_id: File transfer ID
            
        Returns:
            List of chunk message dictionaries
        """
        with self._lock:
            if file_id not in self.active_transfers:
                return []
            
            transfer = self.active_transfers[file_id]
            if transfer.direction != TransferDirection.OUTGOING:
                return []
            
            chunks_data = self.chunk_manager.get_chunks_for_transmission(file_id)
            messages = []
            
            for chunk_index, base64_data, chunk_size in chunks_data:
                chunk_message = FileMessageFactory.create_file_chunk(
                    transfer.from_user,
                    transfer.to_user,
                    file_id,
                    chunk_index,
                    len(chunks_data),
                    chunk_size,
                    transfer.token,
                    base64_data
                )
                messages.append(chunk_message.to_dict())
            
            return messages
    
    def handle_profile_with_avatar(self, message_data: Dict[str, str],
                                  sender_ip: str) -> Optional[Dict[str, Any]]:
        """
        Handle PROFILE message with avatar data.
        
        Args:
            message_data: Message dictionary
            sender_ip: IP address of sender
            
        Returns:
            Avatar info if successful, None otherwise
        """
        try:
            # Parse message
            profile_message = ProfileMessage.from_dict(message_data)
            
            # Validate message
            validation = self.message_validator.validate_profile_with_avatar(
                profile_message, sender_ip)
            if not validation['valid']:
                self._notify_callbacks('error', {
                    'message': f"Invalid profile message: {validation['errors']}"
                })
                return None
            
            # Process avatar if present
            avatar_info = None
            if validation.get('has_avatar'):
                avatar = self.avatar_handler.process_avatar_from_profile(
                    profile_message.user_id, message_data)
                if avatar:
                    avatar_info = self.avatar_handler.get_avatar_info(profile_message.user_id)
            
            self._notify_callbacks('profile_received', {
                'user_id': profile_message.user_id,
                'display_name': profile_message.display_name,
                'status': profile_message.status,
                'avatar_info': avatar_info,
                'validation': validation
            })
            
            return avatar_info
            
        except Exception as e:
            self._notify_callbacks('error', {
                'message': f"Error handling profile: {e}"
            })
            return None
    
    def create_profile_message(self, display_name: str, status: str,
                              avatar_file_path: Optional[str] = None) -> Dict[str, str]:
        """
        Create a PROFILE message with optional avatar.
        
        Args:
            display_name: User's display name
            status: User's status message
            avatar_file_path: Path to avatar image file
            
        Returns:
            Dictionary containing profile message
        """
        avatar_fields = {}
        
        if avatar_file_path:
            avatar = self.avatar_handler.load_avatar_from_file(self.user_id, avatar_file_path)
            if avatar:
                avatar_fields = self.avatar_handler.create_profile_avatar_fields(self.user_id)
        
        profile_message = FileMessageFactory.create_profile_with_avatar(
            self.user_id, display_name, status,
            avatar_fields.get('AVATAR_TYPE'),
            avatar_fields.get('AVATAR_ENCODING'),
            avatar_fields.get('AVATAR_DATA')
        )
        
        return profile_message.to_dict()
    
    def get_transfer_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a transfer."""
        with self._lock:
            if file_id not in self.active_transfers:
                return None
            
            transfer = self.active_transfers[file_id]
            progress = self.progress_tracker.get_progress(file_id)
            
            return {
                'transfer': transfer,
                'progress': progress,
                'file_info': self.chunk_manager.get_file_info(file_id)
            }
    
    def get_all_transfers(self) -> List[Dict[str, Any]]:
        """Get information about all transfers."""
        with self._lock:
            transfers = []
            for file_id in self.active_transfers:
                info = self.get_transfer_info(file_id)
                if info:
                    transfers.append(info)
            return transfers
    
    def cleanup_completed_transfers(self, max_age_hours: int = 24):
        """Clean up old completed transfers."""
        with self._lock:
            current_time = time.time()
            to_remove = []
            
            for file_id, transfer in self.active_transfers.items():
                if (transfer.status in [TransferStatus.COMPLETED, 
                                      TransferStatus.FAILED, 
                                      TransferStatus.CANCELLED] and
                    current_time - transfer.created_time > max_age_hours * 3600):
                    to_remove.append(file_id)
            
            for file_id in to_remove:
                self.chunk_manager.cleanup_file(file_id)
                del self.active_transfers[file_id]
            
            # Clean up progress tracker
            self.progress_tracker.cleanup_completed_transfers(max_age_hours * 3600)