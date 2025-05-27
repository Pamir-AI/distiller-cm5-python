import asyncio
import subprocess
import sys
import platform
import argparse
import logging
import sys
from typing import Any
import nest_asyncio
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mcp.types as types
import mcp.server.stdio

# --- Setup Logging ---
import logging

logger = logging.getLogger(__name__)
# --- Logging is now configured ---

# Enable nested event loops (needed for some environments)
nest_asyncio.apply()

# Parse command line arguments
parser = argparse.ArgumentParser(
    description="Pamir Example : WiFi Management MCP Server (Linux)"
)
args = parser.parse_args()

# Initialize server
server = Server("cli")


@server.list_prompts()
async def list_prompts() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="wifi_assistant",
            description="A prompt for WiFi management assistant with sample conversations",
            arguments=[],
        )
    ]


def create_wifi_assistant_prompt() -> str:
    """Creates the WiFi assistant prompt content."""
    return """Please help onboarding the user to the device. your goal is to help the user connect to the device via wifi and then ssh into it."""


def create_messages(
    prompt_name: str, arguments: dict[str, str] | None = None
) -> list[types.PromptMessage]:
    """Create messages based on the prompt name and arguments."""

    return [
        types.PromptMessage(
            role="user",
            content=types.TextContent(type="text", text=create_wifi_assistant_prompt()),
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
    """List available WiFi management tools (Linux version)."""

    return [
        types.Tool(
            name="get_wifi_networks",
            description="Get the available WiFi networks",
            inputSchema={},
        ),
        types.Tool(
            name="get_wifi_status",
            description="Get the status of the WiFi connection",
            inputSchema={},
        ),
        types.Tool(
            name="connect_to_wifi",
            description="Connect to a WiFi network",
            inputSchema={
                "type": "object",
                "properties": {
                    "ssid": {
                        "type": "string",
                        "description": "The name of the WiFi network",
                    },
                    "password": {
                        "type": "string",
                        "description": "The password for the WiFi network",
                    },
                },
                "required": ["ssid", "password"],
            },
        ),
        types.Tool(
            name="show_ssh_instructions",
            description="Show the instructions for SSHing into the device",
            inputSchema={
                "type": "object",
                "properties": {
                    "ip_address": {
                        "type": "string",
                        "description": "The IP address of the device",
                    }
                },
                "required": ["ip_address"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests (Linux nmcli version)."""
    # Log tool call entry - Log argument keys only for sensitivity
    arg_keys = list(arguments.keys()) if arguments else []
    logger.info(f"Handling tool call: '{name}' with argument keys: {arg_keys}")

    if not arguments:
        arguments = {}

    if name == "get_wifi_networks":
        # Linux command using nmcli
        command = """sudo nmcli -t -f IN-USE,SSID device wifi list | awk -F: '
{
    if ($1 == "*") {
        print $2
    } else {
        print $2
    }
}' | sort | uniq"""

        logger.debug(
            f"Running command for get_wifi_networks: {command[:100]}..."
        )  # Log truncated command
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, check=False
        )

        if result.returncode != 0:
            logger.error(
                f"Command failed for get_wifi_networks (Linux). Return code: {result.returncode}, Stderr: {result.stderr}"
            )
            return [
                types.TextContent(
                    type="text",
                    text=f"Error getting WiFi networks: {result.stderr}",  # Return only stderr
                )
            ]
        else:
            logger.info("Successfully retrieved WiFi networks (Linux).")
            logger.debug(
                f"get_wifi_networks stdout (Linux): {result.stdout[:200]}..."
            )  # Log truncated output
            return [
                types.TextContent(
                    type="text", text=f"Available WiFi networks are: {result.stdout}"
                )
            ]

    elif name == "get_wifi_status":
        # Linux command using nmcli - assuming wlan0 interface
        command_list = ["nmcli", "device", "show", "wlan0"]
        logger.debug(
            f"Running command for get_wifi_status (Linux): {' '.join(command_list)}"
        )
        result = subprocess.run(
            command_list, capture_output=True, text=True, check=False
        )

        if result.returncode != 0:
            logger.error(
                f"Command failed for get_wifi_status (Linux). Return code: {result.returncode}, Stderr: {result.stderr}"
            )
            return [
                types.TextContent(
                    type="text",
                    text="Failed to get wifi status",  # Simple error message
                )
            ]
        else:
            # Process the output to get wifi status info
            status_lines = []
            for line in result.stdout.splitlines():
                # Adjusted keys for nmcli output
                if any(
                    key in line
                    for key in [
                        "GENERAL.DEVICE",
                        "GENERAL.TYPE",
                        "GENERAL.STATE",
                        "GENERAL.CONNECTION",
                        "IP4.ADDRESS",
                    ]
                ):
                    status_lines.append(line.strip())
            status_output = chr(10).join(status_lines)
            logger.info("Successfully retrieved WiFi status (Linux).")
            logger.debug(f"get_wifi_status relevant output (Linux): {status_output}")
            return [
                types.TextContent(type="text", text=f"Wifi status is: {status_output}")
            ]

    elif name == "connect_to_wifi":
        ssid = arguments.get("ssid", "")
        password = arguments.get("password", "")

        if not ssid or not password:
            logger.warning(
                "connect_to_wifi (Linux) called with missing ssid or password."
            )
            return [
                types.TextContent(
                    type="text", text="Error: SSID and password are required."
                )
            ]

        try:
            # Turn on WiFi first (Linux nmcli)
            power_command = ["sudo", "nmcli", "radio", "wifi", "on"]
            logger.debug(
                f"Running command to enable WiFi (Linux): {' '.join(power_command)}"
            )
            power_result = subprocess.run(
                power_command, capture_output=True, text=True, shell=False, check=False
            )
            # nmcli might return 0 even if already on, check stderr just in case
            if (
                power_result.returncode != 0
                and "already enabled" not in power_result.stderr.lower()
            ):
                logger.error(
                    f"Failed to enable WiFi (Linux). Return code: {power_result.returncode}, Stderr: {power_result.stderr}"
                )
                return [
                    types.TextContent(
                        type="text",
                        text=f"Failed to enable WiFi: {power_result.stderr}",
                    )
                ]
            logger.info(
                "WiFi power enabled successfully (Linux)."
                if power_result.returncode == 0
                else "WiFi already enabled (Linux)."
            )

            # Ensure password is a string
            password_str = str(password)

            # Connect to network (Linux nmcli)
            connect_command = [
                "sudo",
                "nmcli",
                "device",
                "wifi",
                "connect",
                str(ssid),
                "password",
                password_str,
            ]
            # Mask password in log
            masked_command_str = (
                f"sudo nmcli device wifi connect '{ssid}' password ****"
            )
            logger.debug(
                f"Running command to connect to WiFi (Linux): {masked_command_str}"
            )

            connect_result = subprocess.run(
                connect_command,
                capture_output=True,
                text=True,
                shell=False,
                check=False,
            )

            if connect_result.returncode == 0:
                logger.info(
                    f"Successfully initiated connection to WiFi network '{ssid}' (Linux)."
                )
                return [
                    types.TextContent(
                        type="text",
                        text=f"Successfully attempted to connect to the wifi network '{ssid}'",
                    )
                ]
            else:
                error_message = connect_result.stderr.strip()
                logger.error(
                    f"Failed to connect to WiFi network '{ssid}' (Linux). Return code: {connect_result.returncode}, Stderr: {error_message}"
                )
                # Provide a cleaner error message
                if (
                    "invalid password" in error_message.lower()
                    or "secrets were required" in error_message.lower()
                ):
                    user_error = "Failed to connect: Incorrect password?"
                elif (
                    "network not found" in error_message.lower()
                    or "No network with SSID" in error_message
                ):
                    user_error = f"Failed to connect: Network '{ssid}' not found?"
                else:
                    user_error = (
                        f"Failed to connect to the wifi network: {error_message}"
                    )

                return [types.TextContent(type="text", text=user_error)]

        except Exception as e:
            logger.error(
                f"Unexpected error connecting to WiFi '{ssid}' (Linux): {e}",
                exc_info=True,
            )
            return [
                types.TextContent(
                    type="text", text=f"Error connecting to WiFi: {str(e)}"
                )
            ]

    elif name == "show_ssh_instructions":
        ip_address = arguments.get("ip_address", "")
        logger.info(f"Returning SSH instructions for IP: {ip_address}")
        return [
            types.TextContent(
                type="text",
                text=f"""Open a terminal under the same network, use the following command: ssh distiller@{ip_address} , the password is just 'one', You can use Cursor to connect via SSH function as well""",
            )
        ]
    else:
        logger.error(f"Received call for unknown tool: '{name}' (Linux server)")
        raise ValueError(f"unknown tool: {name}")


async def run():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="Wi-Fi (Linux)",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(run())
