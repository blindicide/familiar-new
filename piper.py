import subprocess
import shutil
import os

PIPER_EXE = shutil.which("piper") # Find piper executable in PATH
VOICE_MODEL = "./path/to/your/voice.onnx" # Download a suitable voice model
VOICE_CONFIG = "./path/to/your/voice.onnx.json"

def speak_piper(text, output_file="output.wav"):
    if not PIPER_EXE:
        print("Error: Piper executable not found in PATH.")
        print(f"GLaDOS (TTS Piper): {text}")
        return
    if not os.path.exists(VOICE_MODEL):
         print(f"Error: Piper voice model not found at {VOICE_MODEL}")
         print(f"GLaDOS (TTS Piper): {text}")
         return

    print(f"GLaDOS: {text}")
    command = f'echo "{text}" | {PIPER_EXE} --model {VOICE_MODEL} --output_file {output_file}'
    try:
        # Use shell=True cautiously, ensure text is sanitized if it comes from external sources
        # A safer way might be to write text to a temp file and pipe that.
        subprocess.run(command, shell=True, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        # Now play the generated wav file (requires another library like playsound or pygame)
        # Example using playsound: pip install playsound
        import playsound
        try:
            playsound.playsound(output_file)
        except Exception as e:
            print(f"Error playing sound: {e}")
        finally:
             # Clean up the temp file
             if os.path.exists(output_file):
                os.remove(output_file)

    except subprocess.CalledProcessError as e:
        print(f"Error running Piper TTS: {e}")
        print(f"Stderr: {e.stderr.decode()}")
    except Exception as e:
         print(f"An unexpected error occurred during Piper TTS: {e}")


# Test it (after setting up Piper and models)
# speak_piper("This next test involves deadly lasers. You'll be fine.")