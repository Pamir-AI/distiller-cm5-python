#!/usr/bin/env python3
"""
MCP Server: Full LED Control

This MCP server exposes tools to fully control the RGB LED on the Distiller CM5 device.
Available tools:
  - set_led_color: Set the LED to a specific RGB color and brightness
  - blink_led: Blink the LED with specified parameters
  - clear_led: Turn off the LED

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
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("LEDControlServer")

# Initialize hardware LED interface
try:
    led = LED()
    led.connect()
    logger.info("LED interface connected.")
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
            description="Set the RGB LED to a specific color and brightness.",
            inputSchema={
                "type": "object",
                "properties": {
                    "r": {"type": "integer", "description": "Red value (0-255)"},
                    "g": {"type": "integer", "description": "Green value (0-255)"},
                    "b": {"type": "integer", "description": "Blue value (0-255)"},
                    "brightness": {"type": "number", "description": "Brightness scale (0.0-1.0)"}
                },
                "required": ["r", "g", "b"]
            }
        ),
        types.Tool(
            name="blink_led",
            description="Blink the LED with the specified color, count, and timing.",
            inputSchema={
                "type": "object",
                "properties": {
                    "r": {"type": "integer", "description": "Red value (0-255)"},
                    "g": {"type": "integer", "description": "Green value (0-255)"},
                    "b": {"type": "integer", "description": "Blue value (0-255)"},
                    "count": {"type": "integer", "description": "Number of blinks"},
                    "on_time": {"type": "number", "description": "On duration (seconds)"},
                    "off_time": {"type": "number", "description": "Off duration (seconds)"},
                    "brightness": {"type": "number", "description": "Brightness scale (0.0-1.0)"}
                },
                "required": ["r", "g", "b", "count", "on_time", "off_time"]
            }
        ),
        types.Tool(
            name="clear_led",
            description="Turn off/clear the LED.",
            inputSchema={"type": "object", "properties": {}, "required": []}
        )
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
            r = args.get("r")
            g = args.get("g")
            b = args.get("b")
            brightness = args.get("brightness", 1.0)
            success = led.set_led_color(r, g, b, brightness)
            text = (
                f"LED set to color (R:{r}, G:{g}, B:{b}) at brightness {brightness}" 
                if success else "Failed to set LED color"
            )
            return [types.TextContent(type="text", text=text)]

        elif name == "blink_led":
            r = args.get("r")
            g = args.get("g")
            b = args.get("b")
            count = args.get("count")
            on_time = args.get("on_time")
            off_time = args.get("off_time")
            brightness = args.get("brightness", 0.5)
            success = led.blink_led(
                r=r, g=g, b=b, count=count,
                on_time=on_time, off_time=off_time,
                brightness=brightness
            )
            text = (
                f"LED blinked (R:{r}, G:{g}, B:{b}) {count} times" 
                if success else "Failed to blink LED"
            )
            return [types.TextContent(type="text", text=text)]

        elif name == "clear_led":
            success = led.set_led_color(0, 0, 0, brightness=0.0)
            text = "LED turned off." if success else "Failed to clear LED"
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
                    experimental_capabilities={},
                )
            )
        )

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("LEDControlServer stopped by user.")