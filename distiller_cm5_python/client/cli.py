"""
Command Line Interface (CLI) for interacting with the MCP Client.
"""

import asyncio
import argparse
import sys
import os
import time
import logging  # Import standard logging
from colorama import Fore, Style, init as colorama_init

from distiller_cm5_python.client.mid_layer.mcp_client import MCPClient
from distiller_cm5_python.client.ui.events.event_types import (
    EventType,
    StatusType,
    MessageSchema,
)
from distiller_cm5_python.client.ui.events.event_dispatcher import EventDispatcher
from distiller_cm5_python.utils.config import (
    STREAMING_ENABLED,
    SERVER_URL,
    PROVIDER_TYPE,
    MODEL_NAME,
    TIMEOUT,
    LOGGING_LEVEL,
    MCP_SERVER_SCRIPT_PATH,
    API_KEY,
)
from distiller_cm5_python.utils.distiller_exception import (
    UserVisibleError,
    LogOnlyError,
)
from functools import partial  # Import partial for asyncio.to_thread

# Try to import whisper, but don't fail if it's not available initially.
# We'll handle the actual import attempt later based on args.
try:
    from distiller_cm5_sdk import whisper
except ImportError:
    whisper = None  # Placeholder if the SDK isn't installed

# Get logger for this module after setup
logger = logging.getLogger(__name__)


class CLIEventHandler:
    """Handles UI events for CLI display"""

    def __init__(self):
        self.current_message_id = None
        self.message_chunks = []

    def handle_event(self, evt: MessageSchema):
        """Handles dispatched MessageSchema events for CLI display"""
        # Check event type using evt.type enum
        if evt.type == EventType.INFO or evt.type == EventType.STATUS:
            # Treat STATUS like INFO for basic CLI display
            print(f"{Fore.CYAN}{evt.content}{Style.RESET_ALL}")
        elif evt.type == EventType.WARNING:
            print(f"{Fore.YELLOW}{evt.content}{Style.RESET_ALL}")
        elif evt.type == EventType.ERROR:
            print(f"{Fore.RED}{evt.content}{Style.RESET_ALL}")
        elif evt.type == EventType.MESSAGE:
            # Use evt.status enum for message state
            if evt.status == StatusType.IN_PROGRESS:
                # Handle streaming message chunks
                if evt.id != self.current_message_id:
                    # Start of a new message stream
                    self.current_message_id = evt.id
                    self.message_chunks = []
                    print(f"\n{Style.BRIGHT}Assistant: {Style.RESET_ALL}", end="")
                # Access content directly from evt.content
                if isinstance(evt.content, str):
                    self.message_chunks.append(evt.content)
                    print(evt.content, end="", flush=True)
            elif evt.status == StatusType.SUCCESS:
                print("[SUCCESS]", flush=True)

        elif evt.type == EventType.ACTION:
            # Display simplified action info
            if evt.status == StatusType.IN_PROGRESS:
                # Use tool_name from ActionEvent if available
                tool_name = (
                    evt.tool_name
                    if hasattr(evt, "tool_name") and evt.tool_name
                    else "Action"
                )
                print(f"{Fore.BLUE}Running: {tool_name}...{Style.RESET_ALL}")
            elif evt.status == StatusType.SUCCESS:
                # Indicate success, maybe show tool name again
                tool_name = (
                    evt.tool_name
                    if hasattr(evt, "tool_name") and evt.tool_name
                    else "Action"
                )
                print(
                    f"{Fore.GREEN}{tool_name} finished.{Style.RESET_ALL} , output : {evt.content}"
                )

        elif evt.type == EventType.OBSERVATION:
            pass

        # Other event types can be ignored or logged
        else:
            logger.debug(f"CLIEventHandler received unhandled event type: {evt.type}")


async def chat_loop(client: MCPClient, whisper_instance):
    """Start an interactive chat loop with the user, supporting text and audio input."""
    colorama_init()  # Initialize colorama

    if whisper_instance:
        print(
            f"{Style.BRIGHT}Chat session started. Type '/mic' to record audio, 'exit' or 'quit' to end.{Style.RESET_ALL}\n"
        )
    else:
        print(
            f"{Style.BRIGHT}Chat session started (Audio disabled). Type 'exit' or 'quit' to end.{Style.RESET_ALL}\n"
        )

    while True:
        user_input_text = ""
        transcribed_text = ""
        try:
            # Get user input asynchronously to avoid blocking
            prompt = f"{Style.BRIGHT}\nYou: {Style.RESET_ALL}"
            # Use asyncio.to_thread to run the blocking input() in a separate thread
            user_input_text = await asyncio.to_thread(partial(input, prompt))

            # Check for exit command
            if user_input_text.lower() in ["exit", "quit", "q"]:
                print("Exiting chat...")
                break

            # Check for audio input command
            if user_input_text.lower() == "/mic":
                if whisper_instance is None:
                    print(
                        f"{Fore.YELLOW}Audio input is disabled (SDK not found or --disable-audio used).{Style.RESET_ALL}"
                    )
                    continue

                print(
                    f"{Fore.YELLOW}Starting audio input... Press Enter to start recording.{Style.RESET_ALL}"
                )
                await asyncio.to_thread(input)  # Wait for Enter press

                if await asyncio.to_thread(whisper_instance.start_recording):
                    print(
                        f"{Fore.YELLOW}Recording... Press Enter to stop.{Style.RESET_ALL}"
                    )
                    await asyncio.to_thread(input)  # Wait for Enter press to stop
                    audio_data = await asyncio.to_thread(
                        whisper_instance.stop_recording
                    )

                    if audio_data:
                        print(f"{Fore.YELLOW}Transcribing...{Style.RESET_ALL}")
                        # Transcribe using asyncio.to_thread as transcribe_buffer might be CPU-bound
                        transcribed_segments = []
                        try:
                            # Use a wrapper function for the generator in to_thread
                            def get_transcription_sync(data):
                                return list(whisper_instance.transcribe_buffer(data))

                            transcribed_segments = await asyncio.to_thread(
                                get_transcription_sync, audio_data
                            )

                        except Exception as e:
                            logger.error(f"Error during transcription: {e}")
                            print(
                                f"{Fore.RED}\nError during transcription: {e}{Style.RESET_ALL}"
                            )
                            continue  # Skip processing this turn

                        if transcribed_segments:
                            transcribed_text = " ".join(transcribed_segments).strip()
                            print(
                                f"{Style.BRIGHT}You (Audio): {Style.RESET_ALL}{transcribed_text}"
                            )
                            user_input_for_llm = (
                                transcribed_text  # Use transcribed text
                            )
                            # Send transcribed text to client
                            await client.process_query(user_input_for_llm)
                        else:
                            print(
                                f"{Fore.YELLOW}Transcription returned no text.{Style.RESET_ALL}"
                            )
                            continue  # Skip processing if transcription is empty
                    else:
                        print(f"{Fore.YELLOW}No audio recorded.{Style.RESET_ALL}")
                        continue  # Go back to the start of the loop for new input
                else:
                    print(f"{Fore.RED}Failed to start recording.{Style.RESET_ALL}")
                    continue  # Go back to the start of the loop
            else:
                user_input_for_llm = user_input_text  # Use text input

            # Process the query (either text or transcribed audio)
            if not user_input_for_llm:  # Should only happen if text input was empty
                continue

            try:
                await client.process_query(user_input_for_llm)
                print()  # Ensure newline after the full response/stream is printed
            except LogOnlyError as e:
                # Handle errors potentially raised from within process_query's streaming
                logger.error(f"Error during response generation: {e}")
                print(
                    f"{Fore.RED}\nAssistant encountered an error processing the request.{Style.RESET_ALL}"
                )
                # Decide how to handle history - MCPClient already logged the error
                # Maybe add a placeholder message?
                # client.message_processor.add_message("assistant", "[Error processing request]")
            except (
                UserVisibleError
            ) as e:  # Catch user-visible errors from process_query
                logger.error(f"Error during response generation: {e}")
                print(f"{Fore.RED}\nError: {e}{Style.RESET_ALL}")
                # History is handled by process_query yielding the error message

        except KeyboardInterrupt:
            print("\nChat interrupted by user. Exiting...")
            break
        except UserVisibleError as e:
            logger.error(f"Error: {e}")
            print(f"{Fore.RED}\nError: {e}{Style.RESET_ALL}")
            # Decide if we should break or continue
            # break
        except EOFError:
            print("\nInput stream closed. Exiting...")
            break
        except Exception as e:
            print(
                f"{Fore.RED}\nAn unexpected error occurred in the chat loop: {str(e)}{Style.RESET_ALL}"
            )
            logger.exception("Error details:")
            # break # Optional: exit on unexpected errors


def parse_arguments():
    parser = argparse.ArgumentParser(description="MCP Client CLI")
    parser.add_argument(
        "--server-script",
        default=MCP_SERVER_SCRIPT_PATH,
        help="Path to the MCP server script (e.g., ../server/server.py)",
    )
    parser.add_argument(
        "--stream",
        action=argparse.BooleanOptionalAction,
        default=STREAMING_ENABLED,
        help="Enable/disable streaming response",
    )
    parser.add_argument("--llm-url", default=SERVER_URL, help="URL for the LLM backend")
    parser.add_argument(
        "--provider",
        default=PROVIDER_TYPE,
        help="LLM provider type (e.g., llama-cpp, openai)",
    )
    parser.add_argument("--model", default=MODEL_NAME, help="LLM model name")
    parser.add_argument(
        "--api-key", default=API_KEY, help="API key for the LLM provider"
    )
    parser.add_argument(
        "--timeout", type=int, default=TIMEOUT, help="Request timeout in seconds"
    )
    parser.add_argument(
        "--log-level",
        default=LOGGING_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level",
    )
    parser.add_argument(
        "--disable-audio",
        action="store_true",
        help="Disable audio input features (requires distiller_cm5_sdk)",
    )
    parser.add_argument(
        "--gui", action="store_true", help="Launch the GUI interface instead of CLI"
    )
    return parser.parse_args()


async def main():
    args = parse_arguments()

    # Log the effective level
    logger.info(f"Log level set to: {args.log_level}")  # This logger is now configured

    # Make server script path absolute, default to MCP_SERVER_SCRIPT_PATH
    server_script_path = os.path.abspath(args.server_script)
    if not os.path.exists(server_script_path):
        logger.error(f"Server script not found at: {server_script_path}")
        print(
            f"{Fore.RED}Error: Server script not found at '{server_script_path}'. Please provide a valid path.{Style.RESET_ALL}"
        )
        sys.exit(1)

    logger.info(f"Using server script: {server_script_path}")

    # Initialize event dispatcher and handler
    event_handler = CLIEventHandler()
    event_dispatcher = EventDispatcher(debug=args.log_level == "DEBUG")
    event_dispatcher.message_dispatched.connect(event_handler.handle_event)

    client = MCPClient(
        streaming=args.stream,
        llm_server_url=args.llm_url,
        provider_type=args.provider,
        model=args.model,
        api_key=args.api_key,
        timeout=args.timeout,
        dispatcher=event_dispatcher,
    )

    # Instantiate Whisper only if SDK is available and not disabled
    whisper_module = None
    whisper_instance = None
    if not args.disable_audio:
        try:
            # Dynamically import whisper if not already done or if it was None
            global whisper
            if whisper is None:
                from distiller_cm5_sdk import whisper as sdk_whisper

                whisper = sdk_whisper  # Assign to the global placeholder

            if whisper:  # Check if import succeeded
                whisper_instance = whisper.Whisper()
                logger.info("Whisper SDK loaded and instance created.")
            else:
                logger.warning("Audio input disabled: distiller_cm5_sdk not found.")
                print(
                    f"{Fore.YELLOW}Warning: distiller_cm5_sdk not found. Audio input will be disabled.{Style.RESET_ALL}"
                )
        except ImportError:
            logger.warning("Audio input disabled: Failed to import distiller_cm5_sdk.")
            print(
                f"{Fore.YELLOW}Warning: Failed to import distiller_cm5_sdk. Audio input will be disabled.{Style.RESET_ALL}"
            )
            whisper = None  # Ensure whisper is None if import fails here
        except Exception as e:
            logger.error(f"Error initializing Whisper: {e}", exc_info=True)
            print(f"{Fore.RED}Error initializing audio input: {e}{Style.RESET_ALL}")
            whisper_instance = None  # Ensure instance is None on error
            whisper = None  # Ensure whisper module ref is None
    else:
        logger.info("Audio input explicitly disabled via --disable-audio flag.")
        whisper = None  # Ensure whisper is None if disabled by flag

    try:
        logger.info("Connecting to MCP server...")
        connected = await client.connect_to_server(server_script_path)
        if not connected:
            logger.error("Failed to connect to the MCP server.")
            print(
                f"{Fore.RED}Error: Failed to connect to the MCP server. Check server script and logs.{Style.RESET_ALL}"
            )
            sys.exit(1)

        logger.info("Connection successful. Starting chat loop.")
        await chat_loop(client, whisper_instance)  # Pass whisper instance

    except UserVisibleError as e:
        logger.error(f"Initialization Error: {e}")
        print(f"{Fore.RED}Initialization Error: {e}{Style.RESET_ALL}")
    except Exception as e:
        logger.exception("An unexpected error occurred during setup or chat.")
        print(f"{Fore.RED}An unexpected error occurred: {e}{Style.RESET_ALL}")
    finally:
        logger.info("Cleaning up client resources...")
        await client.cleanup()
        logger.info("Cleaning up Whisper resources...")
        if whisper_instance:
            whisper_instance.cleanup()  # Cleanup Whisper resources only if it exists
        else:
            logger.info("Whisper resources cleanup skipped (instance not created).")
        logger.info("Cleaning up event dispatcher...")
        event_dispatcher.close()
        logger.info("Client cleanup complete. Exiting.")


if __name__ == "__main__":
    # We need to initialize the logger early for any potential issues during argument parsing or setup
    # However, the level depends on args. So we do minimal setup first, then refine.
    # This is a bit tricky. Let's configure it *after* parsing args for simplicity now.
    # Consider moving setup *before* arg parsing if pre-arg logs are needed,
    # potentially using a default level initially.
    asyncio.run(main())
