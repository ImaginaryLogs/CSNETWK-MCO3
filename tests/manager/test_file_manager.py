"""
Integration tests for LSNP file manager.
Tests complete file transfer workflows, concurrent transfers, and UI integration.
"""

import unittest
import tempfile
import os
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.manager.file_manager import FileManager, FileManagerEvent, TransferSession
from src.protocol.types.files.file_transfer import TransferDirection
from src.utils.progress_tracker import TransferStatus
from src.utils.file_utils import FileUtils


class TestFileManager(unittest.TestCase):
    """Test file manager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.download_dir = os.path.join(self.temp_dir, "downloads")
        self.upload_dir = os.path.join(self.temp_dir, "uploads")
        self.avatar_dir = os.path.join(self.temp_dir, "avatars")
        self.storage_dir = os.path.join(self.temp_dir, "storage")
        
        # Create directories
        for directory in [self.download_dir, self.upload_dir, self.avatar_dir, self.storage_dir]:
            os.makedirs(directory, exist_ok=True)
        
        self.file_manager = FileManager(
            "alice@192.168.1.10",
            self.download_dir,
            self.upload_dir,
            self.avatar_dir,
            self.storage_dir
        )
        
        # Mock UI to avoid GUI dependencies
        self.file_manager.ui = Mock()
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.file_manager.shutdown()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_file(self, content: str, filename: str = "test.txt") -> str:
        """Create a test file with given content."""
        file_path = os.path.join(self.upload_dir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path
    
    def create_test_image(self, filename: str = "test.png") -> str:
        """Create a test image file."""
        file_path = os.path.join(self.upload_dir, filename)
        # Create minimal PNG
        png_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        with open(file_path, 'wb') as f:
            f.write(png_data)
        return file_path


class TestFileManagerBasicOperations(TestFileManager):
    """Test basic file manager operations."""
    
    @patch('src.utils.tokens.TokenGenerator.generate_token')
    def test_send_file(self, mock_token_gen):
        """Test sending a file."""
        mock_token_gen.return_value = "test_token"
        
        # Create test file
        content = "Hello, this is a test file!"
        file_path = self.create_test_file(content)
        
        # Send file
        file_id = self.file_manager.send_file("bob@192.168.1.11", file_path, "Test file")
        
        self.assertIsNotNone(file_id)
        
        # Check session was created
        session = self.file_manager.get_transfer_session(file_id)
        self.assertIsNotNone(session)
        self.assertEqual(session.direction, TransferDirection.OUTGOING)
        self.assertEqual(session.peer_user_id, "bob@192.168.1.11")
        self.assertEqual(session.filename, "test.txt")
        self.assertEqual(session.status, TransferStatus.PENDING)
    
    def test_send_nonexistent_file(self):
        """Test sending a file that doesn't exist."""
        file_id = self.file_manager.send_file("bob@192.168.1.11", "/nonexistent/file.txt")
        
        self.assertIsNone(file_id)
        self.file_manager.ui.show_error_message.assert_called()
    
    def test_get_outgoing_chunks(self):
        """Test getting chunks for outgoing transfer."""
        # Create and send file
        content = "This is test content for chunking."
        file_path = self.create_test_file(content)
        
        with patch('src.utils.tokens.TokenGenerator.generate_token', return_value="test_token"):
            file_id = self.file_manager.send_file("bob@192.168.1.11", file_path)
        
        self.assertIsNotNone(file_id)
        
        # Get chunks
        chunks = self.file_manager.get_outgoing_chunks(file_id)
        
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            self.assertEqual(chunk['TYPE'], 'FILE_CHUNK')
            self.assertEqual(chunk['FROM'], 'alice@192.168.1.10')
            self.assertEqual(chunk['TO'], 'bob@192.168.1.11')
            self.assertEqual(chunk['FILEID'], file_id)


class TestFileManagerIncomingTransfers(TestFileManager):
    """Test incoming file transfer handling."""
    
    def test_handle_file_offer(self):
        """Test handling incoming file offer."""
        offer_message = {
            'TYPE': 'FILE_OFFER',
            'FROM': 'bob@192.168.1.11',
            'TO': 'alice@192.168.1.10',
            'FILENAME': 'received_file.txt',
            'FILESIZE': '1000',
            'FILETYPE': 'text/plain',
            'FILEID': 'file123',
            'DESCRIPTION': 'Test file from Bob',
            'TIMESTAMP': str(int(time.time())),
            'TOKEN': 'test_token'
        }
        
        # Mock validation to pass
        with patch.object(self.file_manager.transfer_manager.message_validator, 'validate_file_offer') as mock_validate:
            mock_validate.return_value = {'valid': True, 'sanitized_filename': 'received_file.txt'}
            
            success = self.file_manager.handle_incoming_message(offer_message, "192.168.1.11")
        
        self.assertTrue(success)
        
        # Check that UI prompt was shown
        self.file_manager.ui.show_file_offer_prompt.assert_called_once()
        
        # Check pending offers
        pending = self.file_manager.get_pending_offers()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].file_id, 'file123')
        self.assertEqual(pending[0].peer_user_id, 'bob@192.168.1.11')
    
    def test_accept_file_offer(self):
        """Test accepting a file offer."""
        # First create a pending offer
        offer_message = {
            'TYPE': 'FILE_OFFER',
            'FROM': 'bob@192.168.1.11',
            'TO': 'alice@192.168.1.10',
            'FILENAME': 'received_file.txt',
            'FILESIZE': '1000',
            'FILETYPE': 'text/plain',
            'FILEID': 'file123',
            'DESCRIPTION': 'Test file',
            'TIMESTAMP': str(int(time.time())),
            'TOKEN': 'test_token'
        }
        
        with patch.object(self.file_manager.transfer_manager.message_validator, 'validate_file_offer') as mock_validate:
            mock_validate.return_value = {'valid': True, 'sanitized_filename': 'received_file.txt'}
            self.file_manager.handle_incoming_message(offer_message, "192.168.1.11")
        
        # Accept the offer
        success = self.file_manager.accept_file_offer('file123')
        self.assertTrue(success)
        
        # Check that offer is no longer pending
        pending = self.file_manager.get_pending_offers()
        self.assertEqual(len(pending), 0)
        
        # Check that transfer is now active
        active = self.file_manager.get_active_transfers()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].status, TransferStatus.IN_PROGRESS)
    
    def test_reject_file_offer(self):
        """Test rejecting a file offer."""
        # Create pending offer
        offer_message = {
            'TYPE': 'FILE_OFFER',
            'FROM': 'bob@192.168.1.11',
            'TO': 'alice@192.168.1.10',
            'FILENAME': 'received_file.txt',
            'FILESIZE': '1000',
            'FILETYPE': 'text/plain',
            'FILEID': 'file123',
            'DESCRIPTION': 'Test file',
            'TIMESTAMP': str(int(time.time())),
            'TOKEN': 'test_token'
        }
        
        with patch.object(self.file_manager.transfer_manager.message_validator, 'validate_file_offer') as mock_validate:
            mock_validate.return_value = {'valid': True, 'sanitized_filename': 'received_file.txt'}
            self.file_manager.handle_incoming_message(offer_message, "192.168.1.11")
        
        # Reject the offer
        success = self.file_manager.reject_file_offer('file123')
        self.assertTrue(success)
        
        # Check that offer is no longer pending
        pending = self.file_manager.get_pending_offers()
        self.assertEqual(len(pending), 0)
        
        # Check session status
        session = self.file_manager.get_transfer_session('file123')
        self.assertEqual(session.status, TransferStatus.CANCELLED)
    
    def test_handle_file_chunks(self):
        """Test handling incoming file chunks."""
        # First create accepted transfer
        offer_message = {
            'TYPE': 'FILE_OFFER',
            'FROM': 'bob@192.168.1.11',
            'TO': 'alice@192.168.1.10',
            'FILENAME': 'received_file.txt',
            'FILESIZE': '20',
            'FILETYPE': 'text/plain',
            'FILEID': 'file123',
            'DESCRIPTION': 'Test file',
            'TIMESTAMP': str(int(time.time())),
            'TOKEN': 'test_token'
        }
        
        with patch.object(self.file_manager.transfer_manager.message_validator, 'validate_file_offer') as mock_validate:
            mock_validate.return_value = {'valid': True, 'sanitized_filename': 'received_file.txt'}
            self.file_manager.handle_incoming_message(offer_message, "192.168.1.11")
        
        self.file_manager.accept_file_offer('file123')
        
        # Send chunk
        test_data = b"Hello, LSNP chunks!"
        encoded_data = FileUtils.encode_base64(test_data)
        
        chunk_message = {
            'TYPE': 'FILE_CHUNK',
            'FROM': 'bob@192.168.1.11',
            'TO': 'alice@192.168.1.10',
            'FILEID': 'file123',
            'CHUNK_INDEX': '0',
            'TOTAL_CHUNKS': '1',
            'CHUNK_SIZE': str(len(test_data)),
            'TOKEN': 'test_token',
            'DATA': encoded_data
        }
        
        with patch.object(self.file_manager.transfer_manager.message_validator, 'validate_file_chunk') as mock_validate:
            mock_validate.return_value = {'valid': True}
            success = self.file_manager.handle_incoming_message(chunk_message, "192.168.1.11")
        
        self.assertTrue(success)
        
        # Check progress was updated
        session = self.file_manager.get_transfer_session('file123')
        self.assertGreater(session.progress_percentage, 0)


class TestFileManagerEvents(TestFileManager):
    """Test file manager event system."""
    
    def test_event_callbacks(self):
        """Test event callback system."""
        received_events = []
        
        def event_callback(data):
            received_events.append(data)
        
        # Add callback for offer received events
        self.file_manager.add_event_callback(FileManagerEvent.OFFER_RECEIVED, event_callback)
        
        # Trigger an event by handling file offer
        offer_message = {
            'TYPE': 'FILE_OFFER',
            'FROM': 'bob@192.168.1.11',
            'TO': 'alice@192.168.1.10',
            'FILENAME': 'test.txt',
            'FILESIZE': '1000',
            'FILETYPE': 'text/plain',
            'FILEID': 'file123',
            'DESCRIPTION': 'Test',
            'TIMESTAMP': str(int(time.time())),
            'TOKEN': 'test_token'
        }
        
        with patch.object(self.file_manager.transfer_manager.message_validator, 'validate_file_offer') as mock_validate:
            mock_validate.return_value = {'valid': True, 'sanitized_filename': 'test.txt'}
            self.file_manager.handle_incoming_message(offer_message, "192.168.1.11")
        
        # Check that callback was called
        self.assertEqual(len(received_events), 1)
        self.assertIn('session', received_events[0])
        
        # Remove callback
        self.file_manager.remove_event_callback(FileManagerEvent.OFFER_RECEIVED, event_callback)
        
        # Trigger another event - should not be received
        offer_message['FILEID'] = 'file124'
        with patch.object(self.file_manager.transfer_manager.message_validator, 'validate_file_offer') as mock_validate:
            mock_validate.return_value = {'valid': True, 'sanitized_filename': 'test.txt'}
            self.file_manager.handle_incoming_message(offer_message, "192.168.1.11")
        
        # Should still be 1 event
        self.assertEqual(len(received_events), 1)


class TestFileManagerAvatars(TestFileManager):
    """Test avatar functionality in file manager."""
    
    def test_set_avatar(self):
        """Test setting user avatar."""
        # Create test image
        image_path = self.create_test_image("avatar.png")
        
        success = self.file_manager.set_avatar(image_path)
        self.assertTrue(success)
        
        # Check avatar info
        avatar_info = self.file_manager.get_avatar_info("alice@192.168.1.10")
        self.assertTrue(avatar_info['has_avatar'])
        self.assertEqual(avatar_info['mime_type'], 'image/png')
    
    def test_create_profile_with_avatar(self):
        """Test creating profile message with avatar."""
        # Set avatar first
        image_path = self.create_test_image("avatar.png")
        self.file_manager.set_avatar(image_path)
        
        # Create profile message
        profile_msg = self.file_manager.create_profile_message("Alice", "Online")
        
        self.assertEqual(profile_msg['TYPE'], 'PROFILE')
        self.assertEqual(profile_msg['USER_ID'], 'alice@192.168.1.10')
        self.assertEqual(profile_msg['DISPLAY_NAME'], 'Alice')
        self.assertEqual(profile_msg['STATUS'], 'Online')
        self.assertIn('AVATAR_TYPE', profile_msg)
        self.assertIn('AVATAR_DATA', profile_msg)
    
    def test_handle_profile_with_avatar(self):
        """Test handling incoming profile with avatar."""
        # Create test avatar data
        image_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        encoded_data = FileUtils.encode_base64(image_data)
        
        profile_message = {
            'TYPE': 'PROFILE',
            'USER_ID': 'bob@192.168.1.11',
            'DISPLAY_NAME': 'Bob',
            'STATUS': 'Available',
            'AVATAR_TYPE': 'image/png',
            'AVATAR_ENCODING': 'base64',
            'AVATAR_DATA': encoded_data
        }
        
        with patch.object(self.file_manager.transfer_manager.message_validator, 'validate_profile_with_avatar') as mock_validate:
            mock_validate.return_value = {'valid': True, 'has_avatar': True}
            success = self.file_manager.handle_incoming_message(profile_message, "192.168.1.11")
        
        self.assertTrue(success)
        
        # Check that avatar was processed
        avatar_info = self.file_manager.get_avatar_info('bob@192.168.1.11')
        self.assertTrue(avatar_info['has_avatar'])


class TestFileManagerStatistics(TestFileManager):
    """Test file manager statistics and monitoring."""
    
    def test_transfer_statistics(self):
        """Test getting transfer statistics."""
        # Create some transfers
        file_path = self.create_test_file("Test content")
        
        with patch('src.utils.tokens.TokenGenerator.generate_token', side_effect=["test_token_1", "test_token_2"]):
          file_id1 = self.file_manager.send_file("bob@192.168.1.11", file_path, "File 1")
          file_id2 = self.file_manager.send_file("charlie@192.168.1.12", file_path, "File 2")
          print(f"file_id1 = {file_id1}")
          print(f"file_id2 = {file_id2}")


        
        # Get statistics
        stats = self.file_manager.get_transfer_statistics()
        
        self.assertEqual(stats['total_sessions'], 2)
        self.assertEqual(stats['outgoing_transfers'], 2)
        self.assertEqual(stats['incoming_transfers'], 0)
        self.assertIn('storage_stats', stats)
        self.assertIn('avatar_cache_stats', stats)
    
    def test_session_management(self):
        """Test session retrieval methods."""
        # Create test transfers
        file_path = self.create_test_file("Test content")
        
        with patch('src.utils.tokens.TokenGenerator.generate_token', return_value="test_token"):
            file_id = self.file_manager.send_file("bob@192.168.1.11", file_path)
        
        # Test getting all sessions
        all_sessions = self.file_manager.get_all_sessions()
        self.assertEqual(len(all_sessions), 1)
        
        # Test getting specific session
        session = self.file_manager.get_transfer_session(file_id)
        self.assertIsNotNone(session)
        self.assertEqual(session.file_id, file_id)
        
        # Test getting sessions by status
        pending = self.file_manager.get_pending_offers()
        active = self.file_manager.get_active_transfers()
        completed = self.file_manager.get_completed_transfers()
        
        # Should have no pending offers for outgoing transfers
        self.assertEqual(len(pending), 0)
        self.assertEqual(len(active), 0)  # Not started yet
        self.assertEqual(len(completed), 0)


class TestFileManagerConcurrency(TestFileManager):
    """Test concurrent file transfer handling."""
    
    def test_concurrent_transfers(self):
        """Test handling multiple concurrent transfers."""
        # Create multiple test files
        files = []
        for i in range(3):
            content = f"Test content for file {i}"
            file_path = self.create_test_file(content, f"test_{i}.txt")
            files.append(file_path)
        
        # Start multiple transfers
        file_ids = []
        with patch('src.utils.tokens.TokenGenerator.generate_token', return_value="test_token"):
            for i, file_path in enumerate(files):
                file_id = self.file_manager.send_file(f"user{i}@192.168.1.1{10+i}", file_path)
                file_ids.append(file_id)
        
        # Check all transfers were created
        self.assertEqual(len(file_ids), 3)
        for file_id in file_ids:
            self.assertIsNotNone(file_id)
        
        # Check statistics
        stats = self.file_manager.get_transfer_statistics()
        self.assertEqual(stats['total_sessions'], 3)
        self.assertEqual(stats['outgoing_transfers'], 3)
    
    def test_thread_safety(self):
        """Test thread safety of file manager operations."""
        file_path = self.create_test_file("Thread safety test")
        results = []
        errors = []
        
        def worker_thread(thread_id):
            try:
                with patch('src.utils.tokens.TokenGenerator.generate_token', return_value=f"token_{thread_id}"):
                    file_id = self.file_manager.send_file(f"user{thread_id}@192.168.1.100", file_path)
                    results.append(file_id)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 5)
        self.assertEqual(len(set(results)), 5)  # All file IDs should be unique


class TestFileManagerCleanup(TestFileManager):
    """Test cleanup and maintenance functionality."""
    
    def test_cleanup_old_transfers(self):
        """Test cleanup of old transfers."""
        # Create a transfer
        file_path = self.create_test_file("Test content")
        
        with patch('src.utils.tokens.TokenGenerator.generate_token', return_value="test_token"):
            file_id = self.file_manager.send_file("bob@192.168.1.11", file_path)
        
        # Simulate old transfer by modifying creation time
        session = self.file_manager.get_transfer_session(file_id)
        session.created_time = time.time() - 25 * 3600  # 25 hours ago
        session.status = TransferStatus.COMPLETED
        
        # Run cleanup
        initial_count = len(self.file_manager.get_all_sessions())
        self.file_manager.cleanup_old_transfers(max_age_hours=24)
        final_count = len(self.file_manager.get_all_sessions())
        
        self.assertLess(final_count, initial_count)
    
    def test_export_transfer_log(self):
        """Test exporting transfer log."""
        # Create some transfers
        file_path = self.create_test_file("Test content")
        
        with patch('src.utils.tokens.TokenGenerator.generate_token', return_value="test_token"):
            self.file_manager.send_file("bob@192.168.1.11", file_path, "Test transfer")
        
        # Export log
        log_path = os.path.join(self.temp_dir, "transfer_log.json")
        success = self.file_manager.export_transfer_log(log_path)
        
        self.assertTrue(success)
        self.assertTrue(os.path.exists(log_path))
        
        # Verify log content
        import json
        with open(log_path, 'r') as f:
            log_data = json.load(f)
        
        self.assertIn('user_id', log_data)
        self.assertIn('statistics', log_data)
        self.assertIn('sessions', log_data)
        self.assertEqual(log_data['user_id'], 'alice@192.168.1.10')
        self.assertGreater(len(log_data['sessions']), 0)
    
    def test_shutdown(self):
        """Test proper shutdown of file manager."""
        # Create some transfers
        file_path = self.create_test_file("Test content")
        
        with patch('src.utils.tokens.TokenGenerator.generate_token', return_value="test_token"):
            file_id = self.file_manager.send_file("bob@192.168.1.11", file_path)
        
        # Shutdown should not raise errors
        try:
            self.file_manager.shutdown()
        except Exception as e:
            self.fail(f"Shutdown raised an exception: {e}")
        
        # After shutdown, session should be cancelled
        session = self.file_manager.get_transfer_session(file_id)
        if session:  # May be None if cleaned up
            self.assertEqual(session.status, TransferStatus.CANCELLED)


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)