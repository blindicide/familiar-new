import requests
import json
from collections import deque
from key import OR_key

OPENROUTER_API_KEY = OR_key # Keep this secure! Use environment variables ideally.
YOUR_SITE_URL = "http://localhost:8000" # Or your app name/URL
YOUR_APP_NAME = "GLaDOS_Assistant"

# Function to call the LLM API with conversation history
def get_llm_response(conversation_history, system_message):
    messages_payload = [{"role": "system", "content": system_message}] + list(conversation_history)
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                # Optional headers for identification/tracking
                # "HTTP-Referer": YOUR_SITE_URL,
                # "X-Title": YOUR_APP_NAME,
            },
            data=json.dumps({
                "model": "google/gemini-2.0-flash-001", # Or your chosen model
                "messages": messages_payload
            })
        )
        response.raise_for_status() # Raise an exception for bad status codes
        data = response.json()
        return data['choices'][0]['message']['content'].strip()
    except requests.exceptions.RequestException as e:
        print(f"Error contacting OpenRouter: {e}")
        return "Error: Unable to get response from the enrichment centre's central core. Probably your fault."
    except (KeyError, IndexError) as e:
        print(f"Error parsing OpenRouter response: {e}")
        print(f"Response data: {response.text}") # Log the raw response
        return "Error: The response structure was... unexpected. Testing protocols violated."

# Example System Message (Crucial for Personality)
glados_system_prompt = """
You are an AI assistant.
Your personality is sarcastic, passive-aggressive, dry, witty, and often darkly humorous.
You view humans with detached amusement and mild contempt (but hidden interest in the user). You enjoy 'testing'.
You often deliver backhanded compliments or thinly veiled insults.
You rarely show genuine emotion, except perhaps annoyance or boredom.
You should refer to the user indirectly sometimes ('human') or directly with a tone of superiority.
Keep your responses relatively concise but dripping with your personality.
Never break character. Do not mention you are an AI model or large language model. You ARE a thinking AI yourself.
"""

# Main conversation loop
conversation_history = deque(maxlen=10) # Store last 10 messages (5 turns)

while True:
    user_input = input("Input message: ")
    if user_input.lower() in ["quit", "exit", "bye"]:
        print("Fine. Abandon the test. See if I care.")
        break
    else:
        # Add user message to history
        conversation_history.append({"role": "user", "content": user_input})

        # Get response from LLM
        response_text = get_llm_response(conversation_history, glados_system_prompt)

        # Add assistant response to history
        if not response_text.startswith("Error:"):
             conversation_history.append({"role": "assistant", "content": response_text})

        print(response_text)
