# tts_piper.py
# Handles Text-to-Speech using the Piper TTS engine.

import subprocess
import shutil
import os
import platform

# --- Configuration ---
# Option 1: Assume 'piper' is in the system PATH
PIPER_EXE = shutil.which("piper")

# Option 2: Specify the full path if not in PATH
# PIPER_EXE = "/path/to/your/piper/executable" # e.g., "/home/user/piper/piper" or "C:/piper/piper.exe"

# Path to the downloaded Piper voice model (.onnx file)
# Download voices from: https://huggingface.co/rhasspy/piper-voices/tree/main
# Example: VOICE_MODEL = "./models/en_US-lessac-medium.onnx"
VOICE_MODEL = "C:\Users\RYakunin\Documents\Projects\familiar\voices\glados\en-us-glados-high.onnx"

# Path to the corresponding voice config file (.json file)
# Example: VOICE_CONFIG = "./models/en_US-lessac-medium.onnx.json"
VOICE_CONFIG = "C:\Users\RYakunin\Documents\Projects\familiar\voices\glados\en-us-glados-high.onnx.json"

# --- Audio Playback Setup ---
# Choose ONE method for playing the generated WAV file.

# Method A: Using 'playsound' library (cross-platform, simple)
# Install: pip install playsound
USE_PLAYSOUND = True
try:
    import playsound
except ImportError:
    print("Warning: 'playsound' library not found. Install with 'pip install playsound' for audio output.")
    USE_PLAYSOUND = False

# Method B: Using OS-specific commands (no extra library, might be less reliable)
USE_OS_COMMAND = False # Set to True if you prefer this and disable playsound
PLAYER_COMMAND = ""
if platform.system() == "Linux":
    PLAYER_COMMAND = "aplay" # or "paplay"
elif platform.system() == "Darwin": # macOS
    PLAYER_COMMAND = "afplay"
elif platform.system() == "Windows":
    # Windows is tricky with command-line players. playsound is generally better.
    # Could try Powershell:
    # PLAYER_COMMAND = 'powershell -c (New-Object Media.SoundPlayer "{}").PlaySync();'
    # Or rely on an external player installed and in PATH like VLC:
    # PLAYER_COMMAND = 'vlc --play-and-exit {}' # Requires VLC installed
    pass # Stick to playsound on Windows unless specifically configured

# --- TTS Function ---

def speak(text, output_file="glados_output.wav"):
    """Uses Piper TTS to generate audio and plays it."""
    global PIPER_EXE, VOICE_MODEL, VOICE_CONFIG # Allow modification if needed

    # --- Pre-checks ---
    if not PIPER_EXE:
        # Attempt to find piper again in case it was installed after script start
        PIPER_EXE = shutil.which("piper")
        if not PIPER_EXE:
             print("\nError: Piper executable not found.")
             print(f"GLaDOS (TTS Disabled): {text}")
             return

    if not os.path.isfile(VOICE_MODEL):
        print(f"\nError: Piper voice model not found at '{VOICE_MODEL}'")
        print(f"GLaDOS (TTS Disabled): {text}")
        return

    if not os.path.isfile(VOICE_CONFIG):
        print(f"\nError: Piper voice config not found at '{VOICE_CONFIG}'")
        print(f"GLaDOS (TTS Disabled): {text}")
        return

    print(f"\nGLaDOS: {text}") # Print the text regardless

    # --- Generate Audio ---
    try:
        # Construct the command carefully
        command = [
            PIPER_EXE,
            "--model", VOICE_MODEL,
            "--config", VOICE_CONFIG,
            "--output_file", output_file
        ]
        # Pipe the text to Piper's stdin
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(input=text.encode('utf-8'))

        if process.returncode != 0:
            print(f"Error running Piper TTS (Return Code: {process.returncode}):")
            print(f"Stderr: {stderr.decode('utf-8', errors='ignore')}")
            return # Don't try to play a potentially non-existent/corrupt file

    except FileNotFoundError:
         print(f"\nError: Could not execute Piper. Is '{PIPER_EXE}' the correct path?")
         return
    except Exception as e:
        print(f"\nAn unexpected error occurred during Piper TTS generation: {e}")
        return

    # --- Play Audio ---
    if not os.path.exists(output_file):
        print("\nError: Output audio file was not created by Piper.")
        return

    try:
        if USE_PLAYSOUND and 'playsound' in globals():
            playsound.playsound(output_file)
        elif USE_OS_COMMAND and PLAYER_COMMAND:
            play_cmd = PLAYER_COMMAND.format(output_file) if '{}' in PLAYER_COMMAND else [PLAYER_COMMAND, output_file]
            subprocess.run(play_cmd, shell=isinstance(play_cmd, str), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            # Fallback if no player is configured/working
             print("(Audio playback skipped - no suitable player found/enabled)")

    except Exception as e:
        print(f"\nError playing sound file '{output_file}': {e}")
        # Attempt to provide more info if it's a playsound specific error
        if USE_PLAYSOUND and 'playsound' in globals() and isinstance(e, playsound.PlaysoundException):
             print("This might be due to missing audio codecs or permissions.")

    finally:
        # --- Clean up ---
        try:
            if os.path.exists(output_file):
                os.remove(output_file)
        except OSError as e:
            print(f"\nWarning: Could not remove temporary audio file '{output_file}': {e}")

# --- Self-test (optional) ---
if __name__ == '__main__':
    print("Testing Piper TTS...")
    speak("This is only a test. Had this been an actual emergency, something probably would have exploded by now.")
    print("Test complete.")