import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio
from google import genai
from concurrent.futures import TimeoutError
from functools import partial
import json

# Load environment variables from .env file
load_dotenv()

# Access your API key and initialize Gemini client correctly
api_key = "AIzaSyAbuQzXk74liwfGIbXEou3pdGUsqJZc1r0"
client = genai.Client(api_key=api_key)

# Get recipient email from environment variable
recipient_email = os.getenv('GMAIL_RECIPIENT')
if not recipient_email:
    raise ValueError("RECIPIENT_EMAIL not found in .env file")

max_iterations = 5  # Reduced maximum number of iterations
last_response = None
iteration = 0
iteration_response = []
stored_result = None  # Store final result (usually exponential sum)
ascii_values = None  # Store ASCII values for email body
exponential_sum = None  # Store exponential sum specifically
is_email_phase = False  # Track if we're in email phase
email_sent = False  # Track if email has been sent
retry_count = 0 # Re-introduce retry counter
max_retries = 3 # Define max retries

async def generate_with_timeout(client, prompt, timeout=10):
    """Generate content with a timeout"""
    print("Starting LLM generation...")
    try:
        # Add delay to respect rate limits
        await asyncio.sleep(5)  # Increase delay to 5 seconds between API calls
        
        # Convert the synchronous generate_content call to run in a thread
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None, 
                lambda: client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
            ),
            timeout=timeout
        )
        print("LLM generation completed")
        return response
    except TimeoutError:
        print("LLM generation timed out!")
        raise
    except Exception as e:
        print(f"Error in LLM generation: {e}")
        if "429" in str(e):  # Rate limit error
            print("Rate limit hit, waiting 60 seconds...")  # Increase wait time
            await asyncio.sleep(60)  # Wait longer for rate limit reset
            return await generate_with_timeout(client, prompt, timeout)  # Retry
        raise

def reset_state():
    """Reset all global variables to their initial state"""
    global last_response, iteration, iteration_response, stored_result, is_email_phase, email_sent, ascii_values, exponential_sum, retry_count
    last_response = None
    iteration = 0
    iteration_response = []
    stored_result = None
    ascii_values = None
    exponential_sum = None
    is_email_phase = False
    email_sent = False
    retry_count = 0 # Initialize retry_count

async def main():
    # Declare globals at the start of main
    global last_response, iteration, iteration_response, max_iterations, stored_result, is_email_phase, email_sent, ascii_values, exponential_sum, retry_count
    
    reset_state()  # Reset at the start of main
    print("Starting main execution...")
    try:
        # Create a single MCP server connection
        print("Establishing connection to MCP server...")
        server_params = StdioServerParameters(
            command="python",
            args=["example2-3.py"]
        )

        async with stdio_client(server_params) as (read, write):
            print("Connection established, creating session...")
            async with ClientSession(read, write) as session:
                print("Session created, initializing...")
                await session.initialize()
                
                # Get available tools
                print("Requesting tool list...")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                print(f"Successfully retrieved {len(tools)} tools")

                # Create system prompt with available tools
                print("Creating system prompt...")
                print(f"Number of tools: {len(tools)}")
                
                try:
                    tools_description = []
                    for i, tool in enumerate(tools):
                        try:
                            # Get tool properties
                            params = tool.inputSchema
                            desc = getattr(tool, 'description', 'No description available')
                            name = getattr(tool, 'name', f'tool_{i}')
                            
                            # Format the input schema in a more readable way
                            if 'properties' in params:
                                param_details = []
                                for param_name, param_info in params['properties'].items():
                                    param_type = param_info.get('type', 'unknown')
                                    param_details.append(f"{param_name}: {param_type}")
                                params_str = ', '.join(param_details)
                            else:
                                params_str = 'no parameters'

                            tool_desc = f"{i+1}. {name}({params_str}) - {desc}"
                            tools_description.append(tool_desc)
                            print(f"Added description for tool: {tool_desc}")
                        except Exception as e:
                            print(f"Error processing tool {i}: {e}")
                            tools_description.append(f"{i+1}. Error processing tool")
                    
                    tools_description = "\n".join(tools_description)
                    print("Successfully created tools description")
                except Exception as e:
                    print(f"Error creating tools description: {e}")
                    tools_description = "Error loading tools"
                
                print("Created system prompt...")
                
                system_prompt = f"""You are an AI assistant that calculates ASCII values and sends the result via email. You have access to various tools.

Available tools:
{tools_description}

You must respond with EXACTLY ONE line in one of these formats (no additional text):
1. For function calls:
   FUNCTION_CALL: function_name|param1|param2|...
   
2. For final ASCII calculation:
   FINAL_ANSWER: [number]

Task sequence:
1. ASCII Calculation Phase (INITIAL):
   - Convert input text into ASCII values.
   - Tag each reasoning step (e.g., [lookup], [arithmetic]).
   - Calculate the exponential sum of these values.
   - Perform a self-check to verify the sum (e.g., compare against a recomputed value).
   - If unsure or mismatch is detected, return FUNCTION_CALL: retry|reason and reattempt.
   - Return the final sum with FINAL_ANSWER format only if confident.
   - After FINAL_ANSWER is given, this phase ends permanently.

2. Email Operations Phase (AFTER FINAL_ANSWER):
   - This phase begins ONLY after FINAL_ANSWER is provided.
   - You must NEVER return FINAL_ANSWER in this phase.
   - You must identify and use the 'send_gmail' tool.
   - The email should contain:
     * Subject: "ASCII Calculation Result"
     * Recipient: {recipient_email}
     * Body: Include the previously calculated result (handled by the calling code).
   - Call the 'send_gmail' tool with the correct recipient, subject, and a placeholder message (like 'Result calculated').
   - If the email fails to send, retry using FUNCTION_CALL: retry_email|reason until successful.

Phase Transition Rules:
- Once FINAL_ANSWER is given, you MUST move to the email phase.
- In the email phase, you MUST use the 'send_gmail' tool only.
- NEVER recalculate ASCII values after FINAL_ANSWER.
- NEVER return FINAL_ANSWER during the email phase.

Important:
- Execute one operation at a time.
- All email communications must go to {recipient_email}.
- Always sanity-check your calculations and verify tool outputs.
- If a tool call fails or you're unsure of the next step, use FUNCTION_CALL: retry|reason.

Examples:
ASCII Phase:
Input: "Calculate ASCII values for INDIA"
- FUNCTION_CALL: strings_to_chars_to_int|INDIA  [lookup]
- FUNCTION_CALL: int_list_to_exponential_sum|[73,78,68,73,65]  [arithmetic]
- FINAL_ANSWER: [42]

Email Phase:
Input: "Result is 42, send via email"
- FUNCTION_CALL: send_gmail|{recipient_email}|ASCII Calculation Result|Result calculated

DO NOT include any explanations or additional text.
Your entire response should be a single line starting with either FUNCTION_CALL: or FINAL_ANSWER:"""

                query = """Find the ASCII values of characters in INDIA, calculate sum of exponentials, then send the result via email."""
                print("Starting iteration loop...")
                
                while iteration < max_iterations:
                    print(f"\n--- Iteration {iteration + 1} ---")
                    if last_response is None:
                        if is_email_phase:
                            current_query = f"Send the ASCII calculation result ({stored_result}) via email to {recipient_email}"
                        else:
                            current_query = query
                    else:
                        if is_email_phase:
                            current_query = f"Send the ASCII calculation result ({stored_result}) via email to {recipient_email}"
                        else:
                            current_query = current_query + "\n\n" + " ".join(iteration_response)
                            current_query = current_query + "  What should I do next?"

                    # Get model's response with timeout
                    print("Preparing to generate LLM response...")
                    prompt = f"{system_prompt}\n\nQuery: {current_query}"
                    if is_email_phase:
                        prompt += "\nCURRENT_PHASE: EMAIL_OPERATIONS"
                    else:
                        prompt += "\nCURRENT_PHASE: ASCII_CALCULATION"
                    
                    try:
                        response = await generate_with_timeout(client, prompt)
                        response_text = response.text.strip()
                        print(f"LLM Response: {response_text}")
                        
                        # Find the FUNCTION_CALL line in the response
                        for line in response_text.split('\n'):
                            line = line.strip()
                            if line.startswith("FUNCTION_CALL:") or line.startswith("FINAL_ANSWER:"):
                                response_text = line
                                break
                        
                    except Exception as e:
                        print(f"Failed to get LLM response: {e}")
                        break

                    if response_text.startswith("FUNCTION_CALL:"):
                        _, function_info = response_text.split(":", 1)
                        parts = [p.strip() for p in function_info.split("|")]
                        func_name, params = parts[0], parts[1:]
                        
                        # Handle retry commands from LLM
                        if func_name == "retry":
                            retry_count += 1
                            if retry_count > max_retries:
                                print(f"\n=== Maximum retries ({max_retries}) exceeded for general retry. Aborting. ===")
                                # Potentially add a more specific error message to current_query
                                break # Exit loop if too many general retries
                            reason = params[0] if params else "unspecified reason"
                            print(f"\n=== LLM requested retry: {reason} (Attempt {retry_count}/{max_retries}) ===")
                            # Reset last response to potentially force recalculation or different approach by LLM
                            last_response = None 
                            iteration_response.append(f"Retry requested by LLM: {reason}")
                            continue # Ask LLM again
                            
                        # Handle retry_email command from LLM
                        if func_name == "retry_email" and is_email_phase:
                            retry_count += 1
                            if retry_count > max_retries:
                                print(f"\n=== Maximum email retries ({max_retries}) exceeded. Aborting. ===")
                                break # Exit loop if email cannot be sent
                            reason = params[0] if params else "unspecified reason"
                            print(f"\n=== LLM requested email retry: {reason} (Attempt {retry_count}/{max_retries}) ===")
                            # Prepare query to specifically ask for email retry
                            current_query = f"Previous email attempt failed ({reason}). Please try sending the email again with result {exponential_sum} to {recipient_email}. Call 'send_gmail' like: FUNCTION_CALL: send_gmail|{recipient_email}|ASCII Calculation Result|Result calculated"
                            iteration_response.append(f"Email retry requested by LLM: {reason}")
                            continue # Ask LLM again for email
                        
                        # Reset retry count if a non-retry function is called successfully
                        # (This happens implicitly before the tool call if it's send_gmail, 
                        # and after successful execution for other tools - let's ensure it resets)
                        # if func_name not in ["retry", "retry_email"]:
                        #      retry_count = 0 # Reset on successful non-retry step (Consider placement)

                        # Skip ASCII calculations if we're in email phase
                        if is_email_phase:
                            if func_name != "send_gmail":
                                print(f"DEBUG: Expected send_gmail in email phase, but got {func_name}. Asking LLM to use send_gmail.")
                                current_query = f"We are in EMAIL_OPERATIONS phase. The ASCII calculation is complete ({exponential_sum}). You MUST use the 'send_gmail' tool to send this result to {recipient_email}. Call it like: FUNCTION_CALL: send_gmail|{recipient_email}|ASCII Calculation Result|Result calculated"
                                continue
                            else:
                                print("Attempting to send email...")
                                retry_count = 0  # Reset email retry count specifically before trying to send
                                
                        # Store calculation for self-checking if it's an ASCII calculation
                        if func_name == "strings_to_chars_to_int" or func_name == "int_list_to_exponential_sum":
                            last_calculation = (func_name, params)

                        print(f"\nDEBUG: Raw function info: {function_info}")
                        print(f"DEBUG: Split parts: {parts}")
                        print(f"DEBUG: Function name: {func_name}")
                        print(f"DEBUG: Raw parameters: {params}")
                        
                        try:
                            # Find the matching tool to get its input schema
                            tool = next((t for t in tools if t.name == func_name), None)
                            if not tool:
                                print(f"DEBUG: Available tools: {[t.name for t in tools]}")
                                raise ValueError(f"Unknown tool: {func_name}")

                            print(f"DEBUG: Found tool: {tool.name}")
                            print(f"DEBUG: Tool schema: {tool.inputSchema}")

                            # Prepare arguments according to the tool's input schema
                            arguments = {}
                            schema_properties = tool.inputSchema.get('properties', {})
                            print(f"DEBUG: Schema properties: {schema_properties}")

                            for param_name, param_info in schema_properties.items():
                                if not params:  # Check if we have enough parameters
                                    raise ValueError(f"Not enough parameters provided for {func_name}")
                                    
                                value = params.pop(0)  # Get and remove the first parameter
                                param_type = param_info.get('type', 'string')
                                
                                print(f"DEBUG: Converting parameter {param_name} with value {value} to type {param_type}")
                                
                                # Standard type conversion
                                if param_type == 'integer':
                                    arguments[param_name] = int(value)
                                elif param_type == 'number':
                                    arguments[param_name] = float(value)
                                elif param_type == 'array':
                                    if isinstance(value, str):
                                        value = value.strip('[]').split(',')
                                    arguments[param_name] = [int(x.strip()) for x in value]
                                else:
                                    arguments[param_name] = str(value)

                            print(f"DEBUG: Final arguments: {arguments}")
                            print(f"DEBUG: Calling tool {func_name}")
                            
                            # Special handling for send_gmail arguments
                            if is_email_phase and func_name == "send_gmail":
                                message_body = (
                                    f"ASCII Calculation Results for 'INDIA':\n\n"
                                    f"1. ASCII Values: {ascii_values}\n"
                                    f"2. Sum of Exponentials: {exponential_sum}\n"
                                )
                                arguments = {
                                    "recipient_email": recipient_email,
                                    "subject": "ASCII Calculation Result",
                                    "message": message_body
                                }
                                print(f"DEBUG: Updated arguments for send_gmail: {arguments}")
                            
                            result = await session.call_tool(func_name, arguments=arguments)
                            print(f"DEBUG: Raw result: {result}")
                            
                            # Get the full result content
                            if hasattr(result, 'content'):
                                print(f"DEBUG: Result has content attribute")
                                # Handle multiple content items
                                if isinstance(result.content, list):
                                    iteration_result = [
                                        item.text if hasattr(item, 'text') else str(item)
                                        for item in result.content
                                    ]
                                else:
                                    iteration_result = str(result.content)
                            else:
                                print(f"DEBUG: Result has no content attribute")
                                iteration_result = str(result)
                                
                            print(f"DEBUG: Final iteration result: {iteration_result}")

                            # Format the response based on result type
                            if isinstance(iteration_result, list):
                                try:
                                    # Try to parse the JSON response
                                    parsed_result = json.loads(iteration_result[0])
                                    if isinstance(parsed_result, dict) and 'content' in parsed_result:
                                        content_list = parsed_result['content']
                                        if isinstance(content_list, list) and content_list:
                                            result_str = content_list[0].get('text', '')
                                        else:
                                            result_str = str(content_list)
                                    else:
                                        result_str = f"[{', '.join(iteration_result)}]"
                                except json.JSONDecodeError:
                                    result_str = f"[{', '.join(iteration_result)}]"
                                except Exception as e:
                                    print(f"Error parsing result: {e}")
                                    result_str = str(iteration_result)
                            else:
                                result_str = str(iteration_result)
                            
                            print(f"\nDEBUG: Parsed result string: {result_str}")

                            # Store results based on function type AFTER formatting result_str
                            if func_name == "strings_to_chars_to_int":
                                ascii_values = result_str
                                print(f"DEBUG: Stored ascii_values: {ascii_values}")
                            # Removed incorrect assignment for exponential_sum here
                            
                            # Add the result to iteration_response with reasoning tag if provided
                            reasoning_tag = ""
                            # Extract reasoning tag if present (e.g., FUNCTION_CALL: name|params [tag])
                            if "[" in function_info and "]" in function_info:
                                try:
                                    tag_part = function_info.split("[", 1)[1]
                                    reasoning_tag = "[" + tag_part.split("]", 1)[0] + "]"
                                except IndexError:
                                    pass # Ignore if parsing fails

                            iteration_response.append(
                                f"In the {iteration + 1} iteration you called {func_name} with {arguments} parameters {reasoning_tag}, "
                                f"and the function returned {result_str}."
                            )
                            
                            # Update last_response
                            last_response = iteration_result
                            
                            # Check if email was sent successfully and break the loop
                            if is_email_phase and func_name == "send_gmail":
                                success_found = False
                                try:
                                    # Attempt to parse the JSON structure common for tool results
                                    if isinstance(iteration_result, list) and iteration_result:
                                        # Handle potential JSON string within the list
                                        if isinstance(iteration_result[0], str):
                                            try:
                                                parsed = json.loads(iteration_result[0])
                                                if isinstance(parsed, dict) and 'content' in parsed and isinstance(parsed['content'], list) and parsed['content']:
                                                   inner_text = parsed['content'][0].get('text', '')
                                                   if "successfully" in inner_text.lower():
                                                       success_found = True
                                            except json.JSONDecodeError:
                                                # If not JSON, check the raw string
                                                if "successfully" in iteration_result[0].lower():
                                                    success_found = True
                                        # Check plain strings in the list
                                        elif isinstance(iteration_result[0], dict) and 'text' in iteration_result[0]:
                                             if "successfully" in iteration_result[0]['text'].lower():
                                                 success_found = True
                                    # Handle simple string result
                                    elif isinstance(iteration_result, str):
                                         if "successfully" in iteration_result.lower():
                                             success_found = True
                                             
                                    # Also check the formatted result_str just in case
                                    if not success_found and "successfully" in result_str.lower():
                                        print("DEBUG: Success detected in formatted result_str")
                                        success_found = True
                                        
                                except Exception as parse_err:
                                    print(f"DEBUG: Error parsing email success message: {parse_err}")
                                    # Fallback: check the raw formatted string
                                    if "successfully" in result_str.lower():
                                        success_found = True

                                if success_found:
                                    print("\n=== Email Sent Successfully ===")
                                    email_sent = True
                                    break  # Exit the loop after successful email

                        except Exception as e:
                            print(f"DEBUG: Error details: {str(e)}")
                            print(f"DEBUG: Error type: {type(e)}")
                            import traceback
                            traceback.print_exc()
                            if is_email_phase:
                                current_query = f"Error sending email: {str(e)}. Please try sending the email again with the result {stored_result}."
                            else:
                                current_query = f"An error occurred: {str(e)}. According to the task sequence, what should we do next?"
                            continue

                    elif response_text.startswith("FINAL_ANSWER:"):
                        if is_email_phase:
                            print("\n=== ERROR: Received FINAL_ANSWER in email phase ===")
                            current_query = f"We are in EMAIL_OPERATIONS phase. FINAL_ANSWER is not allowed. Please use an email tool to send the result {stored_result} to {recipient_email}"
                            continue
                        
                        print("\n=== ASCII Calculation Complete ===")
                        stored_result = response_text.split(":")[1].strip().strip('[]')  # Remove brackets from stored result
                        exponential_sum = stored_result  # Store the final exponential sum - THIS IS THE CORRECT PLACE
                        print(f"DEBUG: Stored exponential_sum: {exponential_sum}")
                        is_email_phase = True  # Set email phase flag
                        
                        # Clear previous responses to avoid confusion
                        iteration_response = []
                        last_response = None
                        
                        # Update the query to start email operation with recipient
                        current_query = f"We are now in EMAIL_OPERATIONS phase. Send the ASCII calculation result ({stored_result}) via email to {recipient_email}"
                        continue
                    
                    iteration += 1

                if not email_sent:
                    print("\n=== Maximum iterations reached without sending email ===")

    except Exception as e:
        print(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        reset_state()  # Reset at the end of main

if __name__ == "__main__":
    asyncio.run(main())
    
    
