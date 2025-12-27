import time
import os
import json
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pypdf import PdfReader
from src import database

class ShadowFileHandler(FileSystemEventHandler):
    """
    Handles file system events for the watched folders.
    """
    def on_created(self, event):
        if not event.is_directory:
            self.process_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.process_file(event.src_path)

    def process_file(self, file_path):
        """
        Reads the file and sends it to the database for vectorization.
        """
        if file_path.startswith('.'): # Ignore hidden files
            return

        try:
            ext = os.path.splitext(file_path)[1].lower()
            content = ""

            if ext in ['.txt', '.md', '.json', '.py']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            
            elif ext == '.pdf':
                reader = PdfReader(file_path)
                for page in reader.pages:
                    content += page.extract_text() + "\n"
            
            else:
                return # Skip unsupported file types

            if content.strip():
                print(f"[Watcher] Processing file: {file_path}")
                database.vectorize_file(file_path, content)
            
        except Exception as e:
            print(f"[Watcher] Error processing file {file_path}: {e}")

class FolderWatcher:
    """
    Manages the background monitoring of folders.
    """
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.observers = []
        self.running = False
        
    def load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Watcher] Error loading config: {e}")
            return {}

    def start(self):
        if self.running:
            print("[Watcher] Already running.")
            return

        config = self.load_config()
        folders = config.get("watch_folders", [])
        
        event_handler = ShadowFileHandler()

        for folder in folders:
            abs_path = os.path.abspath(folder)
            if not os.path.exists(abs_path):
                print(f"[Watcher] Warning: Folder {abs_path} does not exist. Creating it.")
                os.makedirs(abs_path, exist_ok=True)
            
            observer = Observer()
            observer.schedule(event_handler, abs_path, recursive=True)
            observer.start()
            self.observers.append(observer)
            print(f"[Watcher] Started monitoring: {abs_path}")

        self.running = True
        
        # Keep the main thread alive if run standalone, 
        # but here we usually run it in a daemon thread from app.py.
    
    def stop(self):
        for observer in self.observers:
            observer.stop()
        for observer in self.observers:
            observer.join()
        self.running = False
        print("[Watcher] Stopped monitoring.")

def start_background_watcher():
    """
    Helper to start the watcher in a daemon thread.
    """
    watcher = FolderWatcher()
    watcher.start()
    
    # We don't need a loop here because Observer creates its own threads.
    # We just need to keep the reference alive if needed, but for now 
    # the observers run in background threads.
    return watcher

if __name__ == "__main__":
    # Standalone testing
    w = FolderWatcher()
    w.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        w.stop()
