import os
import re
import logging

logger = logging.getLogger(__name__)


class ServerDiscovery:
    """Handles MCP server discovery for the client bridge"""

    # Regex pattern to extract server name from server file
    SERVER_NAME_PATTERN = re.compile(r'SERVER_NAME\s*=\s*[\'"](.+?)[\'"]')

    def __init__(self, parent=None):
        """
        Initialize the server discovery manager

        Args:
            parent: Optional parent object (typically the bridge instance)
        """
        self._available_servers = []
        self._parent = parent

    @property
    def available_servers(self):
        """
        Get the list of available servers

        Returns:
            List of server info dictionaries with name and path keys
        """
        return self._available_servers

    def discover_mcp_servers(self, config=None):
        """
        Discover available MCP servers from the file system

        Args:
            config: Optional configuration object
        """
        logger.info("Discovering MCP servers")
        self._available_servers = []

        # Build list of directories to search
        server_dirs = self._get_server_directories(config)

        # Scan each directory for server files
        servers_found = 0
        for server_dir in server_dirs:
            if not os.path.exists(server_dir):
                logger.warning(f"Server directory does not exist: {server_dir}")
                continue

            logger.info(f"Searching for servers in: {server_dir}")
            found = self._scan_directory(server_dir)
            servers_found += found

        logger.info(f"Discovered {servers_found} servers")
        return self._available_servers

    def _get_server_directories(self, config=None):
        """
        Get list of directories to search for server files

        Args:
            config: Optional configuration object

        Returns:
            List of directory paths
        """
        # Default server directory relative to this file
        server_dirs = [
            os.path.abspath(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "../mcp_server",
                )
            )
        ]

        # Add custom server directories from config if available
        if config:
            custom_dirs = config.get("server", "custom_server_dirs", default=[])
            if custom_dirs and isinstance(custom_dirs, list):
                server_dirs.extend(custom_dirs)

        return server_dirs

    def _scan_directory(self, server_dir):
        """
        Scan a directory for server files

        Args:
            server_dir: The directory to scan

        Returns:
            Number of servers found in this directory
        """
        servers_found = 0
        try:
            for file in os.listdir(server_dir):
                if file.endswith("_server.py") or file == "server.py":
                    if self._process_server_file(os.path.join(server_dir, file)):
                        servers_found += 1
        except Exception as e:
            logger.error(f"Error scanning directory {server_dir}: {e}", exc_info=True)

        return servers_found

    def _process_server_file(self, file_path):
        """
        Extract server information from a server file

        Args:
            file_path: Path to the server file

        Returns:
            True if server was successfully processed, False otherwise
        """
        try:
            # Default server name from filename
            filename = os.path.basename(file_path)
            server_name = filename.replace("_server.py", "").replace(".py", "").title()

            # Try to parse server name from file content
            try:
                with open(file_path, "r") as f:
                    content = f.read()
                    match = self.SERVER_NAME_PATTERN.search(content)
                    if match:
                        server_name = match.group(1)
            except Exception as e:
                logger.warning(f"Error parsing server name from {file_path}: {e}")

            # Add to available servers
            self._available_servers.append({"name": server_name, "path": file_path})
            logger.info(f"Found server: {server_name} at {file_path}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to process server file {file_path}: {e}", exc_info=True
            )
            return False
