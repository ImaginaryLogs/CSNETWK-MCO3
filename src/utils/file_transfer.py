from typing import Dict, Optional
import time

class FileTransfer:
    def __init__(self, file_id: str, filename: str, filesize: int, filetype: str, 
                 total_chunks: int, sender_id: str, description: str = ""):
        self.file_id = file_id
        self.filename = filename
        self.filesize = filesize
        self.filetype = filetype
        self.total_chunks = total_chunks
        self.sender_id = sender_id
        self.description = description
        self.chunks: Dict[int, bytes] = {}
        self.received_chunks = 0
        self.accepted = False
        self.completed = False
        self.timestamp = int(time.time())
        

    def add_chunk(self, chunk_index: int, data: bytes) -> bool:
        if not self.accepted:
            return False
        
        if chunk_index not in self.chunks:
            self.chunks[chunk_index] = data
            self.received_chunks += 1
        
        if self.received_chunks == self.total_chunks:
            self.completed = True
        
        return True

    def get_assembled_data(self) -> Optional[bytes]:
        if not self.completed:
            return None
        
        assembled = b''
        for i in range(self.total_chunks):
            if i not in self.chunks:
                return None
            assembled += self.chunks[i]
        
        return assembled
