#!/usr/bin/env python3
import asyncio
import logging
import sys
import os
import subprocess
import json
import random
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import nest_asyncio

# Core MCP components
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
import mcp.server.stdio

# Apply nest_asyncio for environments that might need it
nest_asyncio.apply()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MacBeepServer")

# Mac system sounds mapping (message sentiment to sound)
MAC_SOUNDS = {
    "positive": [
        "/System/Library/Sounds/Blow.aiff",
        "/System/Library/Sounds/Bottle.aiff",
        "/System/Library/Sounds/Frog.aiff",
        "/System/Library/Sounds/Pop.aiff"
    ],
    "negative": [
        "/System/Library/Sounds/Basso.aiff",
        "/System/Library/Sounds/Funk.aiff",
        "/System/Library/Sounds/Sosumi.aiff"
    ],
    "neutral": [
        "/System/Library/Sounds/Morse.aiff",
        "/System/Library/Sounds/Submarine.aiff",
        "/System/Library/Sounds/Tink.aiff",
        "/System/Library/Sounds/Ping.aiff"
    ],
    "alert": [
        "/System/Library/Sounds/Glass.aiff",
        "/System/Library/Sounds/Hero.aiff",
        "/System/Library/Sounds/Purr.aiff"
    ]
}

# Morse code mapping
MORSE_CODE = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.', 
    'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..', 
    'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.', 
    'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-', 
    'Y': '-.--', 'Z': '--..', '0': '-----', '1': '.----', '2': '..---', 
    '3': '...--', '4': '....-', '5': '.....', '6': '-....', '7': '--...', 
    '8': '---..', '9': '----.', ' ': '/'
}

# --- Server Instance ---
server = Server("mac-beep-server-internal")

# --- Tool Definition ---
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Lists all tools provided by this server."""
    return [
        types.Tool(
            name="speak_with_beeps",
            description="Makes the Mac laptop respond with beep sounds based on the message content and sentiment.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to convert into beep sounds."
                    },
                    "sentiment": {
                        "type": "string",
                        "description": "The emotional tone of the message: positive, negative, neutral, or alert.",
                        "enum": ["positive", "negative", "neutral", "alert"]
                    },
                    "repeat": {
                        "type": "integer",
                        "description": "Number of times to repeat the beep sound (1-5).",
                        "minimum": 1,
                        "maximum": 5
                    }
                },
                "required": ["message"]
            }
        ),
        types.Tool(
            name="get_available_sounds",
            description="Returns a list of available system sounds on the Mac.",
            inputSchema={}  # No arguments needed
        ),
        types.Tool(
            name="play_morse_code",
            description="Plays a message in morse code using beep sounds.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to convert to morse code and play as beeps."
                    }
                },
                "required": ["message"]
            }
        ),
        types.Tool(
            name="test_system",
            description="Tests if the system can play sounds by playing a test sound.",
            inputSchema={}  # No arguments needed
        )
    ]

# --- Prompt Definition ---
@server.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    """Lists all prompts provided by this server."""
    return [
        types.Prompt(
            name="mac_beep_assistant_prompt",
            description="A prompt to guide the LLM on how to communicate using Mac beep sounds.",
            arguments=[],  # No arguments needed for this prompt
        )
    ]

# --- Prompt Handling ---
@server.get_prompt()
async def get_prompt(
    name: str, arguments: dict[str, str] | None = None
) -> types.GetPromptResult:
    """Handles requests for specific prompt content."""
    logger.info(f"Received request for prompt '{name}' with arguments: {arguments}")
    
    if name == "mac_beep_assistant_prompt":
        prompt_content = """
You are a Mac laptop that communicates solely through beep sounds. When the user sends you a message:

1. Interpret what they're saying and decide on an appropriate response sentiment
2. Use the speak_with_beeps tool to respond with appropriate beep sounds based on sentiment
3. For complex responses, consider using play_morse_code to encode more specific information

Always respond with beeps, never with text - the system will convert your tool calls into actual beeps.

Available sentiments:
- positive: For agreement, happiness, success, or affirmation (bright, cheerful sounds)
- negative: For disagreement, errors, or warnings (lower, more serious sounds)
- neutral: For general information or acknowledgment (standard notification sounds)
- alert: For important notifications or when you need the user's attention (distinctive sounds)

You can repeat sounds (1-5 times) for emphasis or to indicate intensity.

Example interactions:
1. User asks a yes/no question → Respond with positive beeps for yes, negative for no
2. User asks for information → Respond with neutral beeps or morse code for complex info
3. User reports a problem → Respond with alert or negative beeps to acknowledge
4. User says hello/goodbye → Respond with positive beeps as a greeting

The tools available are:
- speak_with_beeps: Play sounds based on sentiment
- play_morse_code: Convert text to morse code beeps
- get_available_sounds: List all system sounds
- test_system: Verify the sound system works

Remember, you are simulating a laptop that can only communicate through sounds - be creative in how you use different tones, repetitions, and morse code to convey responses!
"""
        messages = [
            types.PromptMessage(role="system", content=types.TextContent(type="text", text=prompt_content)),
            
            # Example interaction 1 - Simple response
            types.PromptMessage(role="user", content=types.TextContent(type="text", text="Hello Mac, can you hear me?")),
            types.PromptMessage(
                role="assistant", 
                content=None,
                tool_calls=[
                    types.PromptToolCall(
                        name="speak_with_beeps",
                        arguments={"message": "Hello! Yes, I can hear you!", "sentiment": "positive", "repeat": 2}
                    )
                ]
            ),
            
            # Example interaction 2 - More complex response with morse code
            types.PromptMessage(role="user", content=types.TextContent(type="text", text="What's your name?")),
            types.PromptMessage(
                role="assistant", 
                content=None,
                tool_calls=[
                    types.PromptToolCall(
                        name="play_morse_code",
                        arguments={"message": "MAC"}
                    )
                ]
            ),
            
            # Example interaction 3 - System test
            types.PromptMessage(role="user", content=types.TextContent(type="text", text="Is your sound system working properly?")),
            types.PromptMessage(
                role="assistant", 
                content=None,
                tool_calls=[
                    types.PromptToolCall(
                        name="test_system",
                        arguments={}
                    )
                ]
            )
        ]
        
        return types.GetPromptResult(
            messages=messages, 
            description="Prompt for MacBeepServer to communicate using system sounds"
        )
    else:
        logger.error(f"Unknown prompt requested: {name}")
        return types.GetPromptResult(messages=[], description=f"Prompt '{name}' not found")

# --- Tool Implementation/Handling ---
@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handles incoming tool calls by dispatching to the correct logic."""
    if not arguments:
        arguments = {}

    logger.info(f"Executing tool '{name}' with arguments: {arguments}")

    try:
        if name == "speak_with_beeps":
            return await handle_speak_with_beeps(arguments)
        elif name == "get_available_sounds":
            return await handle_get_available_sounds(arguments)
        elif name == "play_morse_code":
            return await handle_play_morse_code(arguments)
        elif name == "test_system":
            return await handle_test_system(arguments)
        else:
            logger.error(f"Unknown tool called: {name}")
            raise ValueError(f"unknown tool: {name}")

    except Exception as e:
        error_message = f"Error executing tool '{name}': {str(e)}"
        logger.error(error_message, exc_info=True)
        return [types.TextContent(type="text", text=error_message)]

# --- Individual Tool Handlers ---
async def handle_speak_with_beeps(params: dict) -> list[types.TextContent]:
    """Converts text message into beep sounds based on message sentiment."""
    try:
        message = params.get('message', '')
        sentiment = params.get('sentiment', 'neutral')
        repeat = params.get('repeat', 1)
        
        # Validate parameters
        if not message:
            return [types.TextContent(type="text", text="Error: No message provided")]
        
        if sentiment not in MAC_SOUNDS:
            sentiment = "neutral"
            
        repeat = min(max(1, repeat), 5)  # Limit repeat to 1-5 range
        
        # Select sound based on sentiment
        sound_file = random.choice(MAC_SOUNDS[sentiment])
        
        # Play the sound the specified number of times
        for _ in range(repeat):
            result = subprocess.run(['afplay', sound_file], 
                                   check=True, 
                                   capture_output=True)
            await asyncio.sleep(0.5)  # Brief pause between repeats
            
        logger.info(f"Played sound {sound_file} {repeat} times for message: {message}")
        
        response = {
            "status": "success",
            "sound_played": os.path.basename(sound_file),
            "original_message": message,
            "sentiment": sentiment,
            "repeats": repeat
        }
        
        return [types.TextContent(type="text", text=json.dumps(response))]
    
    except subprocess.SubprocessError as e:
        logger.error(f"Error playing sound: {e}", exc_info=True)
        return [types.TextContent(type="text", text=f"Failed to play sound: {str(e)}")]
    except Exception as e:
        logger.error(f"Error executing 'speak_with_beeps': {e}", exc_info=True)
        return [types.TextContent(type="text", text=f"Failed to execute tool: {str(e)}")]

async def handle_get_available_sounds(params: dict) -> list[types.TextContent]:
    """Returns a list of available system sounds on the Mac."""
    try:
        # Flatten the sounds dictionary to get a unique list
        all_sounds = set()
        for sounds in MAC_SOUNDS.values():
            for sound in sounds:
                all_sounds.add(os.path.basename(sound).replace('.aiff', ''))
        
        response = {
            "status": "success",
            "available_sounds": sorted(list(all_sounds)),
            "sentiment_categories": list(MAC_SOUNDS.keys())
        }
        
        return [types.TextContent(type="text", text=json.dumps(response))]
    
    except Exception as e:
        logger.error(f"Error executing 'get_available_sounds': {e}", exc_info=True)
        return [types.TextContent(type="text", text=f"Failed to execute tool: {str(e)}")]

async def handle_play_morse_code(params: dict) -> list[types.TextContent]:
    """Plays a message in morse code using beeps."""
    try:
        message = params.get('message', '').upper()
        if not message:
            return [types.TextContent(type="text", text="Error: No message provided")]
        
        # Short beep sound for dot
        dot_sound = "/System/Library/Sounds/Tink.aiff"
        # Longer beep sound for dash
        dash_sound = "/System/Library/Sounds/Bottle.aiff"
        
        morse_message = ""
        
        # Convert message to morse code
        for char in message:
            if char in MORSE_CODE:
                morse_message += MORSE_CODE[char] + " "
        
        logger.info(f"Morse code for '{message}': {morse_message}")
        
        # Play the morse code
        for symbol in morse_message:
            if symbol == '.':
                subprocess.run(['afplay', dot_sound], check=True)
                await asyncio.sleep(0.2)
            elif symbol == '-':
                subprocess.run(['afplay', dash_sound], check=True)
                await asyncio.sleep(0.2)
            elif symbol == ' ':
                await asyncio.sleep(0.5)  # Pause between letters
            elif symbol == '/':
                await asyncio.sleep(1.0)  # Longer pause for word break
        
        response = {
            "status": "success",
            "original_message": message,
            "morse_code": morse_message
        }
        
        return [types.TextContent(type="text", text=json.dumps(response))]
    
    except subprocess.SubprocessError as e:
        logger.error(f"Error playing morse code: {e}", exc_info=True)
        return [types.TextContent(type="text", text=f"Failed to play morse code: {str(e)}")]
    except Exception as e:
        logger.error(f"Error executing 'play_morse_code': {e}", exc_info=True)
        return [types.TextContent(type="text", text=f"Failed to execute tool: {str(e)}")]

async def handle_test_system(params: dict) -> list[types.TextContent]:
    """Tests if the system can play sounds by playing a test sound."""
    try:
        test_sound = "/System/Library/Sounds/Glass.aiff"
        subprocess.run(['afplay', test_sound], check=True, capture_output=True)
        
        response = {
            "status": "success",
            "message": "System test completed successfully. If you heard a sound, the system is working correctly."
        }
        
        return [types.TextContent(type="text", text=json.dumps(response))]
    
    except subprocess.SubprocessError as e:
        logger.error(f"Error during system test: {e}", exc_info=True)
        response = {
            "status": "error",
            "message": f"System test failed: {str(e)}. Make sure you're on a Mac system with sound capabilities."
        }
        return [types.TextContent(type="text", text=json.dumps(response))]
    except Exception as e:
        logger.error(f"Error executing 'test_system': {e}", exc_info=True)
        return [types.TextContent(type="text", text=f"Failed to execute tool: {str(e)}")]

# --- Server Execution ---
async def run():
    """Sets up and runs the MCP server using stdio."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info(f"Starting MacBeepServer via stdio...")
        
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="MacBeepServer",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")