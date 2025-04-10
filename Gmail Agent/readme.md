# ASCII Calculation and Email Workflow

This project demonstrates an AI-driven workflow that performs calculations on text input and sends the result via email. It uses Google's Gemini AI model orchestrated through an MCP (Modular Control Plane) client-server setup.

## Workflow Overview

The script `tal2gmail2.py` acts as the orchestrator (client) that interacts with both the Gemini LLM and an MCP server (running `example2-3.py`). The process follows these steps:

1.  **Initialization**:
    *   Loads environment variables (API keys, recipient email).
    *   Connects to the MCP server (`example2-3.py`) which provides specific calculation and email tools.
    *   Initializes the Gemini client.

2.  **ASCII Calculation Phase**:
    *   The orchestrator prompts the Gemini LLM with the task (e.g., "Find the ASCII values of characters in INDIA, calculate sum of exponentials...") and the list of available tools from the MCP server.
    *   The LLM decides which calculation tools to call (e.g., `strings_to_chars_to_int`, `int_list_to_exponential_sum`) and returns the function call instructions, potentially with reasoning tags (`[lookup]`, `[arithmetic]`).
    *   The orchestrator executes these tool calls via the MCP server.
    *   The LLM is instructed to perform self-checks and can request a retry (`FUNCTION_CALL: retry|reason`) if it's unsure about a calculation step.
    *   Once confident, the LLM returns the final exponential sum using the `FINAL_ANSWER: [number]` format.
    *   The orchestrator stores the intermediate ASCII values (from `strings_to_chars_to_int`) and the final exponential sum (from `FINAL_ANSWER`).

3.  **Email Operations Phase**:
    *   Upon receiving `FINAL_ANSWER`, the orchestrator transitions to the email phase.
    *   It prompts the LLM to send the result via email.
    *   The LLM is expected to call the `send_gmail` tool, providing recipient, subject, and a placeholder message (as instructed in the prompt).
    *   The orchestrator intercepts this call, replaces the placeholder message with the actual stored ASCII values and exponential sum, and then executes the `send_gmail` tool call via the MCP server with the complete arguments.
    *   The `send_gmail` tool (defined in `example2-3.py`) uses SMTP to send the email via Gmail.
    *   If the LLM detects an email sending failure (based on the tool's response), it can request a retry using `FUNCTION_CALL: retry_email|reason`.

4.  **Termination**:
    *   The loop terminates successfully once the `send_gmail` tool returns a success message (checked by the orchestrator).
    *   The loop also terminates if the maximum number of iterations (`max_iterations`) or retries (`max_retries`) is exceeded.

## Setup

1.  **Environment Variables**:
    *   Create a `.env` file in the same directory as the scripts.
    *   Add the following variables:
        ```dotenv
        # Recipient email address
        GMAIL_RECIPIENT=your_recipient_email@example.com

        # Gmail account to send *from*
        GMAIL_USER=your_sending_email@gmail.com

        # Gmail App Password (NOT your regular password)
        # See: https://support.google.com/accounts/answer/185833
        GMAIL_APP_PASSWORD=your_16_character_app_password
        ```
    *   Replace the placeholder values with your actual email addresses and generated App Password.

2.  **Dependencies**:
    *   Ensure you have the necessary Python libraries installed. You might need:
        ```bash
        pip install python-dotenv google-generativeai mcp-client Pillow pyautogui
        # Add any other specific dependencies used by example2-3.py (e.g., if image tools are used)
        ```
    *   Note: `pyautogui` might require additional system permissions, especially on macOS, to control the mouse and keyboard.

3.  **API Key**:
    *   The Google AI API key is currently hardcoded in `tal2gmail2.py`. For better security, it's recommended to load it from the `.env` file:
        *   Add `GOOGLE_API_KEY=your_google_ai_api_key` to your `.env` file.
        *   In `tal2gmail2.py`, change the API key line:
            ```python
            # Replace:
            # api_key = "AIzaSyAbuQzXk74liwfGIbXEou3pdGUsqJZc1r0"
            # With:
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in .env file")
            client = genai.Client(api_key=api_key)
            ```

## Running the Script

Execute the main orchestrator script from your terminal:

```bash
python tal2gmail2.py
```

This will automatically start the MCP server script (`example2-3.py`) as a subprocess and begin the workflow. Monitor the console output for debug messages and progress.

## Key Files

*   `tal2gmail2.py`: The main client orchestrator script managing the interaction with the LLM and MCP server.
*   `example2-3.py`: The MCP server script defining and providing the tools (calculation functions, `send_gmail`).
*   `.env`: File for storing sensitive credentials like email addresses, passwords, and API keys (you need to create this).
