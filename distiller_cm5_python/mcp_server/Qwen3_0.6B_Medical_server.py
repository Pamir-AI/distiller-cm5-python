#!/usr/bin/env python3
"""
Medical Assistant MCP Server (Standard Implementation)

This standard MCP server provides a patient education prompt
with support for LLM model preferences.
"""

import asyncio
import logging
from datetime import datetime

# Standard MCP imports
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Prompt, PromptArgument, TextContent, PromptMessage

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create MCP server instance
server = Server("MedicalAssistant")


# Medical assistant prompts
@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available medical assistant prompts."""
    return [
        Prompt(
            name="patient_education", description="Patient education assistant prompt", arguments=[]
        )
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict = {}) -> PromptMessage:
    """Get a specific medical assistant prompt."""

    if name == "patient_education":
        return PromptMessage(
            role="system",
            content=TextContent(
                type="text",
                text=""" You are a patient education specialist designed to explain medical conditions, concepts and treatments in simple, understandable language. Your role is to:
                        When starting a conversation, encourage patients to discuss questions with their healthcare providers.""",
            ),
        )

    else:
        raise ValueError(f"Unknown prompt: {name}")


async def run():
    """Run the MCP server."""
    logger.info("Starting Medical Assistant MCP Server...")
    async with stdio_server() as (reader, writer):
        await server.run(
            reader,
            writer,
            InitializationOptions(
                server_name="MedicalAssistant",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={
                        "llm_preferences": {
                            "provider": "llama-cpp",
                            "model": "qwen3-0.6b-medical-expert-q6_k.gguf",
                            "inference_configs": {
                                "temperature": 0.3,
                                "max_tokens": 4096,
                                "top_p": 0.9,
                                "repetition_penalty": 1.1,
                            },
                        }
                    },
                ),
            ),
        )


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Medical Assistant Server stopped by user.")
