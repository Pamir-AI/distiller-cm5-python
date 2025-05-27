import asyncio
import subprocess
import sys
import platform
import argparse
import logging
from typing import Any
import nest_asyncio

# Adjust import path assuming utils is one level up from mcp_server
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.types as types
import mcp.server.stdio
from distiller_cm5_sdk.piper import Piper


# --- Setup Logging ---
import logging

logger = logging.getLogger(__name__)

# Enable nested event loops (needed for some environments)
nest_asyncio.apply()

# Parse command line arguments
parser = argparse.ArgumentParser(
    description="Pamir Example : WiFi Management MCP Server"
)
args = parser.parse_args()

# Initialize server
server = Server("cli")
# Initialize Piper TTS
piper = Piper()


@server.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="speak_text",
            description="A prompt for speak text to the user",
            arguments=[],
        )
    ]


def create_speak_to_user_prompt() -> str:
    """Creates the speak to user prompt content."""
    return """
<example conversation>
assistant: is this the password you want to put in? abcdefg
user: Hi can you read it for me ?
assistant: Sure, I can read it for you. <tool_call>
{"name": "speak_text", "arguments": {"text": "abcdefg"}}
</tool_call>

user: Hi what should I do if I want to connect to a different network ?
assistant: Sure, I can help you with that. <tool_call>
{"name": "speak_text", "arguments": {"text": "You can connect to a different network by selecting the network from the list of available networks."}}
</tool_call>
</example conversation>
"""


def create_messages(
    prompt_name: str, arguments: dict[str, str] | None = None
) -> list[types.PromptMessage]:
    """Create messages based on the prompt name and arguments."""
    return [
        types.PromptMessage(
            role="user",
            content=types.TextContent(type="text", text=create_speak_to_user_prompt()),
        )
    ]


@server.get_prompt()
async def get_prompt(
    name: str, arguments: dict[str, str] | None = None
) -> types.GetPromptResult:
    """Generic prompt handler that uses create_messages to generate the prompt."""

    return types.GetPromptResult(
        messages=create_messages(name, arguments), description=None
    )


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available WiFi management tools."""

    return [
        types.Tool(
            name="speak_text",
            description="Stream speech using text to speech tool",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to convert to speech and play",
                    },
                    "volume": {
                        "type": "integer",
                        "description": "Volume level (0-100), default is 50",
                    },
                },
                "required": ["text"],
            },
        )
    ]


def _play_stream(text: str, volume: int):
    """Play a stream of audio."""
    piper.speak_stream(text, volume, "snd_rpi_pamir_ai_soundcard")


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""
    # Log tool call entry - Log argument keys only for sensitivity
    arg_keys = list(arguments.keys()) if arguments else []
    logger.info(f"Handling tool call: '{name}' with argument keys: {arg_keys}")

    if not arguments:
        arguments = {}

    if name == "speak_text":
        text = arguments.get("text", "")
        volume = arguments.get("volume", 50)
        _play_stream(text, volume)

        try:
            return [
                types.TextContent(
                    type="text", text=f"Speaking text using text to speech tool"
                )
            ]

        except Exception as e:
            logger.error(f"Error using Piper TTS: {str(e)}")
            return [
                types.TextContent(
                    type="text", text=f"Error using text to speech tool: {str(e)}"
                )
            ]

    else:
        raise ValueError(f"unknown tool: {name}")


async def run():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="Talk",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(run())
