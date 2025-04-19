import os
import re
from distiller_cm5_python.utils.logger import logger
from distiller_cm5_python.utils.config import config


class ServerDiscovery:
    """
    Handles MCP server discovery for the MCPClientBridge.

    Searches for server scripts in the file system and extracts server info.
    """

    def __init__(self, bridge):
        """Initialize the server discovery manager.

        Args:
            bridge: The parent MCPClientBridge instance
        """
        self._bridge = bridge
        self._available_servers = []

    @property
    def available_servers(self):
        """Get the list of available servers.

        Returns:
            List of server info dictionaries with name and path keys
        """
        return self._available_servers

    def discover_mcp_servers(self):
        """Discover available MCP servers from the file system."""
        logger.info("Discovering MCP servers")
        self._available_servers = []

        # Look in default server directory
        server_dirs = [
            os.path.abspath(
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "../mcp_server",
                )
            )
        ]

        # Add any custom server directories from config
        custom_server_dirs = config.get("server", "custom_server_dirs", default=[])
        if custom_server_dirs and isinstance(custom_server_dirs, list):
            server_dirs.extend(custom_server_dirs)

        for server_dir in server_dirs:
            if not os.path.exists(server_dir):
                logger.warning(f"Server directory does not exist: {server_dir}")
                continue

            logger.info(f"Searching for servers in: {server_dir}")
            try:
                for file in os.listdir(server_dir):
                    if file.endswith("_server.py") or (file == "server.py"):
                        file_path = os.path.join(server_dir, file)

                        # Try to extract server name
                        server_name = (
                            file.replace("_server.py", "").replace(".py", "").title()
                        )

                        # Try to parse server name from file
                        try:
                            with open(file_path, "r") as f:
                                content = f.read()
                                server_name_match = re.search(
                                    r'SERVER_NAME\s*=\s*[\'"](.+?)[\'"]', content
                                )
                                if server_name_match:
                                    server_name = server_name_match.group(1)
                        except Exception as e:
                            logger.warning(
                                f"Error parsing server name from {file_path}: {e}"
                            )

                        self._available_servers.append(
                            {"name": server_name, "path": file_path}
                        )
                        logger.info(f"Found server: {server_name} at {file_path}")
            except Exception as e:
                logger.error(
                    f"Error discovering servers in {server_dir}: {e}", exc_info=True
                )

        logger.info(f"Discovered {len(self._available_servers)} servers")
