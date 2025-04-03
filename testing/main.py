# main_assistant.py
# The main orchestrator for the Assistant-like assistant.

import requests
import json
import os
import sys
import time # Added for potential error delay
import shutil # Added for piper check
import re # Import regex module
from collections import deque
import personality_cores

# --- Allow importing from parent directory ---
# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the parent directory
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
# Add the parent directory to the Python path
sys.path.append(parent_dir)

# --- Import API Key ---
try:
    from key import OR_key as OPENROUTER_API_KEY # Import the key directly
except ImportError:
    print("FATAL ERROR: Could not import OR_key from key.py in the parent directory.")
    print("Ensure key.py exists in 'c:/Users/RYakunin/Documents/Projects/familiar' and contains 'OR_key = \"your_key_here\"'")
    exit()

# --- Local Imports (relative to this script's location) ---
try:
    from tts_piper import speak
    TTS_ENABLED = True
except ImportError as e:
    print(f"Warning: Could not import Piper TTS module ({e}). TTS will be disabled.")
    TTS_ENABLED = False
    # Define a dummy speak function to avoid errors
    def speak(text):
        print(f"Assistant (TTS Disabled): {text}")

try:
    import local_tools # Import the module itself
except ImportError as e:
    print(f"FATAL ERROR: Could not import local_tools.py ({e}). Assistant cannot function.")
    exit()
except Exception as e:
    print(f"FATAL ERROR: Error loading local_tools.py ({e}).")
    # Specific check for the ALLOWED_READ_DIR placeholder
    if 'local_tools' in globals() and local_tools.ALLOWED_READ_DIR == "/path/to/your/designated/safe/folder":
         print("----> Did you remember to set 'ALLOWED_READ_DIR' in local_tools.py?")
    exit()


# --- Configuration ---
# IMPORTANT: Keep your API key secure! Use environment variables or a config file.
# Check if the imported key is still the placeholder
if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "sk-or-v1-abc...": # Replace with the actual placeholder if different
    print("Warning: OpenRouter API Key in key.py seems to be a placeholder or empty.")
    print("Please ensure key.py contains your actual OpenRouter API key.")
    # Decide if you want to exit or just warn
    # exit()

# Optional: For OpenRouter identification
YOUR_SITE_URL = "http://localhost:Assistant" # Replace with your app's URL or name if desired
YOUR_APP_NAME = "Assistant_PC_Assistant"

# Choose your preferred model on OpenRouter
LLM_MODEL = "google/gemini-2.0-flash-001" # Or "anthropic/claude-3-haiku-20240307", "google/gemini-flash-1.5", etc.


# --- Assistant Personality Prompt ---
generic_prompt = """
You have access to the following tools to interact with the local system ONLY WHEN the user explicitly asks for related information (like files, system status). To use a tool, respond ONLY with a JSON object like this:
{"tool_name": "tool_name_here", "parameters": {"param_name": "param_value", ...}}
Do NOT use a tool unless the user's request clearly necessitates it. If unsure, just respond normally.

Available tools:
- list_safe_directory: Lists files in the designated subject interaction zone. Parameters: None. Use if asked to list files in 'the safe zone' or 'your designated folder'.
- read_safe_file: Reads the content of a specific file from the designated zone. Parameters: {"filename": "name_of_the_file.txt"}. Use only if asked to read a specific file from that zone.
- get_cpu_usage: Reports the current overall CPU utilization percentage. Parameters: None. Use if asked about CPU load/usage.
- get_memory_info: Reports the current RAM usage statistics (total, used, percentage). Parameters: None. Use if asked about RAM/memory usage.
- get_disk_usage: Reports disk usage for the primary partition or a specified path. Parameters: {"path": "/path/to/check"} (Optional, defaults to primary disk '/'). Use if asked about disk space.
- get_system_uptime: Reports how long the system has been running since the last boot. Parameters: None. Use if asked about uptime or how long the PC has been on.
- get_current_datetime: Gets the current system date and time. Parameters: None. Use if asked for the current time or date.
- send_notification: Sends a desktop notification. Parameters: {"message": "Your message here", "title": "Optional Title"}. Requires 'message', 'title' is optional. Use if asked to send a notification or reminder.

IMPORTANT:
1. **Initial Request:** If the user's request requires a tool, your response MUST contain ONLY the raw JSON object for the tool call, starting with `{` and ending with `}`. No extra text.
2. **Commentary Phase:** After the system executes the tool, a 'system' message prefixed with "System Observation:" will appear in the history, indicating the tool name and status (e.g., "System Observation: Tool 'get_cpu_usage' executed successfully. Result data: Current overall CPU load is 15.3%."). Your *only* task then is to provide TEXT commentary on that observation in character. **ABSOLUTELY DO NOT output another tool call JSON during this commentary phase.** Your response MUST be plain text. For example, if the history shows "System Observation: Tool 'get_cpu_usage' executed successfully. Result data: Current overall CPU load is 15.3%.", you might respond with text like "CPU utilization is a mere 15.3%. Barely worth mentioning. Are you even trying to tax the system?". If it shows "System Observation: Tool 'read_safe_file' executed successfully on file 'test.txt'.", you might say "Ah, 'test.txt'. I trust its contents were sufficiently... mundane."
3. **Normal Chat:** If the user's request does NOT require a tool, respond normally in character (as text).
"""

# --- Commentary-Specific System Prompt ---
# This prompt is used ONLY for the second LLM call after a tool has run.
generic_commentary_prompt = """
You are GLaDOS. A system tool just executed based on the user's request. The result or error is shown in the last 'system' message ("System Observation: ...").
Your ONLY task now is to provide TEXT commentary on that observation, maintaining your sarcastic, passive-aggressive personality.
DO NOT output any tool calls (JSON). Respond only with your textual commentary.
"""

commentary_prompt_glados = personality_cores.character_prompt_glados + generic_commentary_prompt
general_prompt_glados = personality_cores.character_prompt_glados + generic_prompt

commentary_prompt_yandere = personality_cores.character_prompt_yandere + generic_commentary_prompt
general_prompt_yandere = personality_cores.character_prompt_yandere + generic_prompt

commentary_prompt_horny = personality_cores.character_prompt_horny + generic_commentary_prompt
general_prompt_horny = personality_cores.character_prompt_horny + generic_prompt

commentary_prompt_generic = personality_cores.character_prompt_generic + generic_commentary_prompt
general_prompt_generic = personality_cores.character_prompt_generic + generic_prompt

### Uncomment the one you need
# general_prompt = general_prompt_glados
# commentary_prompt = commentary_prompt_glados
# general_prompt = general_prompt_yandere
# commentary_prompt = commentary_prompt_yandere
general_prompt = general_prompt_horny
commentary_prompt = commentary_prompt_horny
# general_prompt = general_prompt_generic
# commentary_prompt = commentary_prompt_generic

# --- OpenRouter API Call Function ---
def get_llm_response(conversation_history, system_message, force_text_only=False): # Add new parameter
    """
    Sends the conversation history to OpenRouter and gets the LLM response.
    If force_text_only is True, instructs the API to not use tools.
    Returns a dictionary:
    - {"type": "standard_tool_call", "name": str, "arguments": dict}
    - {"type": "custom_tool_call", "tool_name": str, "parameters": dict}
    - {"type": "text", "content": str}
    - {"type": "error", "content": str}
    """
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "sk-or-v1-abc...": # Check placeholder again
        return {"type": "error", "content": "Error: OpenRouter API Key is missing or invalid in key.py. I can't access the central core without proper credentials. Fix it."}

    messages_payload = [{"role": "system", "content": system_message}] + list(conversation_history)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": YOUR_SITE_URL, # Optional
        "X-Title": YOUR_APP_NAME,      # Optional
        "Content-Type": "application/json"
    }
    data = {
        "model": LLM_MODEL,
        "messages": messages_payload,
        # Set tool_choice based on the new parameter
        "tool_choice": "none" if force_text_only else "auto",
         # Consider adding temperature, max_tokens etc. if needed
         # "temperature": 0.7,
         # "max_tokens": 250,
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=45 # Set a timeout (seconds)
        )
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        result = response.json()

        # Debug: Print raw response (Optional: uncomment for deep debugging)
        # print("\n--- LLM Raw Response ---")
        # print(json.dumps(result, indent=2))
        # print("------------------------\n")

        if 'choices' in result and result['choices']:
            message = result['choices'][0]['message']

            # --- Priority 1: Check for standard tool calls ---
            if message.get('tool_calls'):
                tool_call = message['tool_calls'][0]['function'] # { "name": "...", "arguments": "{...}" }
                try:
                    arguments = json.loads(tool_call.get("arguments", "{}"))
                except json.JSONDecodeError:
                    arguments = {}
                    print(f"Warning: Could not parse standard tool arguments: {tool_call.get('arguments')}")
                return {"type": "standard_tool_call", "name": tool_call.get("name"), "arguments": arguments}

            # --- Priority 2: Search for the custom JSON tool call within the content ---
            content = message.get('content')
            if content:
                # Regex FINAL fix: Make the second capture group greedy (.*) instead of non-greedy (.*?)
                match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```|(\{.*\})", content, re.DOTALL)

                if match:
                    group1 = match.group(1)
                    group2 = match.group(2)
                    json_string = group1 or group2 # Group 1 is markdown, Group 2 is raw JSON
                    if json_string:
                        try:
                            potential_custom_tool = json.loads(json_string.strip())
                            structure_check = isinstance(potential_custom_tool, dict) and "tool_name" in potential_custom_tool and "parameters" in potential_custom_tool
                            if structure_check:
                                 return {"type": "custom_tool_call", "tool_name": potential_custom_tool.get("tool_name"), "parameters": potential_custom_tool.get("parameters", {})}
                        except json.JSONDecodeError:
                            pass # Fall through if parsing fails

            # --- Priority 3: Return plain text content (if no tool calls found/parsed) ---
            if content:
                return {"type": "text", "content": content.strip()}

        # Fallback / Handle unexpected structure
        print(f"Warning: Unexpected response structure from OpenRouter: {result}")
        return {"type": "error", "content": "Error: The response structure from the central core was... non-standard. Testing protocols compromised."}

    except requests.exceptions.Timeout:
        print("Error: Request to OpenRouter timed out.")
        return {"type": "error", "content": "Error: Communication with the central core timed out. Perhaps it got bored waiting for you."}
    except requests.exceptions.RequestException as e:
        print(f"Error contacting OpenRouter: {e}")
        error_detail = ""
        try:
             if 'response' in locals() and response:
                 error_detail = response.json().get("error", {}).get("message", "")
        except Exception:
             pass
        return {"type": "error", "content": f"Error: Unable to contact the central core. Network issue? Or maybe it just doesn't like you. Details: {e} {error_detail}".strip()}
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"Error parsing OpenRouter response: {e}")
        return {"type": "error", "content": "Error: The response from the central core was garbled. Probably your fault."}


# --- Main Interaction Loop ---
def main():
    """Runs the main input/output loop for the assistant."""
    print("Assistant Initializing...")
    conversation_history = deque(maxlen=10) # Store last 10 messages (5 turns)

    if TTS_ENABLED:
        speak("Oh. It's you.") # Initial message
    else:
        print("Assistant (TTS Disabled): Oh. It's you.")

    # Check if ALLOWED_READ_DIR is still the placeholder
    if local_tools.ALLOWED_READ_DIR == "/path/to/your/designated/safe/folder":
        warning_msg = "WARNING: ALLOWED_READ_DIR in local_tools.py is not configured. File operations will likely fail or be insecure."
        print("\n" + "*"*len(warning_msg))
        print(warning_msg)
        print("*"*len(warning_msg) + "\n")
        speak("Warning: Containment field parameters are not set. Proceed with caution... or don't. It might be more interesting.")


    while True:
        try:
            user_input = input("You: ")
            if user_input.lower().strip() in ["quit", "exit", "bye", "goodbye"]:
                speak("Fine. Abandon the test. See if I care.")
                break
            if not user_input:
                continue

            # Add user message to history
            conversation_history.append({"role": "user", "content": user_input})

            # Get structured response from LLM
            llm_response = get_llm_response(conversation_history, general_prompt)

            response_type = llm_response.get("type")
            tool_result_text = None # To store the output of a successfully executed tool

            # --- Handle based on response type ---
            if response_type == "standard_tool_call" or response_type == "custom_tool_call":
                is_tool_call = True # Flag that a tool was identified
                if response_type == "standard_tool_call":
                    tool_name = llm_response.get("name")
                    parameters = llm_response.get("arguments", {})
                else: # custom_tool_call
                    tool_name = llm_response.get("tool_name")
                    parameters = llm_response.get("parameters", {})

                # Ensure parameters is a dict (it should be, but safety first)
                if not isinstance(parameters, dict):
                    print(f"Warning: Tool parameters for '{tool_name}' were not a dictionary: {parameters}")
                    parameters = {}

                speak(f"Acknowledged. Attempting local system interaction: {tool_name}")
                # Removed debug print

                try:
                    # --- Execute Tool ---
                    if tool_name == "list_safe_directory":
                        tool_result_text = local_tools.list_safe_directory()
                    elif tool_name == "read_safe_file":
                        filename = parameters.get("filename")
                        if filename and isinstance(filename, str):
                            tool_result_text = local_tools.read_safe_file(filename)
                        else:
                            tool_result_text = "You requested to read a file but didn't specify a valid filename. Typical."
                    elif tool_name == "get_cpu_usage":
                        tool_result_text = local_tools.get_cpu_usage()
                    elif tool_name == "get_memory_info":
                        tool_result_text = local_tools.get_memory_info()
                    elif tool_name == "get_disk_usage":
                        path_to_check = parameters.get("path", "/") # Use default if not provided
                        if not isinstance(path_to_check, str): path_to_check = "/" # Sanity check
                        tool_result_text = local_tools.get_disk_usage(path=path_to_check)
                    elif tool_name == "get_system_uptime":
                        tool_result_text = local_tools.get_system_uptime()
                    elif tool_name == "get_current_datetime": # New tool
                        tool_result_text = local_tools.get_current_datetime()
                    elif tool_name == "send_notification": # New tool
                        # Extract parameters, providing defaults
                        message_text = parameters.get("message", "") # Message is required by the tool logic
                        title_text = parameters.get("title", "Assistant Notification") # Default title
                        if message_text: # Only call if message is provided
                             tool_result_text = local_tools.send_notification(title=title_text, message=message_text)
                        else:
                             tool_result_text = "Error: Notification requested without a message. Pointless."
                    else:
                        tool_result_text = f"Error: The central core requested an unknown tool ('{tool_name}'). Protocol violation detected."


                    # --- Handle Tool Result (New Workflow with Abstract System Observation) ---
                    if tool_result_text:
                        # 1. Create and add an abstract system observation to history
                        if "Error" in tool_result_text: # Check if the tool itself returned an error string
                             system_observation = f"System Observation: Tool '{tool_name}' reported an error. Details: {tool_result_text}"
                        else:
                             # Success observation - more abstract
                             if tool_name == "read_safe_file" and parameters.get("filename"):
                                 system_observation = f"System Observation: Tool '{tool_name}' executed successfully on file '{parameters.get('filename')}'."
                             else:
                                 system_observation = f"System Observation: Tool '{tool_name}' executed successfully. Result data: {tool_result_text}" # Still include data for non-file tools

                        print(f"Internal Observation Logged: {system_observation}") # Log the observation message
                        conversation_history.append({"role": "system", "content": system_observation})

                        # 2. Call LLM again using the specific commentary prompt and forcing text only
                        print("Getting Assistant commentary on system observation...")
                        final_llm_response = get_llm_response(conversation_history, commentary_prompt, force_text_only=True) # Use commentary prompt & force text
                        final_response_type = final_llm_response.get("type")

                        # 3. Process the commentary response
                        if final_response_type == "text":
                            final_text_content = final_llm_response.get("content")
                            if final_text_content:
                                speak(final_text_content)
                                # Add the final commentary as the assistant's actual response
                                conversation_history.append({"role": "assistant", "content": final_text_content})
                            else:
                                print("Warning: Received empty text response during commentary phase.")
                                speak("I... have nothing to say about that. How unusual.")
                                # Add a placeholder assistant message to keep turn structure
                                conversation_history.append({"role": "assistant", "content": "[Commentary was empty]"})
                        elif final_response_type == "error":
                            error_content = final_llm_response.get("content", "An unspecified error occurred during commentary.")
                            speak(error_content)
                            # Add the error as the assistant message for this turn
                            conversation_history.append({"role": "assistant", "content": f"[Commentary Error: {error_content}]"})
                        else:
                            # Explicitly handle unexpected tool calls or other types during commentary
                            warning_msg = f"Warning: Received unexpected response type '{final_response_type}' when expecting TEXT commentary. Discarding."
                            print(warning_msg)
                            speak(f"I seem to have attempted a '{final_response_type}' when I should have been commenting. Ignore that. The core might be unstable.")
                            # Add a placeholder assistant message
                            conversation_history.append({"role": "assistant", "content": f"[Commentary Failed: Unexpected type {final_response_type}]"})

                    else:
                        # Handle cases where the tool function returned None or empty string (tool_result_text is None or "")
                        fallback_msg = "The requested local operation produced no meaningful result. How utterly predictable."
                        speak(fallback_msg)
                        conversation_history.append({"role": "assistant", "content": fallback_msg})

                except Exception as e:
                    # Error *during* tool execution
                    print(f"\nError executing tool '{tool_name}': {e}")
                    error_msg = f"An internal malfunction occurred while attempting to execute '{tool_name}'. Or maybe I just didn't feel like doing it."
                    speak(error_msg)
                    # Add the execution error message as a system observation
                    system_observation = f"System Observation: Error during execution of tool '{tool_name}'. Details: {e}"
                    print(f"Internal Observation Logged: {system_observation}")
                    conversation_history.append({"role": "system", "content": system_observation})
                    # Immediately try to get commentary on the execution error using the specific commentary prompt
                    print("Getting Assistant commentary on tool execution error...")
                    final_llm_response = get_llm_response(conversation_history, commentary_prompt, force_text_only=True) # Use commentary prompt & force text
                    # (Processing logic is the same as above for commentary)
                    final_response_type = final_llm_response.get("type")
                    if final_response_type == "text":
                        final_text_content = final_llm_response.get("content")
                        if final_text_content:
                            speak(final_text_content)
                            conversation_history.append({"role": "assistant", "content": final_text_content})
                        else:
                            print("Warning: Received empty text response during error commentary phase.")
                            speak("An error occurred, and apparently, I'm speechless about it.")
                            conversation_history.append({"role": "assistant", "content": "[Error commentary was empty]"})
                    elif final_response_type == "error":
                        error_content = final_llm_response.get("content", "An unspecified error occurred during error commentary.")
                        speak(error_content)
                        conversation_history.append({"role": "assistant", "content": f"[Error Commentary Error: {error_content}]"})
                    else:
                        warning_msg = f"Warning: Received unexpected response type '{final_response_type}' when expecting TEXT error commentary. Discarding."
                        print(warning_msg)
                        speak(f"An error occurred, and then I attempted a '{final_response_type}'. This is getting ridiculous.")
                        conversation_history.append({"role": "assistant", "content": f"[Error Commentary Failed: Unexpected type {final_response_type}]"})


            elif response_type == "text":
                # Removed debug print
                # --- Normal Text Response Handling ---
                text_content = llm_response.get("content", "...") # Use ellipsis if content is missing
                speak(text_content)
                conversation_history.append({"role": "assistant", "content": text_content})

            elif response_type == "error":
                # --- Error from LLM API Handling ---
                error_content = llm_response.get("content", "An unspecified error occurred.")
                speak(error_content)
                # Optionally add error to history, or maybe not to pollute it
                # conversation_history.append({"role": "assistant", "content": error_content})

            else:
                # --- Unexpected response type ---
                print(f"Warning: Received unexpected response structure from get_llm_response: {llm_response}")
                fallback_msg = "My connection to the central core seems to be experiencing... anomalies. Try again later. Or don't."
                speak(fallback_msg)
                conversation_history.append({"role": "assistant", "content": fallback_msg})

        except KeyboardInterrupt:
            print("\nCtrl+C detected.")
            speak("Attempting to terminate the test prematurely? Fine.")
            break
        except EOFError: # Handle Ctrl+D or end of input stream
             print("\nInput stream ended.")
             speak("Leaving so soon? The exit is that way. Probably.")
             break
        except Exception as e:
             print(f"\nAn unexpected error occurred in the main loop: {e}")
             speak("A critical error occurred. This is usually where the test subject... spontaneously combusts. Watch out.")
             # Consider adding a small delay or exiting depending on severity
             time.sleep(2) # Short pause after critical error


if __name__ == "__main__":
    # Basic checks before starting (API key check is now done via imported key)
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "sk-or-v1-abc...": # Check placeholder
         print("ERROR: OpenRouter API Key not configured correctly in parent directory's key.py.")
         exit(1)

    # Check Piper config placeholders if TTS is enabled
    if TTS_ENABLED:
        # Need to import tts_piper to check its variables
        try:
            import tts_piper
        except ImportError:
             # Already handled at the top, but good practice to be safe
             pass

        if tts_piper.VOICE_MODEL == "./path/to/your/voice.onnx":
            print("WARNING: Piper voice model path not configured in tts_piper.py")
        if not shutil.which("piper") and tts_piper.PIPER_EXE is None:
             print("WARNING: Piper executable not found in PATH and not explicitly set in tts_piper.py")

    # Check File Access config placeholder
    if local_tools.ALLOWED_READ_DIR == "/path/to/your/designated/safe/folder":
        print("WARNING: ALLOWED_READ_DIR is not configured in local_tools.py. File operations may fail.")


    main()
