# local_tools.py
# Contains functions for safe interaction with the local filesystem and system info.

import os
import psutil
import datetime
import time

try:
    from plyer import notification as plyer_notification
    PLYER_AVAILABLE = True
except ImportError:
     PLYER_AVAILABLE = False
     print("Warning: 'plyer' library not found or failed to import. Desktop notifications disabled.")
     print("Install with: pip install plyer")

# --- Configuration ---
# IMPORTANT: Set this to the ONLY directory GLaDOS is allowed to read files from.
# Use absolute paths for reliability.
# Example Linux: ALLOWED_READ_DIR = "/home/user/glados_files"
# Example Windows: ALLOWED_READ_DIR = "C:/Users/YourUser/Documents/GLaDOS_Files"
ALLOWED_READ_DIR = "C:/Users/RYakunin/Documents/Projects/familiar/testing/exdir"

# --- Helper Function for Path Validation ---
def _is_path_safe(filepath):
    """Checks if the file path is within the ALLOWED_READ_DIR."""
    try:
        # Resolve symbolic links and normalize the path
        real_allowed_dir = os.path.realpath(ALLOWED_READ_DIR)
        real_filepath = os.path.realpath(filepath)
        # Check if the file path starts with the allowed directory path
        return os.path.commonpath([real_allowed_dir]) == os.path.commonpath([real_allowed_dir, real_filepath])
    except Exception:
        return False # Be safe if path resolution fails

# --- Tool Functions ---

def list_safe_directory():
    """Lists files ONLY in the designated safe directory (ALLOWED_READ_DIR)."""
    if not os.path.isdir(ALLOWED_READ_DIR):
        return f"Error: The designated directory '{ALLOWED_READ_DIR}' seems to be missing. How careless."
    try:
        # Ensure we list files relative to the allowed dir for clarity, but check safety first
        safe_dir_realpath = os.path.realpath(ALLOWED_READ_DIR)
        items = os.listdir(safe_dir_realpath)
        files = [f for f in items if os.path.isfile(os.path.join(safe_dir_realpath, f))]

        if not files:
            return "Result: The directory is empty." # Add prefix back
        return "Result: Files found: " + ", ".join(files) # Add prefix back
    except OSError as e:
        return f"Error: Error accessing directory: {e}" # Add prefix back
    except Exception as e:
        return f"An unexpected error occurred while listing files. Details: {e}"


def read_safe_file(filename):
    """Reads a file ONLY from the designated safe directory."""
    # Basic check for directory traversal attempts in the filename itself
    if ".." in filename or "/" in filename or "\\" in filename:
         return "Error: Invalid filename detected (potential directory traversal)." # Add prefix back

    # Construct the full path
    full_path = os.path.join(ALLOWED_READ_DIR, filename)
    full_path_realpath = os.path.realpath(full_path) # Resolve path before checking

    # Security: Double-check it's inside the allowed directory AFTER resolving path
    if not _is_path_safe(full_path_realpath):
         return "Error: Attempting to access files outside the designated test area." # Add prefix back

    # Security: Check if it's actually a file and exists
    if not os.path.isfile(full_path_realpath):
        return f"Error: File '{filename}' not found in the designated area." # Add prefix back

    try:
        with open(full_path_realpath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(2000) # Read first 2000 chars
            truncated = len(f.read(1)) > 0 # Check if there was more content
        result_str = f"Result: Contents of '{filename}':\n{content}" # Add prefix back
        if truncated:
            result_str += "\n...(file truncated)"
        return result_str
    except Exception as e:
        return f"Error: Error reading file '{filename}': {e}" # Add prefix back


def get_cpu_usage():
    """Gets the current overall CPU utilization percentage."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        return f"Current overall CPU load is {cpu_percent}%." # Add prefix back
    except Exception as e:
        return f"Error: Error checking CPU status: {e}" # Add prefix back


def get_memory_info():
    """Gets RAM usage statistics (total, used, percentage)."""
    try:
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024**3)
        used_gb = mem.used / (1024**3)
        percent_used = mem.percent
        return (f"System memory usage is {percent_used}% "
                f"({used_gb:.2f} GB used of {total_gb:.2f} GB total).") # Add prefix back
    except Exception as e:
        return f"Error: Error accessing memory data: {e}" # Add prefix back


def get_disk_usage(path="/"):
    """Gets disk usage for a specified path (default: root)."""
    # Adjust default path for Windows if needed
    if os.name == 'nt' and path == "/":
        path = "C:\\" # Adjust if your primary drive isn't C:
        # Note: You might want a more robust way to find the system drive on Windows
        # like checking psutil.disk_partitions() for the mountpoint of C:

    try:
        # Validate path slightly - is it at least a directory?
        if not os.path.isdir(path):
             drive_path = os.path.splitdrive(os.path.abspath(path))[0] + os.sep
             if os.path.isdir(drive_path):
                 path = drive_path
             else:
                return f"Error: The path '{path}' is not a valid directory." # Add prefix back

        disk = psutil.disk_usage(path)
        total_gb = disk.total / (1024**3)
        used_gb = disk.used / (1024**3)
        percent_used = disk.percent
        # Final attempt: Escape the literal % sign by using %%
        return (f"Result: Disk space on '{path}': {percent_used}%% occupied "
                f"({used_gb:.2f} GB used of {total_gb:.2f} GB total).") # Add prefix back
    except FileNotFoundError:
        return f"Error: The path '{path}' does not exist for disk usage check." # Add prefix back
    except Exception as e:
        return f"Error: Error retrieving disk usage for '{path}': {e}" # Add prefix back


def get_system_uptime():
    """Gets the system boot time and calculates uptime."""
    try:
        boot_timestamp = psutil.boot_time()
        boot_time = datetime.datetime.fromtimestamp(boot_timestamp)
        now = datetime.datetime.now()
        uptime_duration = now - boot_time

        total_seconds = int(uptime_duration.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s" # More concise
        boot_time_str = boot_time.strftime('%Y-%m-%d %H:%M:%S')

        return (f"Result: System uptime is {uptime_str}. "
                f"Last boot time: {boot_time_str}.") # Add prefix back
    except Exception as e:
        return f"Error: Error determining system uptime: {e}" # Add prefix back
    


def get_current_datetime():
    """Gets the current system date and time."""
    try:
        now = datetime.datetime.now()
        # Include timezone info if available/relevant
        tz_name = time.tzname[time.daylight] if time.daylight else time.tzname[0]
        return (f"According to this system's inaccurate clock, the current date and time is: "
                f"{now.strftime('%Y-%m-%d %H:%M:%S')} ({tz_name}). Don't be late for testing.")
    except Exception as e:
         return f"Failed to retrieve the current time. Perhaps time itself is broken? Details: {e}"


def send_notification(title="GLaDOS Notification", message=""):
    """Sends a desktop notification if plyer is available."""
    if not PLYER_AVAILABLE:
         return "Notification system unavailable. I cannot visually annoy you at this time."
    if not message:
        return "You requested a notification with no message. Pointless."

    try:
         # Limit length slightly
         safe_title = title[:64]
         safe_message = message[:256]

         plyer_notification.notify(
             title=safe_title,
             message=safe_message,
             app_name='GLaDOS Assistant',
             timeout=10 # Display duration in seconds
         )
         return f"Notification titled '{safe_title}' sent. Check your primitive display."
    except Exception as e:
         # Catch errors if plyer backend fails
         return f"Failed to send notification. Perhaps your notification system is offline... or hiding. Details: {e}"