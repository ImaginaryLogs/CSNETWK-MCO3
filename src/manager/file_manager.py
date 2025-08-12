import os
import time
import math
import base64
import uuid
from typing import Tuple
from threading import Event
import threading
from src.utils.tokens import validate_token, generate_token
from src.utils.file_transfer import FileTransfer
from src.protocol.types.messages.message_formats import format_kv_message
from src.manager.lsnp_controller import LSNPController
from src.ui.logging import LoggerInstance
from src.config import MAX_CHUNK_SIZE

class FileManager:
  def __init__(self, controller: "LSNPController", logger: "LoggerInstance"):
      self.logger = logger
      self.controller = controller
  
  def _get_project_root(self):
    """Get the project root directory (CSNETWK-MCO3)"""
    # Start from current file location
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Go up directories until we find the project root
    while current_dir != os.path.dirname(current_dir):  # Stop at filesystem root
        if os.path.basename(current_dir) == "CSNETWK-MCO3":
            return current_dir
        # Also check if we're in the project by looking for key files/folders
        if os.path.exists(os.path.join(current_dir, "pyproject.toml")) and \
            os.path.exists(os.path.join(current_dir, "src")) and \
            os.path.exists(os.path.join(current_dir, "files")):
            return current_dir
        current_dir = os.path.dirname(current_dir)
    
    # Fallback: assume we're running from src/manager and go up two levels
    return os.path.dirname(os.path.dirname(current_dir))
  
  def _handle_file_offer(self, kv: dict, addr: Tuple[str, int]):
      from_id = kv.get("FROM", "")
      to_id = kv.get("TO", "")
      token = kv.get("TOKEN", "")
      
      # Verify this message is for usf
      if to_id != self.controller.full_user_id:
          if self.controller.verbose:
              self.logger.info(f"[FILE_OFFER IGNORED] Not for us: {to_id}")
          return
      
      if not validate_token(token, "file"):
          if self.controller.verbose:
              self.logger.info(f"[FILE_OFFER REJECTED] Invalid token from {from_id}")
          return
      
      filename = kv.get("FILENAME", "")
      filesize = int(kv.get("FILESIZE", "0"))
      filetype = kv.get("FILETYPE", "")
      file_id = kv.get("FILEID", "")
      description = kv.get("DESCRIPTION", "")
      
      # Calculate total chunks needed
      total_chunks = math.ceil(filesize / MAX_CHUNK_SIZE)
      
      # Create file transfer object
      transfer = FileTransfer(file_id, filename, filesize, filetype, 
                            total_chunks, from_id, description)
      
      self.controller.pending_offers[file_id] = transfer
      
      # Get sender display name
      sender_name = from_id.split('@')[0]
      for peer in self.controller.peer_map.values():
          if peer.user_id == from_id:
              sender_name = peer.display_name
              break
      
      self.logger.info(f"User {sender_name} is sending you a file do you accept?")
      if self.controller.verbose:
          self.logger.info(f"[FILE_OFFER] {filename} ({filesize} bytes) from {sender_name}")

  def _handle_file_chunk(self, kv: dict, addr: Tuple[str, int]):
      from_id = kv.get("FROM", "")
      to_id = kv.get("TO", "")
      token = kv.get("TOKEN", "")
      
      # Verify this message is for us
      if to_id != self.controller.full_user_id:
          return
      
      if not validate_token(token, "file"):
          if self.controller.verbose:
              self.logger.info(f"[FILE_CHUNK REJECTED] Invalid token from {from_id}")
          return
      
      file_id = kv.get("FILEID", "")
      chunk_index = int(kv.get("CHUNK_INDEX", "0"))
      total_chunks = int(kv.get("TOTAL_CHUNKS", "0"))
      chunk_size = int(kv.get("CHUNK_SIZE", "0"))
      data_b64 = kv.get("DATA", "")
      
      # Check if we have an active transfer for this file
      transfer = self.controller.active_transfers.get(file_id)
      if not transfer:
          # Ignore chunks for files we haven't accepted
          if self.controller.verbose:
              self.logger.info(f"[FILE_CHUNK IGNORED] No active transfer for {file_id}")
          return
      
      try:
          chunk_data = base64.b64decode(data_b64)
          success = transfer.add_chunk(chunk_index, chunk_data)
          
          if self.controller.verbose:
              self.logger.info(f"[FILE_CHUNK] {chunk_index+1}/{total_chunks} for {transfer.filename}")
          
          # Check if transfer is complete
          if transfer.completed:
              self._complete_file_transfer(transfer, addr)
              
      except Exception as e:
          if self.controller.verbose:
              self.logger.info(f"[FILE_CHUNK ERROR] Failed to process chunk: {e}")

  def _handle_file_received(self, kv: dict, addr: Tuple[str, int]):
      file_id = kv.get("FILEID", "")
      status = kv.get("STATUS", "")
      
      if self.controller.verbose:
          self.logger.info(f"[FILE_RECEIVED] {file_id} - {status}")

  def _complete_file_transfer(self, transfer: FileTransfer, sender_addr: Tuple[str, int]):
      """Complete a file transfer and save the file"""
      try:
          assembled_data = transfer.get_assembled_data()
          if not assembled_data:
              return
          
          # Create user-specific downloads directory at project root
          user_downloads_dir = os.path.join(self.controller.project_root, "lsnp_data", self.controller.full_user_id, "downloads")
          os.makedirs(user_downloads_dir, exist_ok=True)
          
          # Save the file
          file_path = os.path.join(user_downloads_dir, transfer.filename)
          with open(file_path, 'wb') as f:
              f.write(assembled_data)
          
          self.logger.info(f"File transfer of {transfer.filename} is complete")
          self.logger.info(f"File saved to: {file_path}")
          
          # Send FILE_RECEIVED confirmation
          self._send_file_received(transfer.file_id, transfer.sender_id, "COMPLETE")
          
          # Clean up
          if transfer.file_id in self.controller.active_transfers:
              del self.controller.active_transfers[transfer.file_id]
              
      except Exception as e:
          self.logger.error(f"[FILE_TRANSFER ERROR] Failed to complete transfer: {e}")

  def _send_file_received(self, file_id: str, recipient_id: str, status: str):
      """Send FILE_RECEIVED message"""
      if recipient_id not in self.controller.peer_map:
          return
      
      peer = self.controller.peer_map[recipient_id]
      timestamp = int(time.time())
      
      msg = f"TYPE: FILE_RECEIVED\nFROM: {self.controller.full_user_id}\nTO: {recipient_id}\nFILEID: {file_id}\nSTATUS: {status}\nTIMESTAMP: {timestamp}\n"
      
      try:
          self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
          if self.controller.verbose:
              self.logger.info(f"[FILE_RECEIVED SENT] {file_id} - {status}")
      except Exception as e:
          if self.controller.verbose:
              self.logger.info(f"[FILE_RECEIVED ERROR] {e}")
 
  def _send_file_response(self, recipient_id: str, file_id: str, response_type: str):
    """Send FILE_ACCEPT or FILE_REJECT message"""
    if recipient_id not in self.controller.peer_map:
        return
    
    peer = self.controller.peer_map[recipient_id]
    timestamp = int(time.time())
    token = generate_token(self.controller.full_user_id, "file")
    
    msg = (f"TYPE: {response_type}\n"
        f"FROM: {self.controller.full_user_id}\n"
        f"TO: {recipient_id}\n"
        f"FILEID: {file_id}\n"
        f"TOKEN: {token}\n"
        f"TIMESTAMP: {timestamp}\n")
    
    try:
        self.controller.socket.sendto(msg.encode(), (peer.ip, peer.port))
        if self.controller.verbose:
            self.controller.lsnp_logger.info(f"[{response_type} SENT] {file_id}")
    except Exception as e:
        if self.controller.verbose:
            self.controller.lsnp_logger.info(f"[{response_type} ERROR] {e}")
 
  def accept_file(self, file_id: str):
      """Accept a pending file offer"""
      if file_id not in self.controller.pending_offers:
          self.logger.error(f"[ERROR] No pending file offer with ID: {file_id}")
          return
      
      transfer = self.controller.pending_offers[file_id]
      transfer.accepted = True
      self.controller.active_transfers[file_id] = transfer
      del self.controller.pending_offers[file_id]
      
      # Send FILE_ACCEPT message to sender
      self._send_file_response(transfer.sender_id, file_id, "FILE_ACCEPT")
      
      self.logger.info(f"[FILE ACCEPTED] {transfer.filename} from {transfer.sender_id.split('@')[0]}")

  def reject_file(self, file_id: str):
      """Reject a pending file offer"""
      if file_id not in self.controller.pending_offers:
          self.logger.error(f"[ERROR] No pending file offer with ID: {file_id}")
          return
      
      transfer = self.controller.pending_offers[file_id]
      
      # Send FILE_REJECT message to sender
      self._send_file_response(transfer.sender_id, file_id, "FILE_REJECT")
      
      del self.controller.pending_offers[file_id]
      
      self.logger.info(f"[FILE REJECTED] {transfer.filename} from {transfer.sender_id.split('@')[0]}")

  def send_file(self, recipient_id: str, file_path: str, description: str = ""):
      """Send a file to another user"""
      # Accept both formats: "user" or "user@ip"
      if "@" not in recipient_id:
          # Find the full user_id in peer_map
          full_recipient_id = None
          for user_id in self.controller.peer_map:
              if user_id.startswith(f"{recipient_id}@"):
                  full_recipient_id = user_id
                  break
          if not full_recipient_id:
              self.logger.error(f"[ERROR] Unknown peer: {recipient_id}")
              return
          recipient_id = full_recipient_id

      if recipient_id not in self.controller.peer_map:
          self.logger.error(f"[ERROR] Unknown peer: {recipient_id}")
          return

      # Check if file_path is absolute or relative
      if not os.path.isabs(file_path):
          # If relative, first check in the 'files' folder at project root
          files_folder_path = os.path.join(self.controller.project_root, "files", file_path)
          if os.path.exists(files_folder_path):
              file_path = files_folder_path
          else:
              # If not in files folder, make it relative to project root
              project_file_path = os.path.join(self.controller.project_root, file_path)
              if os.path.exists(project_file_path):
                  file_path = project_file_path
              else:
                  self.logger.error(f"[ERROR] File not found: {file_path}")
                  self.logger.info(f"[HINT] Place files in: {os.path.join(self.controller.project_root, 'files')}")
                  return

      if not os.path.exists(file_path):
          self.logger.error(f"[ERROR] File not found: {file_path}")
          return

      peer = self.controller.peer_map[recipient_id]
      
      try:
          # Read file
          with open(file_path, 'rb') as f:
              file_data = f.read()
          
          
          # Generate file metadata
          file_id = str(uuid.uuid4())
          filename = os.path.basename(file_path)
          filesize = len(file_data)
          filetype = self._get_file_type(filename)
          timestamp = int(time.time())
          token = generate_token(self.controller.full_user_id, "file")
          response_event = threading.Event()
          self.controller.file_response_events[file_id] = response_event
          self.controller.file_responses[file_id] = ""
          
          # Calculate chunks
          total_chunks = math.ceil(filesize / MAX_CHUNK_SIZE)
          
          # Send FILE_OFFER
          offer_msg = (f"TYPE: FILE_OFFER\n"
                      f"FROM: {self.controller.full_user_id}\n"
                      f"TO: {recipient_id}\n"
                      f"FILENAME: {filename}\n"
                      f"FILESIZE: {filesize}\n"
                      f"FILETYPE: {filetype}\n"
                      f"FILEID: {file_id}\n"
                      f"DESCRIPTION: {description}\n"
                      f"TIMESTAMP: {timestamp}\n"
                      f"TOKEN: {token}\n")
          
          self.controller.socket.sendto(offer_msg.encode(), (peer.ip, peer.port))
          self.logger.info(f"[FILE OFFER SENT] {filename} to {peer.display_name}")
          
          # Wait a bit for the recipient to accept (in a real implementation, 
          # you might want to wait for an acceptance message)
          if response_event.wait(timeout=60):  # 60 second timeout
              response = self.controller.file_responses.get(file_id)
              
              if response == "ACCEPTED":
                  self.logger.info(f"[FILE ACCEPTED] Sending {filename} to {peer.display_name}")
                  
                  # Send file chunks
                  for chunk_index in range(total_chunks):
                      start = chunk_index * MAX_CHUNK_SIZE
                      end = min(start + MAX_CHUNK_SIZE, filesize)
                      chunk_data = file_data[start:end]
                      chunk_b64 = base64.b64encode(chunk_data).decode()
                      
                      chunk_msg = (f"TYPE: FILE_CHUNK\n"
                              f"FROM: {self.controller.full_user_id}\n"
                              f"TO: {recipient_id}\n"
                              f"FILEID: {file_id}\n"
                              f"CHUNK_INDEX: {chunk_index}\n"
                              f"TOTAL_CHUNKS: {total_chunks}\n"
                              f"CHUNK_SIZE: {len(chunk_data)}\n"
                              f"TOKEN: {token}\n"
                              f"DATA: {chunk_b64}\n")
                      
                      self.controller.socket.sendto(chunk_msg.encode(), (peer.ip, peer.port))
                      
                      if self.controller.verbose:
                          self.logger.info(f"[FILE CHUNK SENT] {chunk_index+1}/{total_chunks} to {peer.display_name}")
                      
                      time.sleep(0.1)  # Small delay between chunks
                  
                  self.logger.info(f"[FILE TRANSFER COMPLETE] {filename} sent to {peer.display_name}")
                  
              elif response == "REJECTED":
                  self.logger.info(f"[FILE REJECTED] {peer.display_name} rejected {filename}")
              else:
                  self.logger.error(f"[FILE ERROR] Unknown response: {response}")
          else:
              self.logger.error(f"[FILE TIMEOUT] No response from {peer.display_name} for {filename}")
          
          # Clean up
          if file_id in self.controller.file_response_events:
              del self.controller.file_response_events[file_id]
          if file_id in self.controller.file_responses:
              del self.controller.file_responses[file_id]
              
      except Exception as e:
          self.logger.error(f"[FILE SEND ERROR] {e}")
          # Clean up on error
          if file_id in self.controller.file_response_events:
              del self.controller.file_response_events[file_id]
          if file_id in self.controller.file_responses:
              del self.controller.file_responses[file_id]

  def _get_file_type(self, filename: str) -> str:
      """Get MIME type based on file extension"""
      ext = filename.lower().split('.')[-1] if '.' in filename else ''
      mime_types = {
          'txt': 'text/plain',
          'jpg': 'image/jpeg',
          'jpeg': 'image/jpeg',
          'png': 'image/png',
          'gif': 'image/gif',
          'pdf': 'application/pdf',
          'mp3': 'audio/mpeg',
          'mp4': 'video/mp4',
          'zip': 'application/zip'
      }
      return mime_types.get(ext, 'application/octet-stream')

  def list_pending_files(self):
      """List pending file offers"""
      if not self.controller.pending_offers:
          self.logger.info("No pending file offers.")
          return
      
      self.logger.info("Pending file offers:")
      for file_id, transfer in self.controller.pending_offers.items():
          sender_name = transfer.sender_id.split('@')[0]
          self.logger.info(f"- {transfer.filename} ({transfer.filesize} bytes) from {sender_name}")
          self.logger.info(f"  File ID: {file_id}")
          if transfer.description:
              self.logger.info(f"  Description: {transfer.description}")

  def list_active_transfers(self):
      """List active file transfers"""
      if not self.controller.active_transfers:
          self.logger.info("No active file transfers.")
          return
      
      self.logger.info("Active file transfers:")
      for file_id, transfer in self.controller.active_transfers.items():
          sender_name = transfer.sender_id.split('@')[0]
          progress = f"{transfer.received_chunks}/{transfer.total_chunks}"
          self.logger.info(f"- {transfer.filename} from {sender_name}: {progress} chunks")


    