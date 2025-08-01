"""
File chunking and reconstruction logic for LSNP file transfers.
Handles splitting files into base64-encoded chunks and reassembling them.
"""

import os
import base64
from typing import List, Dict, Optional, Tuple, Iterator
from dataclasses import dataclass
from pathlib import Path

from ....utils.file_utils import FileUtils


@dataclass
class FileChunk:
    """Represents a single file chunk."""
    index: int
    data: bytes
    size: int
    is_base64_encoded: bool = False
    
    @property
    def encoded_data(self) -> str:
        """Get base64 encoded data."""
        if self.is_base64_encoded:
            return self.data.decode('utf-8')
        return FileUtils.encode_base64(self.data)
    
    @property
    def decoded_data(self) -> bytes:
        """Get raw binary data."""
        if self.is_base64_encoded:
            return FileUtils.decode_base64(self.data.decode('utf-8'))
        return self.data


@dataclass
class ChunkedFile:
    """Represents a file split into chunks."""
    file_id: str
    filename: str
    total_size: int
    chunk_size: int
    total_chunks: int
    chunks: Dict[int, FileChunk]
    mime_type: str = "application/octet-stream"
    
    @property
    def is_complete(self) -> bool:
        """Check if all chunks are present."""
        return len(self.chunks) == self.total_chunks
    
    @property
    def missing_chunks(self) -> List[int]:
        """Get list of missing chunk indices."""
        return [i for i in range(self.total_chunks) if i not in self.chunks]
    
    @property
    def received_size(self) -> int:
        """Get total size of received chunks."""
        return sum(chunk.size for chunk in self.chunks.values())


class FileChunkManager:
    """Manages file chunking and reconstruction for LSNP transfers."""
    
    def __init__(self, default_chunk_size: int = 1024):
        """
        Initialize the chunk manager.
        
        Args:
            default_chunk_size: Default size for file chunks in bytes
        """
        self.default_chunk_size = default_chunk_size
        self.active_files: Dict[str, ChunkedFile] = {}
    
    def chunk_file(self, file_path: str, file_id: str, 
                   chunk_size: Optional[int] = None) -> ChunkedFile:
        """
        Split a file into chunks for transmission.
        
        Args:
            file_path: Path to the file to chunk
            file_id: Unique identifier for the file transfer
            chunk_size: Size of each chunk (uses default if None)
            
        Returns:
            ChunkedFile object containing all chunks
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is empty or chunk_size invalid
        """
        if not FileUtils.validate_file_path(file_path):
            raise FileNotFoundError(f"File not found or not readable: {file_path}")
        
        path = Path(file_path)
        file_size = path.stat().st_size
        
        if file_size == 0:
            raise ValueError("Cannot chunk empty file")
        
        if chunk_size is None:
            chunk_size = FileUtils.calculate_optimal_chunk_size(file_size)
        
        if chunk_size <= 0:
            raise ValueError("Chunk size must be positive")
        
        total_chunks = FileUtils.calculate_total_chunks(file_size, chunk_size)
        mime_type = FileUtils.get_mime_type(file_path)
        
        chunked_file = ChunkedFile(
            file_id=file_id,
            filename=path.name,
            total_size=file_size,
            chunk_size=chunk_size,
            total_chunks=total_chunks,
            chunks={},
            mime_type=mime_type
        )
        
        # Read and chunk the file
        with open(file_path, 'rb') as f:
            chunk_index = 0
            while True:
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break
                
                chunk = FileChunk(
                    index=chunk_index,
                    data=chunk_data,
                    size=len(chunk_data)
                )
                
                chunked_file.chunks[chunk_index] = chunk
                chunk_index += 1
        
        self.active_files[file_id] = chunked_file
        return chunked_file
    
    def get_chunk(self, file_id: str, chunk_index: int) -> Optional[FileChunk]:
        """
        Get a specific chunk from a chunked file.
        
        Args:
            file_id: File transfer identifier
            chunk_index: Index of the chunk to retrieve
            
        Returns:
            FileChunk object or None if not found
        """
        if file_id not in self.active_files:
            return None
        
        chunked_file = self.active_files[file_id]
        return chunked_file.chunks.get(chunk_index)
    
    def add_received_chunk(self, file_id: str, filename: str, total_size: int,
                          total_chunks: int, chunk_index: int, 
                          chunk_data: str, chunk_size: int,
                          mime_type: str = "application/octet-stream") -> bool:
        """
        Add a received chunk to a file being reconstructed.
        
        Args:
            file_id: File transfer identifier
            filename: Name of the file
            total_size: Total size of the complete file
            total_chunks: Total number of chunks expected
            chunk_index: Index of this chunk
            chunk_data: Base64 encoded chunk data
            chunk_size: Size of the chunk in bytes
            mime_type: MIME type of the file
            
        Returns:
            True if chunk was added successfully
            
        Raises:
            ValueError: If chunk data is invalid
        """
        # Create chunked file entry if it doesn't exist
        if file_id not in self.active_files:
            self.active_files[file_id] = ChunkedFile(
                file_id=file_id,
                filename=filename,
                total_size=total_size,
                chunk_size=chunk_size,  # This might vary per chunk
                total_chunks=total_chunks,
                chunks={},
                mime_type=mime_type
            )
        
        chunked_file = self.active_files[file_id]
        
        # Validate chunk index
        if chunk_index < 0 or chunk_index >= total_chunks:
            raise ValueError(f"Invalid chunk index: {chunk_index}")
        
        # Skip if chunk already exists
        if chunk_index in chunked_file.chunks:
            return True
        
        try:
            # Decode the chunk data
            decoded_data = FileUtils.decode_base64(chunk_data)
            
            # Validate chunk size
            if len(decoded_data) != chunk_size:
                raise ValueError(f"Chunk size mismatch: expected {chunk_size}, got {len(decoded_data)}")
            
            # Create and store the chunk
            chunk = FileChunk(
                index=chunk_index,
                data=decoded_data,
                size=chunk_size
            )
            
            chunked_file.chunks[chunk_index] = chunk
            return True
            
        except Exception as e:
            raise ValueError(f"Failed to process chunk {chunk_index}: {e}")
    
    def reconstruct_file(self, file_id: str, output_path: str) -> bool:
        """
        Reconstruct a complete file from received chunks.
        
        Args:
            file_id: File transfer identifier
            output_path: Path where to save the reconstructed file
            
        Returns:
            True if file was successfully reconstructed
            
        Raises:
            ValueError: If file is incomplete or chunks are invalid
            IOError: If unable to write to output path
        """
        if file_id not in self.active_files:
            raise ValueError(f"File ID not found: {file_id}")
        
        chunked_file = self.active_files[file_id]
        
        if not chunked_file.is_complete:
            missing = chunked_file.missing_chunks
            raise ValueError(f"File incomplete, missing chunks: {missing}")
        
        # Ensure output directory exists
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, 'wb') as f:
                # Write chunks in order
                for chunk_index in range(chunked_file.total_chunks):
                    chunk = chunked_file.chunks[chunk_index]
                    f.write(chunk.decoded_data)
            
            # Verify file size
            actual_size = Path(output_path).stat().st_size
            if actual_size != chunked_file.total_size:
                raise ValueError(f"Reconstructed file size mismatch: expected {chunked_file.total_size}, got {actual_size}")
            
            return True
            
        except IOError as e:
            raise IOError(f"Failed to write reconstructed file: {e}")
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, any]]:
        """
        Get information about a chunked file.
        
        Args:
            file_id: File transfer identifier
            
        Returns:
            Dictionary with file information or None if not found
        """
        if file_id not in self.active_files:
            return None
        
        chunked_file = self.active_files[file_id]
        
        return {
            'file_id': file_id,
            'filename': chunked_file.filename,
            'total_size': chunked_file.total_size,
            'chunk_size': chunked_file.chunk_size,
            'total_chunks': chunked_file.total_chunks,
            'received_chunks': len(chunked_file.chunks),
            'missing_chunks': chunked_file.missing_chunks,
            'received_size': chunked_file.received_size,
            'is_complete': chunked_file.is_complete,
            'mime_type': chunked_file.mime_type,
            'progress_percentage': (len(chunked_file.chunks) / chunked_file.total_chunks) * 100.0
        }
    
    def iter_chunks(self, file_id: str) -> Iterator[FileChunk]:
        """
        Iterate over chunks in order for a file.
        
        Args:
            file_id: File transfer identifier
            
        Yields:
            FileChunk objects in order
        """
        if file_id not in self.active_files:
            return
        
        chunked_file = self.active_files[file_id]
        for chunk_index in range(chunked_file.total_chunks):
            if chunk_index in chunked_file.chunks:
                yield chunked_file.chunks[chunk_index]
    
    def get_chunks_for_transmission(self, file_id: str) -> List[Tuple[int, str, int]]:
        """
        Get all chunks ready for transmission.
        
        Args:
            file_id: File transfer identifier
            
        Returns:
            List of tuples (chunk_index, base64_data, chunk_size)
        """
        if file_id not in self.active_files:
            return []
        
        chunked_file = self.active_files[file_id]
        chunks_data = []
        
        for chunk_index in range(chunked_file.total_chunks):
            if chunk_index in chunked_file.chunks:
                chunk = chunked_file.chunks[chunk_index]
                chunks_data.append((
                    chunk_index,
                    chunk.encoded_data,
                    chunk.size
                ))
        
        return chunks_data
    
    def cleanup_file(self, file_id: str):
        """
        Remove a file from active tracking.
        
        Args:
            file_id: File transfer identifier
        """
        if file_id in self.active_files:
            del self.active_files[file_id]
    
    def cleanup_all_files(self):
        """Remove all files from active tracking."""
        self.active_files.clear()
    
    def get_active_files(self) -> List[str]:
        """Get list of all active file IDs."""
        return list(self.active_files.keys())
    
    def validate_chunk_integrity(self, file_id: str) -> Dict[str, any]:
        """
        Validate integrity of received chunks.
        
        Args:
            file_id: File transfer identifier
            
        Returns:
            Dictionary with validation results
        """
        if file_id not in self.active_files:
            return {'error': 'File not found'}
        
        chunked_file = self.active_files[file_id]
        results = {
            'file_id': file_id,
            'total_chunks': chunked_file.total_chunks,
            'received_chunks': len(chunked_file.chunks),
            'missing_chunks': chunked_file.missing_chunks,
            'is_complete': chunked_file.is_complete,
            'size_validation': True,
            'sequence_validation': True
        }
        
        # Validate chunk sizes and sequence
        expected_size = chunked_file.received_size
        actual_size = 0
        
        for chunk_index, chunk in chunked_file.chunks.items():
            actual_size += chunk.size
            
            # Check if chunk index is in valid range
            if chunk_index < 0 or chunk_index >= chunked_file.total_chunks:
                results['sequence_validation'] = False
        
        # Check total size consistency
        if expected_size != actual_size:
            results['size_validation'] = False
        
        return results