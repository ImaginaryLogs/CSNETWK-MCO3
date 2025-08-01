"""
Unit tests for LSNP file transfer functionality.
Tests file chunking, reconstruction, avatar handling, and message processing.
"""

import unittest
import tempfile
import os
import base64
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.protocol.types.files.file_chunk_manager import FileChunkManager, FileChunk
from src.protocol.types.files.avatar_handler import AvatarHandler, Avatar
from src.protocol.types.files.file_transfer import FileTransferManager
from src.protocol.types.messages.file_messages import (
    FileOfferMessage, FileChunkMessage, FileReceivedMessage, 
    ProfileMessage, FileMessageFactory
)
from src.utils.file_utils import FileUtils
from src.utils.progress_tracker import ProgressTracker, TransferStatus


class TestFileUtils(unittest.TestCase):
    """Test file utility functions."""
    
    def test_base64_encoding_decoding(self):
        """Test base64 encoding and decoding."""
        test_data = b"Hello, LSNP!"
        encoded = FileUtils.encode_base64(test_data)
        decoded = FileUtils.decode_base64(encoded)
        
        self.assertEqual(test_data, decoded)
        self.assertIsInstance(encoded, str)
    
    def test_invalid_base64_decoding(self):
        """Test invalid base64 data handling."""
        with self.assertRaises(ValueError):
            FileUtils.decode_base64("invalid_base64!")
    
    def test_mime_type_detection(self):
        """Test MIME type detection."""
        self.assertEqual(FileUtils.get_mime_type("test.png"), "image/png")
        self.assertEqual(FileUtils.get_mime_type("test.jpg"), "image/jpeg")
        self.assertEqual(FileUtils.get_mime_type("test.txt"), "text/plain")
        self.assertEqual(FileUtils.get_mime_type("test.unknown"), "application/octet-stream")
    
    def test_avatar_validation(self):
        """Test avatar image validation."""
        # Valid PNG data (minimal PNG header)
        png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        self.assertTrue(FileUtils.validate_avatar_image(png_data, "image/png"))
        
        # Invalid MIME type
        self.assertFalse(FileUtils.validate_avatar_image(png_data, "text/plain"))
        
        # Too large
        large_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * (FileUtils.MAX_AVATAR_SIZE + 1)
        self.assertFalse(FileUtils.validate_avatar_image(large_data, "image/png"))
    
    def test_chunk_size_calculation(self):
        """Test optimal chunk size calculation."""
        # Small file
        chunk_size = FileUtils.calculate_optimal_chunk_size(1000)
        self.assertGreaterEqual(chunk_size, FileUtils.DEFAULT_CHUNK_SIZE)
        self.assertLessEqual(chunk_size, FileUtils.MAX_CHUNK_SIZE)
        
        # Large file
        chunk_size = FileUtils.calculate_optimal_chunk_size(1000000)
        self.assertLessEqual(chunk_size, FileUtils.MAX_CHUNK_SIZE)
    
    def test_filename_sanitization(self):
        """Test filename sanitization."""
        dangerous_name = "file<>:\"/\\|?*.txt"
        safe_name = FileUtils.sanitize_filename(dangerous_name)
        
        self.assertNotIn('<', safe_name)
        self.assertNotIn('>', safe_name)
        self.assertNotIn(':', safe_name)
        self.assertNotIn('"', safe_name)
        self.assertNotIn('/', safe_name)
        self.assertNotIn('\\', safe_name)
        self.assertNotIn('|', safe_name)
        self.assertNotIn('?', safe_name)
        self.assertNotIn('*', safe_name)
    
    def test_file_size_formatting(self):
        """Test file size formatting."""
        self.assertEqual(FileUtils.format_file_size(0), "0 B")
        self.assertEqual(FileUtils.format_file_size(1024), "1.0 KB")
        self.assertEqual(FileUtils.format_file_size(1048576), "1.0 MB")
        self.assertEqual(FileUtils.format_file_size(1073741824), "1.0 GB")


class TestProgressTracker(unittest.TestCase):
    """Test progress tracking functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tracker = ProgressTracker(max_retries=3, retry_delay=1.0)
    
    def test_start_transfer(self):
        """Test starting a new transfer."""
        progress = self.tracker.start_transfer("test_file", "test.txt", 1000, 10)
        
        self.assertEqual(progress.file_id, "test_file")
        self.assertEqual(progress.filename, "test.txt")
        self.assertEqual(progress.total_size, 1000)
        self.assertEqual(progress.total_chunks, 10)
        self.assertEqual(progress.status, TransferStatus.IN_PROGRESS)
        self.assertEqual(progress.received_chunks, 0)
    
    def test_receive_chunk(self):
        """Test receiving chunks."""
        self.tracker.start_transfer("test_file", "test.txt", 1000, 10)
        
        # Receive first chunk
        success = self.tracker.receive_chunk("test_file", 0, 100)
        self.assertTrue(success)
        
        progress = self.tracker.get_progress("test_file")
        self.assertEqual(progress.received_chunks, 1)
        self.assertEqual(progress.progress_percentage, 10.0)
        self.assertEqual(progress.bytes_received, 100)
    
    def test_complete_transfer(self):
        """Test completing a transfer."""
        self.tracker.start_transfer("test_file", "test.txt", 100, 1)
        
        # Receive all chunks
        self.tracker.receive_chunk("test_file", 0, 100)
        
        progress = self.tracker.get_progress("test_file")
        self.assertEqual(progress.status, TransferStatus.COMPLETED)
        self.assertEqual(progress.progress_percentage, 100.0)
    
    def test_missing_chunks(self):
        """Test missing chunk detection."""
        self.tracker.start_transfer("test_file", "test.txt", 300, 3)
        
        # Receive chunks 0 and 2, skip 1
        self.tracker.receive_chunk("test_file", 0, 100)
        self.tracker.receive_chunk("test_file", 2, 100)
        
        missing = self.tracker.get_missing_chunks("test_file")
        self.assertEqual(missing, [1])
    
    def test_retry_logic(self):
        """Test chunk retry logic."""
        self.tracker.start_transfer("test_file", "test.txt", 300, 3)
        
        # Mark chunk for retry
        self.tracker.mark_chunk_for_retry("test_file", 1)
        
        retry_chunks = self.tracker.get_chunks_needing_retry("test_file")
        self.assertEqual(retry_chunks, [0, 2])  # 1 was marked for retry, so excluded
        
        progress = self.tracker.get_progress("test_file")
        chunk = progress.chunks[1]
        self.assertEqual(chunk.retry_count, 1)


class TestFileChunkManager(unittest.TestCase):
    """Test file chunking and reconstruction."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.chunk_manager = FileChunkManager()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_file(self, content: str, filename: str = "test.txt") -> str:
        """Create a test file with given content."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path
    
    def test_chunk_small_file(self):
        """Test chunking a small file."""
        content = "Hello, LSNP! This is a test file."
        file_path = self.create_test_file(content)
        
        chunked_file = self.chunk_manager.chunk_file(file_path, "test_file", chunk_size=10)
        
        self.assertEqual(chunked_file.file_id, "test_file")
        self.assertEqual(chunked_file.filename, "test.txt")
        self.assertGreater(chunked_file.total_chunks, 1)
        self.assertTrue(chunked_file.is_complete)
    
    def test_chunk_and_reconstruct(self):
        """Test complete chunk and reconstruction cycle."""
        content = "This is a longer test file content that will be split into multiple chunks."
        file_path = self.create_test_file(content)
        
        # Chunk the file
        chunked_file = self.chunk_manager.chunk_file(file_path, "test_file", chunk_size=20)
        
        # Simulate receiving chunks
        for chunk_index, chunk in chunked_file.chunks.items():
            success = self.chunk_manager.add_received_chunk(
                "received_file", "received.txt", len(content.encode()),
                chunked_file.total_chunks, chunk_index, chunk.encoded_data,
                chunk.size, "text/plain"
            )
            self.assertTrue(success)
        
        # Reconstruct file
        output_path = os.path.join(self.temp_dir, "reconstructed.txt")
        success = self.chunk_manager.reconstruct_file("received_file", output_path)
        self.assertTrue(success)
        
        # Verify content
        with open(output_path, 'r') as f:
            reconstructed_content = f.read()
        
        self.assertEqual(content, reconstructed_content)
    
    def test_invalid_chunk_handling(self):
        """Test handling of invalid chunks."""
        # Try to add chunk for non-existent file
        success = self.chunk_manager.add_received_chunk(
            "nonexistent", "test.txt", 100, 5, 0, "aGVsbG8=", 5, "text/plain"
        )
        self.assertTrue(success)  # Should create new chunked file
        
        # Try to add invalid chunk index
        with self.assertRaises(ValueError):
            self.chunk_manager.add_received_chunk(
                "test_file", "test.txt", 100, 5, 10, "aGVsbG8=", 5, "text/plain"
            )
    
    def test_chunk_validation(self):
        """Test chunk validation."""
        content = "Test content"
        file_path = self.create_test_file(content)
        
        chunked_file = self.chunk_manager.chunk_file(file_path, "test_file")
        
        validation = self.chunk_manager.validate_chunk_integrity("test_file")
        self.assertTrue(validation['is_complete'])
        self.assertTrue(validation['size_validation'])
        self.assertTrue(validation['sequence_validation'])


class TestAvatarHandler(unittest.TestCase):
    """Test avatar handling functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.avatar_handler = AvatarHandler(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_image(self, format_type: str = "png") -> bytes:
        """Create a minimal test image."""
        if format_type == "png":
            # Minimal PNG header
            return b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        elif format_type == "jpg":
            # Minimal JPEG header
            return b'\xff\xd8\xff' + b'\x00' * 100
        else:
            return b'\x00' * 100
    
    def test_process_valid_avatar(self):
        """Test processing valid avatar data."""
        image_data = self.create_test_image("png")
        encoded_data = FileUtils.encode_base64(image_data)
        
        profile_data = {
            'AVATAR_TYPE': 'image/png',
            'AVATAR_ENCODING': 'base64',
            'AVATAR_DATA': encoded_data
        }
        
        avatar = self.avatar_handler.process_avatar_from_profile("user@192.168.1.10", profile_data)
        
        self.assertIsNotNone(avatar)
        self.assertEqual(avatar.user_id, "user@192.168.1.10")
        self.assertEqual(avatar.mime_type, "image/png")
        self.assertEqual(avatar.data, image_data)
        self.assertTrue(avatar.is_valid)
    
    def test_process_invalid_avatar(self):
        """Test processing invalid avatar data."""
        # Too large image
        large_image = b'\x89PNG\r\n\x1a\n' + b'\x00' * (FileUtils.MAX_AVATAR_SIZE + 1)
        encoded_data = FileUtils.encode_base64(large_image)
        
        profile_data = {
            'AVATAR_TYPE': 'image/png',
            'AVATAR_ENCODING': 'base64',
            'AVATAR_DATA': encoded_data
        }
        
        avatar = self.avatar_handler.process_avatar_from_profile("user@192.168.1.10", profile_data)
        self.assertIsNone(avatar)
    
    def test_missing_avatar_fields(self):
        """Test handling missing avatar fields."""
        profile_data = {
            'AVATAR_TYPE': 'image/png',
            # Missing AVATAR_ENCODING and AVATAR_DATA
        }
        
        avatar = self.avatar_handler.process_avatar_from_profile("user@192.168.1.10", profile_data)
        self.assertIsNone(avatar)
    
    def test_create_profile_fields(self):
        """Test creating profile fields from avatar."""
        image_data = self.create_test_image("png")
        encoded_data = FileUtils.encode_base64(image_data)
        
        profile_data = {
            'AVATAR_TYPE': 'image/png',
            'AVATAR_ENCODING': 'base64',
            'AVATAR_DATA': encoded_data
        }
        
        # Process avatar
        avatar = self.avatar_handler.process_avatar_from_profile("user@192.168.1.10", profile_data)
        self.assertIsNotNone(avatar)
        
        # Create profile fields
        fields = self.avatar_handler.create_profile_avatar_fields("user@192.168.1.10")
        
        self.assertEqual(fields['AVATAR_TYPE'], 'image/png')
        self.assertEqual(fields['AVATAR_ENCODING'], 'base64')
        self.assertEqual(fields['AVATAR_DATA'], encoded_data)
    
    def test_avatar_caching(self):
        """Test avatar caching functionality."""
        image_data = self.create_test_image("png")
        encoded_data = FileUtils.encode_base64(image_data)
        
        profile_data = {
            'AVATAR_TYPE': 'image/png',
            'AVATAR_ENCODING': 'base64',
            'AVATAR_DATA': encoded_data
        }
        
        # Process and cache avatar
        avatar = self.avatar_handler.process_avatar_from_profile("user@192.168.1.10", profile_data)
        self.assertIsNotNone(avatar)
        
        # Retrieve cached avatar
        cached_avatar = self.avatar_handler.get_avatar("user@192.168.1.10")
        self.assertIsNotNone(cached_avatar)
        self.assertEqual(cached_avatar.data, image_data)
        
        # Check cache stats
        stats = self.avatar_handler.get_cache_stats()
        self.assertEqual(stats['cached_avatars'], 1)


class TestFileMessages(unittest.TestCase):
    """Test file transfer message formats."""
    
    def test_file_offer_message(self):
        """Test FILE_OFFER message creation and validation."""
        message = FileMessageFactory.create_file_offer(
            "alice@192.168.1.10", "bob@192.168.1.11", "test.txt",
            1000, "text/plain", "file123", "Test file", "token123"
        )
        
        self.assertEqual(message.from_user, "alice@192.168.1.10")
        self.assertEqual(message.to_user, "bob@192.168.1.11")
        self.assertEqual(message.filename, "test.txt")
        self.assertEqual(message.filesize, 1000)
        
        # Test dictionary conversion
        message_dict = message.to_dict()
        self.assertEqual(message_dict['TYPE'], 'FILE_OFFER')
        self.assertEqual(message_dict['FROM'], "alice@192.168.1.10")
        
        # Test reconstruction from dictionary
        reconstructed = FileOfferMessage.from_dict(message_dict)
        self.assertEqual(reconstructed.filename, "test.txt")
    
    def test_file_chunk_message(self):
        """Test FILE_CHUNK message creation and validation."""
        test_data = b"Hello, chunk data!"
        encoded_data = FileUtils.encode_base64(test_data)
        
        message = FileMessageFactory.create_file_chunk(
            "alice@192.168.1.10", "bob@192.168.1.11", "file123",
            0, 5, len(test_data), "token123", encoded_data
        )
        
        self.assertEqual(message.chunk_index, 0)
        self.assertEqual(message.total_chunks, 5)
        self.assertEqual(message.chunk_size, len(test_data))
        self.assertEqual(message.data, encoded_data)
        
        # Test validation
        validation = message.validate()
        self.assertTrue(validation['valid'])
    
    def test_file_received_message(self):
        """Test FILE_RECEIVED message creation and validation."""
        message = FileMessageFactory.create_file_received(
            "bob@192.168.1.11", "alice@192.168.1.10", "file123", "COMPLETE"
        )
        
        self.assertEqual(message.from_user, "bob@192.168.1.11")
        self.assertEqual(message.to_user, "alice@192.168.1.10")
        self.assertEqual(message.fileid, "file123")
        self.assertEqual(message.status, "COMPLETE")
        
        # Test validation
        validation = message.validate()
        self.assertTrue(validation['valid'])
    
    def test_profile_message_with_avatar(self):
        """Test PROFILE message with avatar fields."""
        image_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        encoded_data = FileUtils.encode_base64(image_data)
        
        message = FileMessageFactory.create_profile_with_avatar(
            "user@192.168.1.10", "Test User", "Online",
            "image/png", "base64", encoded_data
        )
        
        self.assertEqual(message.user_id, "user@192.168.1.10")
        self.assertEqual(message.display_name, "Test User")
        self.assertEqual(message.avatar_type, "image/png")
        self.assertEqual(message.avatar_data, encoded_data)
        
        # Test validation
        validation = message.validate()
        self.assertTrue(validation['valid'])
        self.assertTrue(validation['has_avatar'])
    
    def test_message_factory_parsing(self):
        """Test message factory parsing functionality."""
        # Test FILE_OFFER parsing
        offer_data = {
            'TYPE': 'FILE_OFFER',
            'FROM': 'alice@192.168.1.10',
            'TO': 'bob@192.168.1.11',
            'FILENAME': 'test.txt',
            'FILESIZE': '1000',
            'FILETYPE': 'text/plain',
            'FILEID': 'file123',
            'DESCRIPTION': 'Test file',
            'TIMESTAMP': str(int(time.time())),
            'TOKEN': 'token123'
        }
        
        parsed = FileMessageFactory.parse_message(offer_data)
        self.assertIsInstance(parsed, FileOfferMessage)
        self.assertEqual(parsed.filename, 'test.txt')
        
        # Test invalid message type
        invalid_data = {'TYPE': 'INVALID_TYPE'}
        parsed = FileMessageFactory.parse_message(invalid_data)
        self.assertIsNone(parsed)


class TestFileTransferIntegration(unittest.TestCase):
    """Integration tests for file transfer functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.download_dir = os.path.join(self.temp_dir, "downloads")
        self.avatar_dir = os.path.join(self.temp_dir, "avatars")
        
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.avatar_dir, exist_ok=True)
        
        self.transfer_manager = FileTransferManager(
            "alice@192.168.1.10", self.download_dir, self.avatar_dir
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_file(self, content: str, filename: str = "test.txt") -> str:
        """Create a test file with given content."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path
    
    @patch('src.utils.tokens.TokenGenerator.generate_token')
    def test_complete_file_transfer_workflow(self, mock_token_gen):
        """Test complete file transfer workflow."""
        mock_token_gen.return_value = "test_token"
        
        # Create test file
        content = "This is a test file for transfer."
        file_path = self.create_test_file(content)
        
        # Offer file
        file_id = self.transfer_manager.offer_file("bob@192.168.1.11", file_path, "Test transfer")
        self.assertIsNotNone(file_id)
        
        # Get chunks for transmission
        chunks = self.transfer_manager.get_chunks_for_sending(file_id)
        self.assertGreater(len(chunks), 0)
        
        # Simulate receiving chunks on another transfer manager
        receiver = FileTransferManager("bob@192.168.1.11", self.download_dir, self.avatar_dir)
        
        # First, simulate file offer reception
        offer_message = {
            'TYPE': 'FILE_OFFER',
            'FROM': 'alice@192.168.1.10',
            'TO': 'bob@192.168.1.11',
            'FILENAME': 'test.txt',
            'FILESIZE': str(len(content.encode())),
            'FILETYPE': 'text/plain',
            'FILEID': file_id,
            'DESCRIPTION': 'Test transfer',
            'TIMESTAMP': str(int(time.time())),
            'TOKEN': 'test_token'
        }
        
        with patch.object(receiver.message_validator, 'validate_file_offer') as mock_validate:
            mock_validate.return_value = {'valid': True, 'sanitized_filename': 'test.txt'}
            success = receiver.handle_file_offer(offer_message, "192.168.1.10")
            self.assertTrue(success)
        
        # Accept the offer
        success = receiver.accept_file_offer(file_id)
        self.assertTrue(success)
        
        # Simulate receiving chunks
        with patch.object(receiver.message_validator, 'validate_file_chunk') as mock_validate_chunk:
            mock_validate_chunk.return_value = {'valid': True}
            
            for chunk_data in chunks:
                success = receiver.handle_file_chunk(chunk_data, "192.168.1.10")
                self.assertTrue(success)
        
        # Verify file was reconstructed
        transfer_info = receiver.get_transfer_info(file_id)
        self.assertIsNotNone(transfer_info)
        
        # Check if file exists in download directory
        expected_file = os.path.join(self.download_dir, "test.txt")
        if os.path.exists(expected_file):
            with open(expected_file, 'r') as f:
                reconstructed_content = f.read()
            self.assertEqual(content, reconstructed_content)


if __name__ == '__main__':
    unittest.main()