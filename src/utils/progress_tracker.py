"""
Progress tracking for file transfers in LSNP.
Monitors chunk reception, calculates transfer speeds, and manages retry logic.
"""

import time
from typing import Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum


class TransferStatus(Enum):
    """Status of a file transfer."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ChunkInfo:
    """Information about a file chunk."""
    index: int
    size: int
    received: bool = False
    received_time: Optional[float] = None
    retry_count: int = 0
    last_retry_time: Optional[float] = None


@dataclass
class TransferProgress:
    """Progress information for a file transfer."""
    file_id: str
    filename: str
    total_size: int
    total_chunks: int
    received_chunks: int = 0
    status: TransferStatus = TransferStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    chunks: Dict[int, ChunkInfo] = field(default_factory=dict)
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_chunks == 0:
            return 0.0
        return (self.received_chunks / self.total_chunks) * 100.0
    
    @property
    def bytes_received(self) -> int:
        """Calculate total bytes received."""
        return sum(chunk.size for chunk in self.chunks.values() if chunk.received)
    
    @property
    def transfer_speed(self) -> float:
        """Calculate transfer speed in bytes per second."""
        if not self.start_time or self.bytes_received == 0:
            return 0.0
        
        elapsed_time = time.time() - self.start_time
        if elapsed_time <= 0:
            return 0.0
        
        return self.bytes_received / elapsed_time
    
    @property
    def eta_seconds(self) -> Optional[float]:
        """Calculate estimated time to completion in seconds."""
        speed = self.transfer_speed
        if speed <= 0:
            return None
        
        remaining_bytes = self.total_size - self.bytes_received
        return remaining_bytes / speed


class ProgressTracker:
    """Tracks progress of file transfers and manages retry logic."""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 2.0):
        """
        Initialize progress tracker.
        
        Args:
            max_retries: Maximum number of retries per chunk
            retry_delay: Delay between retries in seconds
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.transfers: Dict[str, TransferProgress] = {}
        self.progress_callbacks: List[Callable[[TransferProgress], None]] = []
    
    def add_progress_callback(self, callback: Callable[[TransferProgress], None]):
        """Add a callback function to be called on progress updates."""
        self.progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[TransferProgress], None]):
        """Remove a progress callback."""
        if callback in self.progress_callbacks:
            self.progress_callbacks.remove(callback)
    
    def _notify_progress_callbacks(self, progress: TransferProgress):
        """Notify all progress callbacks of an update."""
        for callback in self.progress_callbacks:
            try:
                callback(progress)
            except Exception as e:
                print(f"Error in progress callback: {e}")
    
    def start_transfer(self, file_id: str, filename: str, total_size: int, 
                      total_chunks: int) -> TransferProgress:
        """
        Start tracking a new file transfer.
        
        Args:
            file_id: Unique identifier for the transfer
            filename: Name of the file being transferred
            total_size: Total size of the file in bytes
            total_chunks: Total number of chunks expected
            
        Returns:
            TransferProgress object for the new transfer
        """
        progress = TransferProgress(
            file_id=file_id,
            filename=filename,
            total_size=total_size,
            total_chunks=total_chunks,
            start_time=time.time(),
            status=TransferStatus.IN_PROGRESS
        )
        
        # Initialize chunk info
        for i in range(total_chunks):
            progress.chunks[i] = ChunkInfo(index=i, size=0)
        
        self.transfers[file_id] = progress
        self._notify_progress_callbacks(progress)
        return progress
    
    def receive_chunk(self, file_id: str, chunk_index: int, chunk_size: int) -> bool:
        """
        Mark a chunk as received.
        
        Args:
            file_id: File transfer identifier
            chunk_index: Index of the received chunk
            chunk_size: Size of the chunk in bytes
            
        Returns:
            True if chunk was successfully recorded, False otherwise
        """
        if file_id not in self.transfers:
            return False
        
        progress = self.transfers[file_id]
        
        if chunk_index not in progress.chunks:
            return False
        
        chunk = progress.chunks[chunk_index]
        
        # Only count if not already received
        if not chunk.received:
            chunk.received = True
            chunk.received_time = time.time()
            chunk.size = chunk_size
            progress.received_chunks += 1
            
            # Check if transfer is complete
            if progress.received_chunks == progress.total_chunks:
                progress.status = TransferStatus.COMPLETED
                progress.end_time = time.time()
            
            self._notify_progress_callbacks(progress)
        
        return True
    
    def get_missing_chunks(self, file_id: str) -> List[int]:
        """
        Get list of missing chunk indices for a transfer.
        
        Args:
            file_id: File transfer identifier
            
        Returns:
            List of missing chunk indices
        """
        if file_id not in self.transfers:
            return []
        
        progress = self.transfers[file_id]
        return [index for index, chunk in progress.chunks.items() 
                if not chunk.received]
    
    def get_chunks_needing_retry(self, file_id: str) -> List[int]:
        """
        Get list of chunk indices that need to be retried.
        
        Args:
            file_id: File transfer identifier
            
        Returns:
            List of chunk indices that should be retried
        """
        if file_id not in self.transfers:
            return []
        
        progress = self.transfers[file_id]
        current_time = time.time()
        retry_chunks = []
        
        for index, chunk in progress.chunks.items():
            if (not chunk.received and 
                chunk.retry_count < self.max_retries and
                (chunk.last_retry_time is None or 
                 current_time - chunk.last_retry_time >= self.retry_delay)):
                retry_chunks.append(index)
        
        return retry_chunks
    
    def mark_chunk_for_retry(self, file_id: str, chunk_index: int):
        """
        Mark a chunk for retry.
        
        Args:
            file_id: File transfer identifier
            chunk_index: Index of the chunk to retry
        """
        if file_id not in self.transfers:
            return
        
        progress = self.transfers[file_id]
        if chunk_index in progress.chunks:
            chunk = progress.chunks[chunk_index]
            chunk.retry_count += 1
            chunk.last_retry_time = time.time()
    
    def fail_transfer(self, file_id: str, reason: str = "Unknown error"):
        """
        Mark a transfer as failed.
        
        Args:
            file_id: File transfer identifier
            reason: Reason for failure
        """
        if file_id not in self.transfers:
            return
        
        progress = self.transfers[file_id]
        progress.status = TransferStatus.FAILED
        progress.end_time = time.time()
        self._notify_progress_callbacks(progress)
    
    def cancel_transfer(self, file_id: str):
        """
        Cancel a transfer.
        
        Args:
            file_id: File transfer identifier
        """
        if file_id not in self.transfers:
            return
        
        progress = self.transfers[file_id]
        progress.status = TransferStatus.CANCELLED
        progress.end_time = time.time()
        self._notify_progress_callbacks(progress)
    
    def get_progress(self, file_id: str) -> Optional[TransferProgress]:
        """
        Get progress information for a transfer.
        
        Args:
            file_id: File transfer identifier
            
        Returns:
            TransferProgress object or None if not found
        """
        return self.transfers.get(file_id)
    
    def get_all_transfers(self) -> Dict[str, TransferProgress]:
        """Get all tracked transfers."""
        return self.transfers.copy()
    
    def cleanup_completed_transfers(self, max_age_seconds: float = 3600):
        """
        Clean up old completed transfers.
        
        Args:
            max_age_seconds: Maximum age for completed transfers
        """
        current_time = time.time()
        to_remove = []
        
        for file_id, progress in self.transfers.items():
            if (progress.status in [TransferStatus.COMPLETED, 
                                  TransferStatus.FAILED, 
                                  TransferStatus.CANCELLED] and
                progress.end_time and 
                current_time - progress.end_time > max_age_seconds):
                to_remove.append(file_id)
        
        for file_id in to_remove:
            del self.transfers[file_id]
    
    def get_transfer_summary(self, file_id: str) -> Dict[str, any]:
        """
        Get a summary of transfer statistics.
        
        Args:
            file_id: File transfer identifier
            
        Returns:
            Dictionary with transfer summary
        """
        progress = self.get_progress(file_id)
        if not progress:
            return {}
        
        duration = None
        if progress.start_time:
            end_time = progress.end_time or time.time()
            duration = end_time - progress.start_time
        
        return {
            'file_id': file_id,
            'filename': progress.filename,
            'status': progress.status.value,
            'progress_percentage': progress.progress_percentage,
            'bytes_received': progress.bytes_received,
            'total_size': progress.total_size,
            'transfer_speed': progress.transfer_speed,
            'eta_seconds': progress.eta_seconds,
            'duration': duration,
            'missing_chunks': len(self.get_missing_chunks(file_id)),
            'retry_chunks': len(self.get_chunks_needing_retry(file_id))
        }