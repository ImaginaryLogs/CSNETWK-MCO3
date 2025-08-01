"""
High-level file transfer coordination for LSNP.
Manages active transfers, handles user acceptance/rejection, and coordinates with main controller.
"""

import threading
import time
import base64
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum
from dataclasses import dataclass

from ..protocol.types.files.file_transfer import FileTransferManager, TransferDirection
from ..storage.file_storage import FileStorage
from ..ui.file_transfer_ui import FileTransferUI
from ..utils.progress_tracker import TransferStatus
from ..utils.file_utils import FileUtils


class FileManagerEvent(Enum):
    """Events emitted by the file manager."""
    OFFER_RECEIVED = "offer_received"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_REJECTED = "offer_rejected"
    TRANSFER_STARTED = "transfer_started"
    TRANSFER_PROGRESS = "transfer_progress"
    TRANSFER_COMPLETED = "transfer_completed"
    TRANSFER_FAILED = "transfer_failed"
    AVATAR_UPDATED = "avatar_updated"


@dataclass
class TransferSession:
    """Represents a complete file transfer session."""
    file_id: str
    direction: TransferDirection
    peer_user_id: str
    filename: str
    filesize: int
    status: TransferStatus
    progress_percentage: float = 0.0
    transfer_speed: float = 0.0
    eta_seconds: Optional[float] = None
    created_time: float = 0.0
    completed_time: Optional[float] = None
    local_file_path: Optional[str] = None
    error_message: Optional[str] = None


class FileManager:
    """High-level file transfer coordinator for LSNP."""
    
    def __init__(self, user_id: str, download_dir: str = "downloads",
                 upload_dir: str = "uploads", avatar_cache_dir: str = "avatars",
                 storage_dir: str = "lsnp_storage"):
        """
        Initialize file manager.
        
        Args:
            user_id: Current user's ID
            download_dir: Directory for downloaded files
            upload_dir: Directory to scan for uploadable files
            avatar_cache_dir: Directory for avatar cache
            storage_dir: Base directory for file storage
        """
        self.user_id = user_id
        self.download_dir = download_dir
        self.upload_dir = upload_dir
        
        # Initialize components
        self.transfer_manager = FileTransferManager(user_id, download_dir, avatar_cache_dir)
        self.file_storage = FileStorage(storage_dir)
        self.ui = FileTransferUI()
        
        # Event handling
        self.event_callbacks: Dict[FileManagerEvent, List[Callable]] = {
            event: [] for event in FileManagerEvent
        }
        
        # Transfer tracking
        self.pending_offers: Set[str] = set()  # File IDs waiting for user response
        self.active_sessions: Dict[str, TransferSession] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Setup transfer manager callbacks
        self._setup_transfer_callbacks()
        
        # Auto-cleanup timer
        self._cleanup_timer = None
        self._start_cleanup_timer()
    
    def _setup_transfer_callbacks(self):
        """Setup callbacks for the transfer manager."""
        self.transfer_manager.add_transfer_callback(self._handle_transfer_event)
    
    def _handle_transfer_event(self, event: str, data: Dict[str, Any]):
        """Handle events from the transfer manager."""
        with self._lock:
            if event == 'file_offer_received':
                self._handle_offer_received(data)
            elif event == 'file_offer_accepted':
                self._handle_offer_accepted(data)
            elif event == 'file_offer_rejected':
                self._handle_offer_rejected(data)
            elif event == 'chunk_received':
                self._handle_chunk_received(data)
            elif event == 'file_transfer_completed':
                self._handle_transfer_completed(data)
            elif event == 'file_transfer_failed':
                self._handle_transfer_failed(data)
            elif event == 'profile_received':
                self._handle_profile_received(data)
            elif event == 'error':
                self._handle_error(data)
    
    def _handle_offer_received(self, data: Dict[str, Any]):
        """Handle incoming file offer."""
        transfer = data['transfer']
        file_id = data['file_id']
        
        # Add to pending offers
        self.pending_offers.add(file_id)
        
        # Create session
        session = TransferSession(
            file_id=file_id,
            direction=TransferDirection.INCOMING,
            peer_user_id=transfer.from_user,
            filename=transfer.filename,
            filesize=transfer.filesize,
            status=TransferStatus.PENDING,
            created_time=transfer.created_time
        )
        
        self.active_sessions[file_id] = session
        
        # Show UI prompt (non-blocking)
        self.ui.show_file_offer_prompt(
            transfer.from_user,
            transfer.filename,
            transfer.filesize,
            transfer.description,
            lambda: self.accept_file_offer(file_id),
            lambda: self.reject_file_offer(file_id)
        )
        
        self._emit_event(FileManagerEvent.OFFER_RECEIVED, {
            'session': session,
            'validation': data.get('validation', {})
        })
    
    def _handle_offer_accepted(self, data: Dict[str, Any]):
        """Handle file offer acceptance."""
        file_id = data['file_id']
        transfer = data['transfer']
        
        if file_id in self.pending_offers:
            self.pending_offers.remove(file_id)
        
        if file_id in self.active_sessions:
            session = self.active_sessions[file_id]
            session.status = TransferStatus.IN_PROGRESS
        
        self._emit_event(FileManagerEvent.OFFER_ACCEPTED, {
            'file_id': file_id,
            'session': self.active_sessions.get(file_id)
        })
    
    def _handle_offer_rejected(self, data: Dict[str, Any]):
        """Handle file offer rejection."""
        file_id = data['file_id']
        
        if file_id in self.pending_offers:
            self.pending_offers.remove(file_id)
        
        if file_id in self.active_sessions:
            session = self.active_sessions[file_id]
            session.status = TransferStatus.CANCELLED
        
        self._emit_event(FileManagerEvent.OFFER_REJECTED, {
            'file_id': file_id,
            'session': self.active_sessions.get(file_id)
        })
    
    def _handle_chunk_received(self, data: Dict[str, Any]):
        """Handle chunk reception progress."""
        file_id = data['file_id']
        progress = data.get('progress')
        
        if file_id in self.active_sessions and progress:
            session = self.active_sessions[file_id]
            session.progress_percentage = progress.progress_percentage
            session.transfer_speed = progress.transfer_speed
            session.eta_seconds = progress.eta_seconds
            
            # Update UI progress
            self.ui.update_transfer_progress(file_id, progress.progress_percentage, 
                                           progress.transfer_speed, progress.eta_seconds)
        
        self._emit_event(FileManagerEvent.TRANSFER_PROGRESS, {
            'file_id': file_id,
            'session': self.active_sessions.get(file_id),
            'progress': progress
        })
    
    def _handle_transfer_completed(self, data: Dict[str, Any]):
        """Handle transfer completion."""
        file_id = data['file_id']
        transfer = data['transfer']
        file_path = data.get('file_path')
        
        if file_id in self.active_sessions:
            session = self.active_sessions[file_id]
            session.status = TransferStatus.COMPLETED
            session.progress_percentage = 100.0
            session.completed_time = time.time()
            session.local_file_path = file_path
        
        # Show completion notification
        self.ui.show_transfer_completed(transfer.filename, file_path)
        
        self._emit_event(FileManagerEvent.TRANSFER_COMPLETED, {
            'file_id': file_id,
            'session': self.active_sessions.get(file_id),
            'file_path': file_path
        })
    
    def _handle_transfer_failed(self, data: Dict[str, Any]):
        """Handle transfer failure."""
        file_id = data['file_id']
        reason = data.get('reason', 'Unknown error')
        
        if file_id in self.active_sessions:
            session = self.active_sessions[file_id]
            session.status = TransferStatus.FAILED
            session.error_message = reason
        
        # Show error notification
        self.ui.show_transfer_error(file_id, reason)
        
        self._emit_event(FileManagerEvent.TRANSFER_FAILED, {
            'file_id': file_id,
            'session': self.active_sessions.get(file_id),
            'error': reason
        })
    
    def _handle_profile_received(self, data: Dict[str, Any]):
        """Handle profile with avatar."""
        if data.get('avatar_info'):
            self._emit_event(FileManagerEvent.AVATAR_UPDATED, {
                'user_id': data['user_id'],
                'avatar_info': data['avatar_info']
            })
    
    def _handle_error(self, data: Dict[str, Any]):
        """Handle general errors."""
        message = data.get('message', 'Unknown error')
        self.ui.show_error_message(message)
    
    def _emit_event(self, event: FileManagerEvent, data: Dict[str, Any]):
        """Emit an event to registered callbacks."""
        for callback in self.event_callbacks[event]:
            try:
                callback(data)
            except Exception as e:
                print(f"Error in file manager callback: {e}")
    
    def add_event_callback(self, event: FileManagerEvent, callback: Callable):
        """Add callback for file manager events."""
        self.event_callbacks[event].append(callback)
    
    def remove_event_callback(self, event: FileManagerEvent, callback: Callable):
        """Remove event callback."""
        if callback in self.event_callbacks[event]:
            self.event_callbacks[event].remove(callback)
    
    def send_file(self, to_user: str, file_path: str, description: str = "") -> Optional[str]:
        """
        Send a file to another user.
        
        Args:
            to_user: Recipient user ID
            file_path: Path to file to send
            description: Optional description
            
        Returns:
            File ID if successful, None otherwise
        """
        with self._lock:
            # Validate file
            if not self.file_storage.get_file_path(file_path) and not FileUtils.validate_file_path(file_path):
                self.ui.show_error_message(f"File not found: {file_path}")
                return None
            
            # Create file offer
            file_id = self.transfer_manager.offer_file(to_user, file_path, description)
            
            if file_id:
                # Create session
                file_info = FileUtils.get_file_info(file_path)
                session = TransferSession(
                    file_id=file_id,
                    direction=TransferDirection.OUTGOING,
                    peer_user_id=to_user,
                    filename=file_info['filename'],
                    filesize=file_info['size'],
                    status=TransferStatus.PENDING,
                    created_time=time.time(),
                    local_file_path=file_path
                )
                
                self.active_sessions[file_id] = session
                
                self._emit_event(FileManagerEvent.TRANSFER_STARTED, {
                    'file_id': file_id,
                    'session': session
                })
            
            return file_id
    
    def accept_file_offer(self, file_id: str) -> bool:
        """
        Accept an incoming file offer.
        
        Args:
            file_id: File transfer ID
            
        Returns:
            True if accepted successfully
        """
        with self._lock:
            if file_id not in self.pending_offers:
                return False
            
            success = self.transfer_manager.accept_file_offer(file_id)
            # If pending_offers is a set or list:
            if success:
              self.pending_offers.discard(file_id)

            # OR if pending_offers is a dictionary:
            if success:
                self.pending_offers.discard(file_id)
            
            return success
    
    def reject_file_offer(self, file_id: str) -> bool:
        """
        Reject an incoming file offer.
        
        Args:
            file_id: File transfer ID
            
        Returns:
            True if rejected successfully
        """
        with self._lock:
            if file_id not in self.pending_offers:
                return False
            
            success = self.transfer_manager.reject_file_offer(file_id)
            if success:
                self.pending_offers.discard(file_id) 
            
            return success
    
    def cancel_transfer(self, file_id: str) -> bool:
        """
        Cancel an active transfer.
        
        Args:
            file_id: File transfer ID
            
        Returns:
            True if cancelled successfully
        """
        with self._lock:
            if file_id in self.active_sessions:
                session = self.active_sessions[file_id]
                session.status = TransferStatus.CANCELLED
                
                # Clean up
                self.transfer_manager.progress_tracker.cancel_transfer(file_id)
                self.transfer_manager.chunk_manager.cleanup_file(file_id)
                
                return True
            
            return False
    
    def get_pending_offers(self) -> List[TransferSession]:
        """Get list of pending file offers."""
        with self._lock:
            return [self.active_sessions[file_id] for file_id in self.pending_offers 
                   if file_id in self.active_sessions]
    
    def get_active_transfers(self) -> List[TransferSession]:
        """Get list of active transfers."""
        with self._lock:
            return [session for session in self.active_sessions.values() 
                   if session.status == TransferStatus.IN_PROGRESS]
    
    def get_completed_transfers(self) -> List[TransferSession]:
        """Get list of completed transfers."""
        with self._lock:
            return [session for session in self.active_sessions.values() 
                   if session.status == TransferStatus.COMPLETED]
    
    def get_transfer_session(self, file_id: str) -> Optional[TransferSession]:
        """Get transfer session by file ID."""
        with self._lock:
            return self.active_sessions.get(file_id)
    
    def get_all_sessions(self) -> List[TransferSession]:
        """Get all transfer sessions."""
        with self._lock:
            return list(self.active_sessions.values())
    
    def handle_incoming_message(self, message_data: Dict[str, str], sender_ip: str) -> bool:
        """
        Handle incoming file transfer related messages.
        
        Args:
            message_data: Message dictionary
            sender_ip: IP address of sender
            
        Returns:
            True if message was handled
        """
        message_type = message_data.get('TYPE')
        
        if message_type == 'FILE_OFFER':
            return self.transfer_manager.handle_file_offer(message_data, sender_ip)
        elif message_type == 'FILE_CHUNK':
            return self.transfer_manager.handle_file_chunk(message_data, sender_ip)
        elif message_type == 'FILE_RECEIVED':
            return self._handle_file_received_message(message_data, sender_ip)
        elif message_type == 'PROFILE':
            # Handle profile with potential avatar
            self.transfer_manager.handle_profile_with_avatar(message_data, sender_ip)
            return True
        
        return False
    
    def _handle_file_received_message(self, message_data: Dict[str, str], sender_ip: str) -> bool:
        """Handle FILE_RECEIVED message."""
        try:
            from ..protocol.types.messages.file_messages import FileReceivedMessage
            
            message = FileReceivedMessage.from_dict(message_data)
            validation = message.validate()
            
            if not validation['valid']:
                return False
            
            # Update session if we have one
            if message.fileid in self.active_sessions:
                session = self.active_sessions[message.fileid]
                if message.status == 'COMPLETE':
                    session.status = TransferStatus.COMPLETED
                    session.completed_time = time.time()
                elif message.status in ['FAILED', 'CANCELLED']:
                    session.status = TransferStatus.FAILED
                    session.error_message = f"Recipient reported: {message.status}"
            
            return True
            
        except Exception as e:
            print(f"Error handling FILE_RECEIVED message: {e}")
            return False
    
    def get_outgoing_chunks(self, file_id: str) -> List[Dict[str, Any]]:
        """
        Get chunks for an outgoing file transfer.
        
        Args:
            file_id: File transfer ID
            
        Returns:
            List of chunk message dictionaries
        """
        return self.transfer_manager.get_chunks_for_sending(file_id)
    
    def set_avatar(self, avatar_file_path: str) -> bool:
        """
        Set user's avatar from a file.
        
        Args:
            avatar_file_path: Path to avatar image file
            
        Returns:
            True if avatar was set successfully
        """
        try:
            avatar = self.transfer_manager.avatar_handler.load_avatar_from_file(
                self.user_id, avatar_file_path)
            
            if avatar:
                self._emit_event(FileManagerEvent.AVATAR_UPDATED, {
                    'user_id': self.user_id,
                    'avatar_info': self.transfer_manager.avatar_handler.get_avatar_info(self.user_id)
                })
                return True
            
            return False
            
        except Exception as e:
            self.ui.show_error_message(f"Error setting avatar: {e}")
            return False
    
    def get_avatar_info(self, user_id: str) -> Dict[str, Any]:
        """Get avatar information for a user."""
        return self.transfer_manager.avatar_handler.get_avatar_info(user_id)
    
    def create_profile_message(self, display_name, status):
      profile_msg = {
          'TYPE': 'PROFILE',
          'USER_ID': self.user_id,
          'DISPLAY_NAME': display_name,
          'STATUS': status
      }

      # Add full avatar fields (TYPE, ENCODING, DATA) if avatar exists
      avatar_fields = self.transfer_manager.avatar_handler.create_profile_avatar_fields(self.user_id)
      profile_msg.update(avatar_fields)

      return profile_msg




    
    def get_transfer_statistics(self) -> Dict[str, Any]:
        """Get comprehensive transfer statistics."""
        with self._lock:
            stats = {
                'total_sessions': len(self.active_sessions),
                'pending_offers': len(self.pending_offers),
                'active_transfers': len(self.get_active_transfers()),
                'completed_transfers': len(self.get_completed_transfers()),
                'failed_transfers': len([s for s in self.active_sessions.values() 
                                       if s.status == TransferStatus.FAILED]),
                'cancelled_transfers': len([s for s in self.active_sessions.values() 
                                          if s.status == TransferStatus.CANCELLED]),
                'incoming_transfers': len([s for s in self.active_sessions.values() 
                                         if s.direction == TransferDirection.INCOMING]),
                'outgoing_transfers': len([s for s in self.active_sessions.values() 
                                         if s.direction == TransferDirection.OUTGOING]),
                'total_bytes_transferred': sum(s.filesize for s in self.active_sessions.values() 
                                             if s.status == TransferStatus.COMPLETED),
                'storage_stats': self.file_storage.get_storage_stats(),
                'avatar_cache_stats': self.transfer_manager.avatar_handler.get_cache_stats()
            }
            
            # Format bytes
            stats['total_bytes_formatted'] = FileUtils.format_file_size(stats['total_bytes_transferred'])
            
            return stats
    
    def cleanup_old_transfers(self, max_age_hours: int = 24):
        """
        Clean up old transfer sessions and files.
        
        Args:
            max_age_hours: Maximum age for old transfers
        """
        with self._lock:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            # Clean up old sessions
            to_remove = []
            for file_id, session in self.active_sessions.items():
                if (session.status in [TransferStatus.COMPLETED, TransferStatus.FAILED, 
                                     TransferStatus.CANCELLED] and
                    current_time - session.created_time > max_age_seconds):
                    to_remove.append(file_id)
            
            for file_id in to_remove:
                del self.active_sessions[file_id]
            
            # Clean up transfer manager
            self.transfer_manager.cleanup_completed_transfers(max_age_hours)
            
            # Clean up file storage
            self.file_storage.cleanup_failed_transfers(max_age_hours)
            
            # Clean up old avatars
            self.transfer_manager.avatar_handler.cleanup_old_avatars(max_age_hours // 24)
    
    def _start_cleanup_timer(self):
        """Start periodic cleanup timer."""
        def cleanup_worker():
            try:
                self.cleanup_old_transfers(24)  # Clean up 24+ hour old transfers
            except Exception as e:
                print(f"Error in cleanup timer: {e}")
            finally:
                # Schedule next cleanup in 1 hour
                self._cleanup_timer = threading.Timer(3600, cleanup_worker)
                self._cleanup_timer.daemon = True
                self._cleanup_timer.start()
        
        self._cleanup_timer = threading.Timer(3600, cleanup_worker)  # Start after 1 hour
        self._cleanup_timer.daemon = True
        self._cleanup_timer.start()
    
    def shutdown(self):
        """Shutdown the file manager and clean up resources."""
        with self._lock:
            # Cancel cleanup timer
            if self._cleanup_timer:
                self._cleanup_timer.cancel()
            
            # Cancel all active transfers
            for file_id in list(self.active_sessions.keys()):
                self.cancel_transfer(file_id)
            
            # Clean up components
            self.transfer_manager.chunk_manager.cleanup_all_files()
            
            print("File manager shutdown complete")
    
    def export_transfer_log(self, file_path: str) -> bool:
        """
        Export transfer log to a file.
        
        Args:
            file_path: Path to export the log
            
        Returns:
            True if exported successfully
        """
        try:
            import json
            from pathlib import Path
            
            # Prepare export data
            export_data = {
                'export_time': time.time(),
                'user_id': self.user_id,
                'statistics': self.get_transfer_statistics(),
                'sessions': []
            }
            
            # Add session data
            for session in self.active_sessions.values():
                session_data = {
                    'file_id': session.file_id,
                    'direction': session.direction.value,
                    'peer_user_id': session.peer_user_id,
                    'filename': session.filename,
                    'filesize': session.filesize,
                    'status': session.status.value,
                    'progress_percentage': session.progress_percentage,
                    'created_time': session.created_time,
                    'completed_time': session.completed_time,
                    'error_message': session.error_message
                }
                export_data['sessions'].append(session_data)
            
            # Write to file
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error exporting transfer log: {e}")
            return False