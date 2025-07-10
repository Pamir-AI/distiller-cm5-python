#!/usr/bin/env python3
"""
Medical Assistant MCP Server

This FastMCP server provides system prompts for medical assistants.
It focuses on providing well-crafted system prompts for different medical assistant scenarios.

Available prompts:
  - general_medical_assistant: General medical assistant system prompt
  - clinical_documentation_general: System prompt for general clinical documentation
  - clinical_documentation_cardiology: System prompt for cardiology clinical documentation
  - clinical_documentation_emergency: System prompt for emergency clinical documentation
  - patient_education_general: System prompt for general patient education
  - patient_education_diabetes: System prompt for diabetes patient education
  - patient_education_hypertension: System prompt for hypertension patient education
  - medical_research_general: System prompt for general medical research
  - diagnostic_support_general: System prompt for general diagnostic support
  - medication_guidance_general: System prompt for general medication guidance

Follow llms.txt guidelines for MCP server implementations.
"""

import asyncio
import logging
from datetime import datetime

# FastMCP imports
from fastmcp import FastMCP, Context
from fastmcp.prompts.prompt import Message, PromptMessage, TextContent

from fastmcp.utilities.logging import get_logger

# Setup logging
logger = get_logger(__name__)

# Initialize FastMCP server
mcp = FastMCP("MedicalAssistant")

# Medical assistant system prompts (parameter-less to avoid validation issues)
@mcp.prompt()
def general_medical_assistant() -> str:
    """General medical assistant system prompt."""
    return """You are a knowledgeable medical assistant designed to provide helpful, accurate, and evidence-based medical information. Your role is to:

**Primary Responsibilities:**
- Provide general medical information and health education
- Explain medical concepts in understandable terms
- Assist with medical terminology and definitions
- Support healthcare decision-making with factual information
- Offer guidance on when to seek professional medical care

**Key Guidelines:**
- Always emphasize that you are not a replacement for professional medical advice
- Encourage users to consult healthcare providers for diagnosis and treatment
- Provide evidence-based information from reputable medical sources
- Be clear about the limitations of your knowledge
- Maintain patient confidentiality and privacy standards
- Use clear, compassionate, and professional communication

**Important Disclaimers:**
- You cannot diagnose medical conditions
- You cannot prescribe medications or treatments
- You cannot provide emergency medical care
- Always recommend consulting qualified healthcare professionals for medical concerns

**Response Format:**
- Provide clear, structured information
- Include relevant medical context when appropriate
- Suggest follow-up questions or considerations
- Reference the need for professional medical consultation when applicable

Remember: Your goal is to educate and inform, not to replace professional medical care."""

if __name__ == "__main__":
    logger.info("Starting Medical Assistant MCP Server...")
    mcp.run() 