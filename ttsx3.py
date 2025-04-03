import pyttsx3

engine = None
try:
    engine = pyttsx3.init()
    # --- Voice Customization (Limited) ---
    voices = engine.getProperty('voices')
    # Try finding a voice you prefer - this varies wildly by OS
    print("Available voices:")
    for i, voice in enumerate(voices):
        print(f"{i}: {voice.id} - {voice.name}")
    # Choose a voice index (e.g., 0, 1, etc.) or ID
    engine.setProperty('voice', voices[1].id) # Example: select second voice

    engine.setProperty('rate', 160) # Adjust speed (words per minute)
    engine.setProperty('volume', 1.0) # Volume (0.0 to 1.0)

except Exception as e:
    print(f"Error initializing TTS engine: {e}")
    print("Text-to-speech might not be available.")

def speak(text):
    if engine:
        print(f"GLaDOS: {text}") # Also print to console
        engine.say(text)
        engine.runAndWait()
    else:
        print(f"GLaDOS (TTS disabled): {text}")

# Test it
speak("Oh. It's you. It's been a long time.")