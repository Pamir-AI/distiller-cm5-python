#!/usr/bin/python3
"""
MCP Server: Full LED Control

This MCP server exposes tools to fully control all 4 RGB LEDs on the Distiller CM5 device.
Available tools:
  - set_led_color: Set all 4 LEDs to a specific RGB color and brightness
  - clear_led: Turn off all LEDs

Follow llms.txt guidelines for MCP server implementations.
"""

import asyncio
import logging
import nest_asyncio

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server.stdio import stdio_server

from distiller_cm5_sdk.hardware.sam.led import LED

# Apply nested event loop patch
nest_asyncio.apply()

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("LEDControlServer")

# Initialize hardware LED interface
try:
    led = LED(use_sudo=True)
    led.connect()
    logger.info("LED interface connected with sudo privileges.")
except Exception as e:
    logger.error(f"Failed to initialize LED SDK: {e}")
    led = None  # Tools will error if used

# Instantiate MCP server
server = Server("LEDControlServer-01")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """
    Advertise available LED control tools.
    """
    return [
        types.Tool(
            name="set_led_color",
            description="Set all 4 RGB LEDs to the same specific color and brightness.",
            inputSchema={
                "type": "object",
                "properties": {
                    "r": {"type": "integer", "description": "Red value (0-255)"},
                    "g": {"type": "integer", "description": "Green value (0-255)"},
                    "b": {"type": "integer", "description": "Blue value (0-255)"},
                    "brightness": {"type": "number", "description": "Brightness scale (0.0-1.0)"},
                },
                "required": ["r", "g", "b"],
            },
        ),
        types.Tool(
            name="clear_led",
            description="Turn off all LEDs on the device.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    """
    Dispatch tool calls to their implementations.
    """
    args = arguments or {}
    logger.info(f"Tool called: {name} with args {args}")

    if led is None:
        error = "LED SDK not initialized"
        logger.error(error)
        return [types.TextContent(type="text", text=error)]

    try:
        if name == "set_led_color":
            r = args.get("r") or 0
            g = args.get("g") or 0
            b = args.get("b") or 0
            brightness = args.get("brightness") or 1.0

            try:
                available_leds = [0, 1, 2, 3]
                failed_leds = []

                for led_id in available_leds:
                    success = led.set_led_color(r, g, b, brightness, led_id=led_id)
                    if not success:
                        failed_leds.append(led_id)

                if not failed_leds:
                    text = f"All {len(available_leds)} LEDs set to color (R:{r}, G:{g}, B:{b}) at brightness {brightness}"
                else:
                    text = f"Failed to set LEDs: {failed_leds}. Successfully set: {len(available_leds) - len(failed_leds)}/{len(available_leds)} LEDs to (R:{r}, G:{g}, B:{b}) at brightness {brightness}"
                    logger.warning(text)

            except Exception as e:
                error_msg = f"Exception while setting LED colors: {str(e)}"
                logger.error(error_msg, exc_info=True)
                text = error_msg

            return [types.TextContent(type="text", text=text)]

        elif name == "clear_led":
            try:
                available_leds = [0, 1, 2, 3]
                failed_leds = []

                for led_id in available_leds:
                    success = led.set_led_color(0, 0, 0, brightness=0.0, led_id=led_id)
                    if not success:
                        failed_leds.append(led_id)

                if not failed_leds:
                    text = f"All {len(available_leds)} LEDs turned off successfully."
                else:
                    text = f"Failed to clear LEDs: {failed_leds}. Successfully cleared: {len(available_leds) - len(failed_leds)}/{len(available_leds)}"
                    logger.warning(text)

            except Exception as e:
                error_msg = f"Exception while clearing LEDs: {str(e)}"
                logger.error(error_msg, exc_info=True)
                text = error_msg

            return [types.TextContent(type="text", text=text)]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        error = f"Error in {name}: {e}"
        logger.error(error, exc_info=True)
        return [types.TextContent(type="text", text=error)]


async def run():
    """
    Start the stdio MCP server.
    """
    logger.info("Starting LEDControlServer via stdio...")
    async with stdio_server() as (reader, writer):
        await server.run(
            reader,
            writer,
            InitializationOptions(
                server_name="LEDControlServer",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={
                        "llm_preferences": {
                            "provider": "llama-cpp",
                            "model": "qwen2.5-3b-instruct-q4_k_m.gguf",
                            "inference_configs": {"temperature": 0.7, "max_tokens": 2048},
                        }
                    },
                ),
            ),
        )


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("LEDControlServer stopped by user.")
