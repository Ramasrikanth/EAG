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

max_iterations = 10  # Increased to allow for all operations
last_response = None
iteration = 0
iteration_response = []
is_paint_phase = False
stored_result = None  # Add this to store ASCII result
paint_state = "start"  # Add this to track Paint operation state

async def generate_with_timeout(client, prompt, timeout=10):
    """Generate content with a timeout"""
    print("Starting LLM generation...")
    try:
        # Add delay to respect rate limits
        await asyncio.sleep(3)  # Add 3-second delay between API calls
        
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
            print("Rate limit hit, waiting 40 seconds...")
            await asyncio.sleep(40)  # Wait for rate limit reset
            return await generate_with_timeout(client, prompt, timeout)  # Retry
        raise

def reset_state():
    """Reset all global variables to their initial state"""
    global last_response, iteration, iteration_response, is_paint_phase, stored_result, paint_state
    last_response = None
    iteration = 0
    iteration_response = []
    is_paint_phase = False
    stored_result = None
    paint_state = "start"

async def main():
    # Declare globals at the start of main
    global last_response, iteration, iteration_response, max_iterations, is_paint_phase, stored_result, paint_state
    
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
                    # First, let's inspect what a tool object looks like
                    # if tools:
                    #     print(f"First tool properties: {dir(tools[0])}")
                    #     print(f"First tool example: {tools[0]}")
                    
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
                
                system_prompt = f"""You are an AI assistant that solves math problems and helps with drawing in Paint. You have access to various tools.

Available tools:
{tools_description}

You must respond with EXACTLY ONE line in one of these formats (no additional text):
1. For function calls:
   FUNCTION_CALL: function_name|param1|param2|...
   
2. For final ASCII calculation:
   FINAL_ANSWER: [number]

Task sequence:
1. ASCII Calculation Phase:
   - Get ASCII values using strings_to_chars_to_int
   - Calculate exponential sum using int_list_to_exponential_sum
   - Return the final sum with FINAL_ANSWER

2. Paint Operations Phase (after FINAL_ANSWER):
   Step 1: Launch Graphics Editor
   - First, you need to launch a graphics editor window on the secondary monitor
   - Wait for confirmation that the window is open and maximized
   
   Step 2: Create Shape
   - Once the editor is open, create a rectangular shape
   - The shape should be positioned at coordinates (545,310) for top-left corner
   - And extend to coordinates (956,503) for bottom-right corner
   - Wait for confirmation that the shape is drawn
   
   Step 3: Insert Result
   - After the shape is created, insert the ASCII calculation result as text
   - The text should appear inside the rectangular shape
   - This completes the sequence

Important:
- Execute one operation at a time
- Wait for success confirmation before proceeding
- Use FINAL_ANSWER only for ASCII calculation result
- For Paint operations, always use FUNCTION_CALL
- Proceed to next step only after success message
- If operation fails, retry the same operation
- Success is indicated by "successfully" in result

Examples:
For ASCII calculation:
Input: "Calculate ASCII values for INDIA"
- FUNCTION_CALL: strings_to_chars_to_int|INDIA
- FUNCTION_CALL: int_list_to_exponential_sum|[73,78,68,73,65]
- FINAL_ANSWER: [42]

For Graphics Editor operations:
Input: "ASCII calculation result is 42. Based on the task sequence, what should we do first?"
Response: "I need to launch the graphics editor window"
- The assistant determines how to launch the editor

Input: "Graphics editor window opened successfully. What's the next step?"
Response: "I need to create a rectangular shape at position (545,310) to (956,503)"
- The assistant determines how to draw the shape

Input: "Shape has been drawn successfully. What should we do next?"
Response: "I need to insert the calculation result (42) as text inside the shape"
- The assistant determines how to add the text

DO NOT include any explanations or additional text.
Your entire response should be a single line starting with either FUNCTION_CALL: or FINAL_ANSWER:"""

                query = """Find the ASCII values of characters in INDIA, calculate sum of exponentials, then draw a rectangle in Paint and add the result as text."""
                print("Starting iteration loop...")
                
                while iteration < max_iterations:
                    print(f"\n--- Iteration {iteration + 1} ---")
                    if last_response is None:
                        if is_paint_phase:
                            if paint_state == "start":
                                current_query = "Please start Paint operations by using the open paint function."
                            elif paint_state == "draw":
                                current_query = "Paint is open. Now draw a rectangle using the coordinates 545,310,956,503"
                            elif paint_state == "text":
                                current_query = f"Rectangle is drawn. Now add the text '{stored_result}' inside the rectangle"
                        else:
                            current_query = query
                    else:
                        if is_paint_phase:
                            current_query = current_query  # Keep the Paint operation query
                        else:
                            current_query = current_query + "\n\n" + " ".join(iteration_response)
                            current_query = current_query + "  What should I do next?"

                    # Get model's response with timeout
                    print("Preparing to generate LLM response...")
                    prompt = f"{system_prompt}\n\nQuery: {current_query}"
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
                        
                        # Skip ASCII calculations if we're in paint phase
                        if is_paint_phase and (func_name == "strings_to_chars_to_int" or func_name == "int_list_to_exponential_sum"):
                            current_query = "We already have the ASCII calculation. Please use open paint to start Paint operations."
                            continue

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

                            # Special handling for draw_rectangle to properly parse coordinates
                            if func_name == "draw_rectangle":
                                # Combine all parameters into a single string and split by comma
                                coord_string = ",".join(params)
                                coords = [int(x.strip()) for x in coord_string.split(",")]
                                if len(coords) != 4:
                                    raise ValueError("draw_rectangle requires exactly 4 coordinates")
                                
                                # Assign coordinates to the correct parameters
                                arguments = {
                                    "x1": int(coords[0]),
                                    "y1": int(coords[1]),
                                    "x2": int(coords[2]),
                                    "y2": int(coords[3])
                                }
                            else:
                                for param_name, param_info in schema_properties.items():
                                    if not params:  # Check if we have enough parameters
                                        raise ValueError(f"Not enough parameters provided for {func_name}")
                                        
                                    value = params.pop(0)  # Get and remove the first parameter
                                    param_type = param_info.get('type', 'string')
                                    
                                    print(f"DEBUG: Converting parameter {param_name} with value {value} to type {param_type}")
                                    
                                    # Standard type conversion for other functions
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
                            
                            # Add the result to iteration_response for non-Paint operations
                            if not is_paint_phase:
                                iteration_response.append(
                                    f"In the {iteration + 1} iteration you called {func_name} with {arguments} parameters, "
                                    f"and the function returned {result_str}."
                                )
                            
                            # Update last_response
                            last_response = iteration_result
                            
                            # For Paint phase, report the operation result and let LLM decide next step
                            if is_paint_phase:
                                await asyncio.sleep(1)  # Brief pause between operations
                                
                                print(f"\nDEBUG: Current paint_state: {paint_state}")
                                print(f"DEBUG: Operation result: {result_str}")
                                
                                # More robust success detection with operation tracking
                                success = False
                                if "successfully" in result_str.lower():
                                    if "paint" in result_str.lower() and paint_state == "start":
                                        success = True
                                    elif paint_state == "text":
                                        success = True
                                # Special case for rectangle drawing
                                elif paint_state == "draw":
                                    # For rectangle, consider it successful even with the start_x error
                                    # since this error occurs after the rectangle is actually drawn
                                    if "start_x" in result_str:
                                        success = True
                                    # Also consider it successful if no critical errors
                                    elif not any(error in result_str.lower() for error in ["no such file", "failed", "invalid"]):
                                        success = True
                                
                                print(f"DEBUG: Operation success: {success}")
                                
                                if success:
                                    if paint_state == "start":
                                        paint_state = "draw"
                                        current_query = "Paint opened successfully. According to the task sequence, we need to draw a rectangle with coordinates 545,310,956,503"
                                    elif paint_state == "draw":
                                        paint_state = "text"
                                        current_query = f"Rectangle drawn successfully. According to the task sequence, we need to add text. The text should be: {stored_result}"
                                    elif paint_state == "text":
                                        print("\n=== All Paint Operations Completed Successfully ===")
                                        break  # Exit the loop after completing all operations
                                else:
                                    # If operation failed, create a state-specific retry message
                                    if paint_state == "start":
                                        current_query = "Paint operation was not successful. According to the task sequence, what should we try first?"
                                    elif paint_state == "draw":
                                        current_query = "Rectangle operation was not successful. According to the task sequence, we need to draw a rectangle with coordinates 545,310,956,503"
                                    elif paint_state == "text":
                                        current_query = f"Text operation was not successful. According to the task sequence, what text should we add? Remember to use: {stored_result}"
                                
                                last_response = None
                                continue

                        except Exception as e:
                            print(f"DEBUG: Error details: {str(e)}")
                            print(f"DEBUG: Error type: {type(e)}")
                            import traceback
                            traceback.print_exc()
                            current_query = f"An error occurred: {str(e)}. According to the task sequence, what should we do next?"
                            continue

                    elif response_text.startswith("FINAL_ANSWER:"):
                        print("\n=== ASCII Calculation Complete ===")
                        stored_result = response_text.split(":")[1].strip().strip('[]')  # Remove brackets from stored result
                        is_paint_phase = True  # Set paint phase flag
                        paint_state = "start"  # Initialize paint state
                        
                        # Clear previous responses to avoid confusion
                        iteration_response = []
                        last_response = None
                        
                        # Update the query to start Paint operations
                        current_query = f"ASCII calculation is complete with result {stored_result}. According to the task sequence, what is the first step we should perform?"
                        continue
                    
                    iteration += 1

    except Exception as e:
        print(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        reset_state()  # Reset at the end of main

if __name__ == "__main__":
    asyncio.run(main())
    
    
