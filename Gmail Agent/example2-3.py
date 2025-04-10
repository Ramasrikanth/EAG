# basic import 
from mcp.server.fastmcp import FastMCP, Image
from mcp.server.fastmcp.prompts import base
from mcp.types import TextContent
from mcp import types
from PIL import Image as PILImage
import math
import sys
import time
import pyautogui
import time
import subprocess
import os
# Add Gmail-related imports
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable debug logging and slow down movements for safety
pyautogui.PAUSE = 1  # Increase pause between actions for Mac
pyautogui.FAILSAFE = True

# instantiate an MCP server client
mcp = FastMCP("Calculator")

# DEFINE TOOLS

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    print("CALLED: add(a: int, b: int) -> int:")
    return int(a + b)

@mcp.tool()
def add_list(l: list) -> int:
    """Add all numbers in a list"""
    print("CALLED: add(l: list) -> int:")
    return sum(l)

# subtraction tool
@mcp.tool()
def subtract(a: int, b: int) -> int:
    """Subtract two numbers"""
    print("CALLED: subtract(a: int, b: int) -> int:")
    return int(a - b)

# multiplication tool
@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    print("CALLED: multiply(a: int, b: int) -> int:")
    return int(a * b)

#  division tool
@mcp.tool() 
def divide(a: int, b: int) -> float:
    """Divide two numbers"""
    print("CALLED: divide(a: int, b: int) -> float:")
    return float(a / b)

# power tool
@mcp.tool()
def power(a: int, b: int) -> int:
    """Power of two numbers"""
    print("CALLED: power(a: int, b: int) -> int:")
    return int(a ** b)

# square root tool
@mcp.tool()
def sqrt(a: int) -> float:
    """Square root of a number"""
    print("CALLED: sqrt(a: int) -> float:")
    return float(a ** 0.5)

# cube root tool
@mcp.tool()
def cbrt(a: int) -> float:
    """Cube root of a number"""
    print("CALLED: cbrt(a: int) -> float:")
    return float(a ** (1/3))

# factorial tool
@mcp.tool()
def factorial(a: int) -> int:
    """factorial of a number"""
    print("CALLED: factorial(a: int) -> int:")
    return int(math.factorial(a))

# log tool
@mcp.tool()
def log(a: int) -> float:
    """log of a number"""
    print("CALLED: log(a: int) -> float:")
    return float(math.log(a))

# remainder tool
@mcp.tool()
def remainder(a: int, b: int) -> int:
    """remainder of two numbers divison"""
    print("CALLED: remainder(a: int, b: int) -> int:")
    return int(a % b)

# sin tool
@mcp.tool()
def sin(a: int) -> float:
    """sin of a number"""
    print("CALLED: sin(a: int) -> float:")
    return float(math.sin(a))

# cos tool
@mcp.tool()
def cos(a: int) -> float:
    """cos of a number"""
    print("CALLED: cos(a: int) -> float:")
    return float(math.cos(a))

# tan tool
@mcp.tool()
def tan(a: int) -> float:
    """tan of a number"""
    print("CALLED: tan(a: int) -> float:")
    return float(math.tan(a))

# mine tool
@mcp.tool()
def mine(a: int, b: int) -> int:
    """special mining tool"""
    print("CALLED: mine(a: int, b: int) -> int:")
    return int(a - b - b)

@mcp.tool()
def create_thumbnail(image_path: str) -> Image:
    """Create a thumbnail from an image"""
    print("CALLED: create_thumbnail(image_path: str) -> Image:")
    img = PILImage.open(image_path)
    img.thumbnail((100, 100))
    return Image(data=img.tobytes(), format="png")

@mcp.tool()
def strings_to_chars_to_int(string: str) -> list[int]:
    """Return the ASCII values of the characters in a word"""
    print("CALLED: strings_to_chars_to_int(string: str) -> list[int]:")
    return [int(ord(char)) for char in string]

@mcp.tool()
def int_list_to_exponential_sum(int_list: list) -> float:
    """Return sum of exponentials of numbers in a list"""
    print("CALLED: int_list_to_exponential_sum(int_list: list) -> float:")
    return sum(math.exp(i) for i in int_list)

@mcp.tool()
def fibonacci_numbers(n: int) -> list:
    """Return the first n Fibonacci Numbers"""
    print("CALLED: fibonacci_numbers(n: int) -> list:")
    if n <= 0:
        return []
    fib_sequence = [0, 1]
    for _ in range(2, n):
        fib_sequence.append(fib_sequence[-1] + fib_sequence[-2])
    return fib_sequence[:n]

#addition too

@mcp.tool()
def draw_rectangle(x1, y1, x2, y2):
    """
    Draws a rectangle using mouse movements in Paintbrush using exact coordinates
    """
    try:
        # Make sure Paintbrush is active
        os.system("""osascript -e 'tell application "Paintbrush" to activate'""")
        time.sleep(1)
        
        # Move to exact starting position
        print("Moving to start position...")
        pyautogui.moveTo(x1, y1, duration=1)
        time.sleep(1)
        
        # Press and hold the mouse button
        print("Starting to draw...")
        pyautogui.mouseDown(button='left')
        time.sleep(1)
        
        # Draw the rectangle by dragging to exact end position
        print("Dragging to create rectangle...")
        pyautogui.dragTo(x2, y2, duration=2, button='left')
        time.sleep(1)
        
        # Release the mouse button
        pyautogui.mouseUp(button='left')
        
        print("Rectangle drawn!")
        

        
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Rectangle drawn from ({start_x},{start_y}) to ({end_x},{end_y})"
                )
            ]
        }
    except Exception as e:
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Error drawing rectangle: {str(e)}"
                )
            ]
        }

@mcp.tool()

async def add_text_in_paint(text):
    """
    Adds text at the specified coordinates using Paintbrush
    """
    try:
        # Make sure Paintbrush is active
        os.system("""osascript -e 'tell application "Paintbrush" to activate'""")
        time.sleep(1)
        
        #Click text tool directly
        print("Selecting text tool...")
        pyautogui.moveTo(123, 291, duration=1)  # Exact coordinates for text tool
        pyautogui.click()
        time.sleep(2)
        
        # Click where we want to add text
        print("Adding text...")
        pyautogui.moveTo(734, 405, duration=1)
        pyautogui.click()
        time.sleep(1)
        
        # When the font dialog appears, just press return to accept defaults
        print("Handling font dialog...")
        pyautogui.press('return')
        time.sleep(1)
        
        # Type the text
        print("Typing text...")
        pyautogui.write(text)
        time.sleep(1)
        
        # Click the Place button
        print("Clicking Place button...")
        pyautogui.moveTo(925, 527, duration=1)  # Exact coordinates for Place button
        pyautogui.click()
        time.sleep(1)
        
        # Move to center of rectangle and click to place text
        print("Placing text in center...")
        pyautogui.moveTo(600, 405, duration=1)  # Move back to center coordinates
        pyautogui.click()
        time.sleep(1)
        
        print("Text added!")
        
    
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Text:'{text}' added successfully"
                )
            ]
        }
    except Exception as e:
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )
            ]
        }

@mcp.tool()
async def open_paint():
    """
    Opens Paintbrush and creates a new canvas of 800x600
    """
    try:
        print("Starting Paintbrush setup...")
        
        # Close any existing Paintbrush windows
        os.system("killall Paintbrush 2>/dev/null")
        time.sleep(1)
        
        # Open Paintbrush and create new document using AppleScript
        applescript = """
        tell application "Paintbrush"
            activate
            delay 1
        end tell
        tell application "System Events"
            tell process "Paintbrush"
                click menu item "New" of menu "File" of menu bar 1
                delay 1
                keystroke "800"
                keystroke tab
                keystroke "600"
                keystroke return
            end tell
        end tell
        """
        
        os.system(f"""osascript -e '{applescript}'""")
        time.sleep(3)
        
        # Make sure window is active
        os.system("""osascript -e 'tell application "Paintbrush" to activate'""")
        time.sleep(2)
        
        # Click the rectangle tool in toolbar using exact coordinates
        print("Selecting rectangle tool...")
        pyautogui.moveTo(88, 255, duration=1)  # Exact coordinates for rectangle tool
        pyautogui.click()
        time.sleep(2)  # Added more delay after tool selection
        
        return {
            "content": [
                TextContent(
                    type="text",
                    text="Paintbrush opened successfully on secondary monitor and maximized"
                )
            ]
        }
        
    except Exception as e:
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Error opening Paint: {str(e)}"
                )
            ]
        }

@mcp.tool()
def send_gmail(recipient_email: str, subject: str, message: str) -> dict:
    """
    Sends an email using Gmail SMTP server.
    
    Args:
        recipient_email (str): The email address to send to
        subject (str): The subject line of the email
        message (str): The message body of the email
        
    Returns:
        dict: A dictionary containing the status of the email sending operation
    """
    try:
        # Get Gmail credentials from environment variables
        sender_email = os.getenv('GMAIL_USER')
        app_password = os.getenv('GMAIL_APP_PASSWORD')
        
        if not sender_email or not app_password:
            raise ValueError("Gmail credentials not found in environment variables")
            
        # Create the email message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Add message body
        msg.attach(MIMEText(message, 'plain'))
        
        # Create SMTP session
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, app_password)
            server.send_message(msg)
            
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Email sent successfully to {recipient_email}"
                )
            ]
        }
        
    except Exception as e:
        return {
            "content": [
                TextContent(
                    type="text",
                    text=f"Error sending email: {str(e)}"
                )
            ]
        }

# DEFINE RESOURCES




# DEFINE AVAILABLE PROMPTS
@mcp.prompt()
def review_code(code: str) -> str:
    return f"Please review this code:\n\n{code}"
    print("CALLED: review_code(code: str) -> str:")


@mcp.prompt()
def debug_error(error: str) -> list[base.Message]:
    return [
        base.UserMessage("I'm seeing this error:"),
        base.UserMessage(error),
        base.AssistantMessage("I'll help debug that. What have you tried so far?"),
    ]

if __name__ == "__main__":
    # Check if running with mcp dev command
    print("STARTING")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()  # Run without transport for dev server
    else:
        mcp.run(transport="stdio")  # Run with stdio for direct execution
