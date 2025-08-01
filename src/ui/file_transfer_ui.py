"""
User interface components for LSNP file transfers.
Handles file offer prompts, progress display, and avatar management.
"""

import threading
import time
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from ..utils.file_utils import FileUtils


@dataclass
class ProgressInfo:
    """Progress information for UI display."""
    file_id: str
    filename: str
    progress_percentage: float
    transfer_speed: float
    eta_seconds: Optional[float]
    bytes_transferred: int
    total_bytes: int


class FileTransferUI:
    """User interface for file transfer operations."""
    
    def __init__(self):
        """Initialize file transfer UI."""
        self.root = None  # Will be set by main UI
        self.progress_windows: Dict[str, tk.Toplevel] = {}
        self.offer_windows: Dict[str, tk.Toplevel] = {}
        
        # UI callbacks
        self.file_selected_callback: Optional[Callable[[str], None]] = None
        self.avatar_selected_callback: Optional[Callable[[str], None]] = None
    
    def set_root_window(self, root: tk.Tk):
        """Set the root window for UI operations."""
        self.root = root
    
    def show_file_offer_prompt(self, from_user: str, filename: str, filesize: int,
                              description: str, accept_callback: Callable, reject_callback: Callable):
        """
        Show file offer prompt to user.
        
        Args:
            from_user: User offering the file
            filename: Name of the offered file
            filesize: Size of the file in bytes
            description: Optional file description
            accept_callback: Callback to call when accepting
            reject_callback: Callback to call when rejecting
        """
        if not self.root:
            # Fallback to console prompt
            self._console_file_offer_prompt(from_user, filename, filesize, description,
                                          accept_callback, reject_callback)
            return
        
        # Create offer window
        offer_window = tk.Toplevel(self.root)
        offer_window.title("File Transfer Offer")
        offer_window.geometry("400x250")
        offer_window.resizable(False, False)
        
        # Center the window
        offer_window.transient(self.root)
        offer_window.grab_set()
        
        # Create UI elements
        main_frame = ttk.Frame(offer_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Incoming File Transfer", 
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 10))
        
        # From user
        from_frame = ttk.Frame(main_frame)
        from_frame.pack(fill=tk.X, pady=2)
        ttk.Label(from_frame, text="From:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        ttk.Label(from_frame, text=from_user).pack(side=tk.LEFT, padx=(5, 0))
        
        # Filename
        filename_frame = ttk.Frame(main_frame)
        filename_frame.pack(fill=tk.X, pady=2)
        ttk.Label(filename_frame, text="File:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        ttk.Label(filename_frame, text=filename).pack(side=tk.LEFT, padx=(5, 0))
        
        # File size
        size_frame = ttk.Frame(main_frame)
        size_frame.pack(fill=tk.X, pady=2)
        ttk.Label(size_frame, text="Size:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        ttk.Label(size_frame, text=FileUtils.format_file_size(filesize)).pack(side=tk.LEFT, padx=(5, 0))
        
        # Description (if provided)
        if description:
            desc_frame = ttk.Frame(main_frame)
            desc_frame.pack(fill=tk.X, pady=2)
            ttk.Label(desc_frame, text="Description:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
            
            # Use text widget for longer descriptions
            desc_text = tk.Text(desc_frame, height=3, width=40, wrap=tk.WORD)
            desc_text.pack(side=tk.LEFT, padx=(5, 0), fill=tk.BOTH, expand=True)
            desc_text.insert(tk.END, description)
            desc_text.config(state=tk.DISABLED)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        def on_accept():
            offer_window.destroy()
            accept_callback()
        
        def on_reject():
            offer_window.destroy()
            reject_callback()
        
        def on_close():
            offer_window.destroy()
            reject_callback()
        
        ttk.Button(button_frame, text="Accept", command=on_accept).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Reject", command=on_reject).pack(side=tk.RIGHT)
        
        # Handle window close
        offer_window.protocol("WM_DELETE_WINDOW", on_close)
        
        # Store window reference
        file_id = f"{from_user}_{filename}_{int(time.time())}"
        self.offer_windows[file_id] = offer_window
    
    def _console_file_offer_prompt(self, from_user: str, filename: str, filesize: int,
                                  description: str, accept_callback: Callable, reject_callback: Callable):
        """Console fallback for file offer prompt."""
        def prompt_worker():
            print(f"\n=== FILE TRANSFER OFFER ===")
            print(f"From: {from_user}")
            print(f"File: {filename}")
            print(f"Size: {FileUtils.format_file_size(filesize)}")
            if description:
                print(f"Description: {description}")
            
            while True:
                try:
                    response = input("Accept file transfer? (y/n): ").strip().lower()
                    if response in ['y', 'yes']:
                        accept_callback()
                        break
                    elif response in ['n', 'no']:
                        reject_callback()
                        break
                    else:
                        print("Please enter 'y' for yes or 'n' for no.")
                except (EOFError, KeyboardInterrupt):
                    reject_callback()
                    break
        
        # Run in separate thread to avoid blocking
        threading.Thread(target=prompt_worker, daemon=True).start()
    
    def show_transfer_progress(self, file_id: str, filename: str) -> Optional[tk.Toplevel]:
        """
        Show transfer progress window.
        
        Args:
            file_id: File transfer ID
            filename: Name of the file being transferred
            
        Returns:
            Progress window if GUI available, None otherwise
        """
        if not self.root:
            return None
        
        # Create progress window
        progress_window = tk.Toplevel(self.root)
        progress_window.title(f"Transferring: {filename}")
        progress_window.geometry("400x150")
        progress_window.resizable(False, False)
        
        # Create UI elements
        main_frame = ttk.Frame(progress_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Filename label
        filename_label = ttk.Label(main_frame, text=filename, font=("Arial", 10, "bold"))
        filename_label.pack(pady=(0, 10))
        
        # Progress bar
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(main_frame, variable=progress_var, maximum=100)
        progress_bar.pack(fill=tk.X, pady=5)
        
        # Status label
        status_label = ttk.Label(main_frame, text="Starting transfer...")
        status_label.pack(pady=5)
        
        # Cancel button
        def cancel_transfer():
            progress_window.destroy()
            # TODO: Implement cancel callback
        
        cancel_button = ttk.Button(main_frame, text="Cancel", command=cancel_transfer)
        cancel_button.pack(pady=(10, 0))
        
        # Store references for updating
        progress_window.progress_var = progress_var
        progress_window.status_label = status_label
        
        # Store window reference
        self.progress_windows[file_id] = progress_window
        
        return progress_window
    
    def update_transfer_progress(self, file_id: str, progress_percentage: float,
                               transfer_speed: float, eta_seconds: Optional[float]):
        """
        Update transfer progress display.
        
        Args:
            file_id: File transfer ID
            progress_percentage: Progress as percentage (0-100)
            transfer_speed: Transfer speed in bytes per second
            eta_seconds: Estimated time to completion in seconds
        """
        if file_id not in self.progress_windows:
            return
        
        window = self.progress_windows[file_id]
        if not window.winfo_exists():
            del self.progress_windows[file_id]
            return
        
        try:
            # Update progress bar
            window.progress_var.set(progress_percentage)
            
            # Update status text
            speed_text = FileUtils.format_file_size(int(transfer_speed)) + "/s"
            
            if eta_seconds and eta_seconds > 0:
                eta_text = self._format_time(eta_seconds)
                status_text = f"{progress_percentage:.1f}% - {speed_text} - ETA: {eta_text}"
            else:
                status_text = f"{progress_percentage:.1f}% - {speed_text}"
            
            window.status_label.config(text=status_text)
            
        except tk.TclError:
            # Window was destroyed
            if file_id in self.progress_windows:
                del self.progress_windows[file_id]
    
    def _format_time(self, seconds: float) -> str:
        """Format time duration for display."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def show_transfer_completed(self, filename: str, file_path: Optional[str]):
        """
        Show transfer completion notification.
        
        Args:
            filename: Name of the completed file
            file_path: Path where file was saved
        """
        if self.root:
            # GUI notification
            message = f"File transfer completed: {filename}"
            if file_path:
                message += f"\n\nSaved to: {file_path}"
            
            messagebox.showinfo("Transfer Complete", message)
        else:
            # Console notification
            print(f"\n=== TRANSFER COMPLETED ===")
            print(f"File: {filename}")
            if file_path:
                print(f"Saved to: {file_path}")
    
    def show_transfer_error(self, file_id: str, error_message: str):
        """
        Show transfer error notification.
        
        Args:
            file_id: File transfer ID
            error_message: Error description
        """
        # Close progress window if open
        if file_id in self.progress_windows:
            try:
                self.progress_windows[file_id].destroy()
            except tk.TclError:
                pass
            del self.progress_windows[file_id]
        
        if self.root:
            messagebox.showerror("Transfer Error", f"File transfer failed:\n{error_message}")
        else:
            print(f"\n=== TRANSFER ERROR ===")
            print(f"Error: {error_message}")
    
    def show_error_message(self, message: str):
        """Show general error message."""
        if self.root:
            messagebox.showerror("Error", message)
        else:
            print(f"Error: {message}")
    
    def show_file_selection_dialog(self, title: str = "Select File to Send") -> Optional[str]:
        """
        Show file selection dialog.
        
        Args:
            title: Dialog title
            
        Returns:
            Selected file path or None if cancelled
        """
        if not self.root:
            return self._console_file_selection()
        
        file_path = filedialog.askopenfilename(
            title=title,
            filetypes=[
                ("All files", "*.*"),
                ("Images", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("Documents", "*.txt *.pdf *.doc *.docx"),
                ("Archives", "*.zip *.tar *.gz")
            ]
        )
        
        return file_path if file_path else None
    
    def _console_file_selection(self) -> Optional[str]:
        """Console fallback for file selection."""
        try:
            file_path = input("Enter file path to send: ").strip()
            if file_path and Path(file_path).exists():
                return file_path
            else:
                print("File not found.")
                return None
        except (EOFError, KeyboardInterrupt):
            return None
    
    def show_avatar_selection_dialog(self) -> Optional[str]:
        """
        Show avatar image selection dialog.
        
        Returns:
            Selected image path or None if cancelled
        """
        if not self.root:
            return self._console_file_selection()
        
        file_path = filedialog.askopenfilename(
            title="Select Avatar Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("All files", "*.*")
            ]
        )
        
        return file_path if file_path else None
    
    def create_transfer_summary_window(self, sessions: List[Dict[str, Any]]) -> Optional[tk.Toplevel]:
        """
        Create a window showing transfer summary.
        
        Args:
            sessions: List of transfer session data
            
        Returns:
            Summary window if GUI available, None otherwise
        """
        if not self.root:
            self._console_transfer_summary(sessions)
            return None
        
        # Create summary window
        summary_window = tk.Toplevel(self.root)
        summary_window.title("File Transfer Summary")
        summary_window.geometry("600x400")
        
        # Create treeview for sessions
        main_frame = ttk.Frame(summary_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview
        columns = ("Direction", "Peer", "Filename", "Size", "Status", "Progress")
        tree = ttk.Treeview(main_frame, columns=columns, show="headings")
        
        # Configure columns
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate data
        for session in sessions:
            direction = session.get('direction', 'Unknown')
            peer = session.get('peer_user_id', 'Unknown')
            filename = session.get('filename', 'Unknown')
            size = FileUtils.format_file_size(session.get('filesize', 0))
            status = session.get('status', 'Unknown')
            progress = f"{session.get('progress_percentage', 0):.1f}%"
            
            tree.insert("", tk.END, values=(direction, peer, filename, size, status, progress))
        
        # Close button
        close_button = ttk.Button(main_frame, text="Close", 
                                command=summary_window.destroy)
        close_button.pack(pady=(10, 0))
        
        return summary_window
    
    def _console_transfer_summary(self, sessions: List[Dict[str, Any]]):
        """Console fallback for transfer summary."""
        print("\n=== TRANSFER SUMMARY ===")
        for i, session in enumerate(sessions, 1):
            print(f"{i}. {session.get('direction', 'Unknown').upper()}")
            print(f"   Peer: {session.get('peer_user_id', 'Unknown')}")
            print(f"   File: {session.get('filename', 'Unknown')}")
            print(f"   Size: {FileUtils.format_file_size(session.get('filesize', 0))}")
            print(f"   Status: {session.get('status', 'Unknown')}")
            print(f"   Progress: {session.get('progress_percentage', 0):.1f}%")
            print()
    
    def cleanup_windows(self):
        """Clean up any open UI windows."""
        # Close progress windows
        for window in list(self.progress_windows.values()):
            try:
                window.destroy()
            except tk.TclError:
                pass
        self.progress_windows.clear()
        
        # Close offer windows
        for window in list(self.offer_windows.values()):
            try:
                window.destroy()
            except tk.TclError:
                pass
        self.offer_windows.clear()