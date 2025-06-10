#!/usr/bin/env python3
"""
MCP Client - Main Entry Point

This script now delegates execution to cli.py, which handles
argument parsing and running the interactive client.
"""
import asyncio
import sys
import os
import logging
from typing import Optional

# Add project root to sys.path if necessary, although cli.py should handle it
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the main function from the actual CLI entry point
from distiller_cm5_python.client.cli import main as cli_main, parse_arguments
from distiller_cm5_python.utils.distiller_exception import UserVisibleError
# Import necessary components for LLM server management
from distiller_cm5_python.client.llm_infra.llama_manager import LlamaCppServerManager
from distiller_cm5_python.utils.config import PROVIDER_TYPE, SERVER_URL, MODEL_NAME

# Get logger instance for this module
from distiller_cm5_python.utils.logger import setup_logging

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

async def main():
    """Main entry point that handles optional LLM server startup and delegates to cli.py"""
    
    llama_manager: Optional[LlamaCppServerManager] = None
    started_server = False
    
    try:
        # Parse arguments 
        args = parse_arguments()
        
        # --- Llama.cpp Server Management ---
        if PROVIDER_TYPE == "llama-cpp":
            logger.info("Configuration specifies llama-cpp provider. Checking server status...")
            if not SERVER_URL or not MODEL_NAME:
                 logger.error("Missing SERVER_URL or MODEL_NAME in configuration for llama-cpp.")
                 print(f"Error: Missing server URL or model name for llama-cpp in configuration.")
                 sys.exit(1)
                 
            llama_manager = LlamaCppServerManager(SERVER_URL, MODEL_NAME)
            
            if not llama_manager.is_running():
                logger.info(f"Llama-cpp server not detected at {SERVER_URL}. Attempting to start...")
                try:
                    llama_manager.start() # Start the server
                    started_server = True
                    logger.info(f"Llama-cpp server started successfully by main.py (PID: {llama_manager.get_pid()})")
                except UserVisibleError as e:
                    logger.error(f"Failed to start llama-cpp server: {e}")
                    print(f"Error: Could not start the required llama-cpp server: {e}")
                    sys.exit(1) # Exit if server fails to start
            else:
                 logger.info(f"Existing llama-cpp server detected at {SERVER_URL}. Proceeding.")
        # --- End Llama.cpp Server Management ---
        

        if hasattr(args, 'gui') and args.gui:
            logger.info("Starting GUI mode...")
            # Import the GUI app and run it
            from distiller_cm5_python.client.ui.App import App
            app = App()
            return await app.run()
        else:   
            # Directly call the main function from cli.py
            # cli.py handles argument parsing, client setup, and the chat loop.
            logger.info("Starting CLI...")
            await cli_main()
        
    except KeyboardInterrupt:
        logger.info("Application terminated by user (KeyboardInterrupt).")
        print("\nExiting.") # Provide user feedback on interrupt
    except Exception as e:
        # Catch any unexpected errors during CLI execution
        logger.critical(f"Critical error in main execution: {e}", exc_info=True)
        print(f"An unexpected critical error occurred: {e}")
        sys.exit(1) # Exit with error code
    finally:
        # --- Llama.cpp Server Shutdown ---
        if llama_manager and started_server:
            logger.info(f"Shutting down managed llama-cpp server (PID: {llama_manager.get_pid()})...")
            stopped = llama_manager.stop()
            if stopped:
                logger.info("Llama-cpp server stopped successfully.")
            else:
                logger.warning("Llama-cpp server might not have stopped cleanly.")
        # --- End Llama.cpp Server Shutdown ---

if __name__ == "__main__":
    # Use asyncio.run() which handles the event loop setup and teardown
    asyncio.run(main()) 