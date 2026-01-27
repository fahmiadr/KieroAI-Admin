import os
import sys
import argparse
import subprocess
import threading
import time
import shutil
import zipfile
from datetime import datetime, timedelta

def get_today_str():
    return datetime.now().strftime('%Y-%m-%d')

class LogRotator:
    def __init__(self, log_dir, service_name):
        self.log_dir = log_dir
        self.service_name = service_name
        self.current_date = get_today_str()
        
        # Ensure log dir exists
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        self.archive_dir = os.path.join(self.log_dir, 'archive')
        if not os.path.exists(self.archive_dir):
            os.makedirs(self.archive_dir)

    def get_log_file_path(self):
        return os.path.join(self.log_dir, f"{self.current_date}.log")
    
    def get_current_log_path(self):
        return os.path.join(self.log_dir, "current.log")

    def check_rotation(self):
        """Check if date has changed, if so update current_date."""
        today = get_today_str()
        if today != self.current_date:
            print(f"[LogManager] Rotating log from {self.current_date} to {today}")
            self.current_date = today
            # Kosongkan current.log saat ganti hari (opsional, atau biarkan append)
            # open(self.get_current_log_path(), 'w').close() 

    def write(self, content):
        """Write content to both daily log and current.log"""
        self.check_rotation()
        
        # 1. Write to Daily Log
        daily_path = self.get_log_file_path()
        try:
            with open(daily_path, 'a', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"Error writing to daily log: {e}")

        # 2. Write to Current Log (For Dashboard Viewer)
        # Dashboard reads 'current.log'. We keep it updated.
        current_path = self.get_current_log_path()
        try:
            with open(current_path, 'a', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"Error writing to current log: {e}")

    def archive_old_logs(self):
        """Archive logs older than 7 days."""
        print("[Archive] Checking for old logs...")
        cutoff_date = datetime.now() - timedelta(days=7)
        
        for filename in os.listdir(self.log_dir):
            if filename.endswith(".log") and filename != "current.log":
                try:
                    # Parse filename YYYY-MM-DD.log
                    date_str = filename.replace('.log', '')
                    file_date = datetime.strptime(date_str, '%Y-%m-%d')
                    
                    if file_date < cutoff_date:
                        self._compress_and_delete(filename)
                except ValueError:
                    continue # Skip files that don't match pattern

    def _compress_and_delete(self, filename):
        file_path = os.path.join(self.log_dir, filename)
        zip_name = f"{filename}.zip"
        zip_path = os.path.join(self.archive_dir, zip_name)
        
        print(f"[Archive] Compressing {filename} -> {zip_name}")
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(file_path, arcname=filename)
            
            # Delete original file
            os.remove(file_path)
            print(f"[Archive] Archived and deleted {filename}")
        except Exception as e:
            print(f"[Archive] Error archiving {filename}: {e}")

def archive_worker(rotator):
    """Background thread to run archiving periodically."""
    while True:
        rotator.archive_old_logs()
        # Check every 24 hours
        time.sleep(86400) 

def run_service(command, rotator):
    """Run the actual service command."""
    print(f"[LogManager] Starting service: {command}")
    
    # Use shell=True for complex commands (cd ... && npm ...)
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, # Merge stderr into stdout
        text=True,
        bufsize=1, # Line buffered
        encoding='utf-8',
        errors='replace'
    )
    
    # Read output line by line
    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            # Print to stdout so it still shows in console if running manually
            sys.stdout.write(line)
            sys.stdout.flush()
            
            # Write to logs
            rotator.write(line)
            
    return process.returncode

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Service Log Manager & Rotator")
    parser.add_argument("--name", required=True, help="Service name (e.g. backend)")
    parser.add_argument("--cmd", required=True, help="Command to run")
    parser.add_argument("--log_dir", required=True, help="Directory to store logs")
    
    args = parser.parse_args()
    
    print(f"[LogManager] Initializing for {args.name}...")
    rotator = LogRotator(args.log_dir, args.name)
    
    # Start Archiver Thread (Daemon)
    archiver_thread = threading.Thread(target=archive_worker, args=(rotator,), daemon=True)
    archiver_thread.start()
    
    try:
        # Run Service
        return_code = run_service(args.cmd, rotator)
        sys.exit(return_code)
    except KeyboardInterrupt:
        print("\n[LogManager] Stopping...")
