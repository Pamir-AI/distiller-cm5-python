"""
Manages the lifecycle and connection status of a local llama-cpp server process.
"""

import os
import sys
import subprocess
import time
import psutil
import requests
from typing import Optional
from urllib.parse import urlparse

from utils.logger import logger
from utils.config import N_CTX, LLAMA_CPP_START_WAIT_TIME, LOGGING_LEVEL
from utils.distiller_exception import UserVisibleError

class LlamaCppServerManager:
    """Handles starting, stopping, and checking a local llama-cpp server process."""

    def __init__(self, server_url: str, model_name: str, health_endpoint: str = "/health"):
        """Initialize the manager.

        Args:
            server_url: The URL where the server should run (e.g., "http://127.0.0.1:8000").
            model_name: The name of the model the server should load.
            health_endpoint: The endpoint path used for health checks.
        """
        self.server_url = server_url.rstrip('/')
        self.model_name = model_name
        self.health_endpoint = health_endpoint
        self.process: Optional[subprocess.Popen] = None
        self.pid: Optional[int] = None
        self.script_path: Optional[str] = self._find_server_script()

        logger.debug(f"LlamaCppServerManager initialized for URL: {self.server_url}, Model: {self.model_name}")

    def _find_server_script(self) -> Optional[str]:
        """Attempt to locate the llama-cpp server script relative to this file.
           Assumes this structure: .../client/llm_infra/llama_manager.py
                                    .../llm_server/server.py
        """
        current_dir = os.path.dirname(os.path.abspath(__file__)) # llm_infra directory
        llm_infra_dir = current_dir
        client_dir = os.path.dirname(llm_infra_dir)
        project_root_dir = os.path.dirname(client_dir)
        server_script = os.path.join(project_root_dir, "llm_server", "server.py")
        if os.path.exists(server_script):
             logger.debug(f"Found llama-cpp server script at: {server_script}")
             return os.path.abspath(server_script)
        else:
             logger.error(f"Could not find llama-cpp server script expected at {server_script}")
             return None

    def start(self) -> bool:
        """Start the llama-cpp server process if not already running.

        Returns:
            True if the server is started and connected successfully, False otherwise.
        """
        if self.is_running():
            logger.info(f"Llama.cpp server already running (PID: {self.pid}) and responsive.")
            return True

        if not self.script_path:
             raise UserVisibleError("Cannot start llama-cpp server: server script not found.")

        # Parse host and port
        try:
            parsed_url = urlparse(self.server_url)
            host = parsed_url.hostname
            port = parsed_url.port
            if not host or not port:
                raise ValueError("Host or port not found in server_url")
        except Exception as e:
            logger.error(f"Invalid server URL format for starting server: {self.server_url}. Error: {e}")
            raise UserVisibleError(f"Invalid server URL: {self.server_url}. Expected format like http://127.0.0.1:8000")

        command = [
            sys.executable,
            self.script_path,
            "--host", host,
            "--port", str(port),
            "--model-name", self.model_name,
            "--n-ctx", str(N_CTX),
            "--logging-level", str(LOGGING_LEVEL)
        ]
        logger.info(f"Starting llama-cpp server with command: {' '.join(command)}")

        try:
            # Start in background, allow output to parent terminal for debugging
            self.process = subprocess.Popen(command)
            self.pid = self.process.pid
            logger.info(f"Started llama-cpp server process with PID: {self.pid}")
        except Exception as e:
            logger.error(f"Failed to execute Popen command: {e}")
            self.process = None
            self.pid = None
            raise UserVisibleError(f"Failed to start the llama-cpp server process: {e}")

        # Wait for server to become responsive
        logger.info(f"Waiting up to {LLAMA_CPP_START_WAIT_TIME}s for server to become responsive...")
        start_wait = time.time()
        connection_ok = False
        while time.time() - start_wait < LLAMA_CPP_START_WAIT_TIME:
            if self.process and self.process.poll() is not None:
                logger.error(f"Server process {self.pid} terminated prematurely with code {self.process.returncode}.")
                self._clear_process_info()
                raise UserVisibleError("Local llama-cpp server process failed to stay running.")

            if self.check_connection(): # Use the manager's own check method
                connection_ok = True
                break
            time.sleep(0.5)

        if not connection_ok:
            logger.error(f"Failed to connect to the llama-cpp service at {self.server_url} within {LLAMA_CPP_START_WAIT_TIME}s.")
            self.stop() # Attempt to terminate the potentially hung process
            raise UserVisibleError("Could not start or connect to local llama-cpp LLM server.")

        logger.info(f"Llama-cpp server started successfully (PID: {self.pid}) and connection verified.")
        return True

    def stop(self) -> bool:
        """Stop the managed llama-cpp server process.

        Returns:
            True if the process was stopped or was not running, False on error.
        """
        process_to_stop = self.process
        pid_to_stop = self.pid

        if process_to_stop is None and pid_to_stop is not None:
            # If we only have PID, try to find process using psutil
            try:
                process_to_stop = psutil.Process(pid_to_stop)
            except psutil.NoSuchProcess:
                logger.info(f"Process with PID {pid_to_stop} not found (already stopped?).")
                self._clear_process_info()
                return True # Considered success if not found
            except Exception as e:
                 logger.warning(f"Error finding process with PID {pid_to_stop}: {e}")
                 process_to_stop = None

        if process_to_stop is not None:
            pid_to_stop = process_to_stop.pid # Ensure PID matches process object
            logger.info(f"Attempting to terminate llama-cpp server process PID: {pid_to_stop}")
            try:
                process_to_stop.terminate() # Try graceful termination
                try:
                    process_to_stop.wait(timeout=3) # Wait up to 3 seconds
                    logger.info(f"Llama.cpp server process {pid_to_stop} terminated gracefully.")
                except (psutil.TimeoutExpired, getattr(subprocess, 'TimeoutExpired', Exception)): # Handle both psutil & subprocess timeout
                    logger.warning(f"Process {pid_to_stop} did not terminate gracefully, attempting force kill.")
                    process_to_stop.kill()
                    try:
                        process_to_stop.wait(timeout=1) # Short wait after kill
                        logger.info(f"Llama.cpp server process {pid_to_stop} killed.")
                    except (psutil.TimeoutExpired, getattr(subprocess, 'TimeoutExpired', Exception)):
                         logger.error(f"Process {pid_to_stop} did not terminate after kill.")
                self._clear_process_info()
                return True
            except psutil.NoSuchProcess:
                 logger.info(f"Process {pid_to_stop} not found during termination (already terminated?).")
                 self._clear_process_info()
                 return True
            except Exception as e:
                 logger.error(f"Error during termination of process {pid_to_stop}: {e}")
                 self._clear_process_info() # Clear local state even on error
                 return False # Indicate termination failed
        else:
            logger.info("No active llama-cpp server process known to this manager.")
            self._clear_process_info() # Ensure state is clear
            return True # No process was running, consider it stopped

    def check_connection(self) -> bool:
        """Check if the server is responsive at its health endpoint."""
        try:
            # Ensure URL includes scheme for requests
            url_to_check = self.server_url
            if not url_to_check.startswith(("http://", "https://")):
                 url_to_check = "http://" + url_to_check

            endpoint = f"{url_to_check.rstrip('/')}/{self.health_endpoint.lstrip('/')}"
            # Use a short timeout for health checks
            response = requests.get(endpoint, timeout=2)
            if response.status_code == 200:
                 # Optional: Check if the process associated with self.pid still exists
                 if self.pid and not psutil.pid_exists(self.pid):
                      logger.warning(f"Server at {self.server_url} is responsive, but original process (PID: {self.pid}) is gone. Clearing internal process state.")
                      self._clear_process_info()
                      # Consider this False as *our* managed process isn't the one responding?
                      # Or True because *something* is there? Let's return True but clear state.
                      return True
                 return True
            else:
                 # logger.debug(f"Llama-cpp connection check failed at {endpoint}. Status: {response.status_code}")
                 return False
        except requests.exceptions.RequestException:
            # logger.debug(f"Llama-cpp connection check failed at {endpoint}. Error: {e}")
            return False
        except Exception as e:
             logger.error(f"Unexpected error during llama-cpp connection check: {e}")
             return False

    def is_running(self) -> bool:
        """Checks if the managed process is believed to be running and responsive."""
        # Check if we have a process object and it hasn't terminated
        if self.process and self.process.poll() is None:
            # If process seems alive, double-check with a connection test
            if self.check_connection():
                return True
            else:
                 logger.warning(f"Managed process (PID: {self.pid}) exists but server at {self.server_url} is unresponsive.")
                 return False
        # If no process object or it has terminated, check connection anyway
        # An external server might be running at the URL
        elif self.check_connection():
             logger.info(f"Server is responsive at {self.server_url}, but not managed by this instance (PID: {self.pid} is None or terminated). Clearing internal process state.")
             self._clear_process_info()
             return True # Server is running, just not *our* process

        # No process and no connection
        return False

    def get_pid(self) -> Optional[int]:
        """Returns the PID of the managed process, if known."""
        return self.pid

    def _clear_process_info(self):
        """Reset internal process and PID tracking."""
        self.process = None
        self.pid = None

    def _clear_process_info(self):
        """Reset internal process and PID tracking."""
        self.process = None
        self.pid = None 