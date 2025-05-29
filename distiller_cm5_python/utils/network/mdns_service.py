#!/usr/bin/env python3
"""
mDNS Service Advertisement module.
Provides mDNS service discovery for the web interface.
"""

import logging
import socket
import asyncio
import uuid
import re
from typing import Optional, Tuple
from zeroconf import ServiceInfo, Zeroconf
from zeroconf.asyncio import AsyncZeroconf

logger = logging.getLogger(__name__)

class MDNSService:
    """
    mDNS Service Advertisement class.
    """
    
    def __init__(self, service_name: Optional[str] = None, domain: str = "local"):
        """
        Initialize mDNS service.
        
        Args:
            service_name: Service name (default: auto-generated from hostname)
            domain: Domain suffix (default: local)
        """
        self.service_name = service_name or self._auto_generate_name()
        self.domain = domain
        self.zeroconf = None
        self.service_info = None
        self.async_zeroconf = None
        logger.info(f"Initialized mDNS service with name: {self.service_name}")
    
    def _auto_generate_name(self) -> str:
        """
        Auto-generate a service name based on the device's hostname.
        
        Returns:
            A unique service name
        """
        hostname = socket.gethostname().lower()
        
        # Clean up hostname to ensure it's DNS-compatible
        # Replace any non-alphanumeric chars with hyphens
        clean_hostname = re.sub(r'[^a-z0-9-]', '-', hostname)
        
        # If hostname doesn't start with 'distiller', add it as a prefix
        if not clean_hostname.startswith('distiller'):
            service_name = f"distiller-{clean_hostname}"
        else:
            service_name = clean_hostname
            
        # Ensure we don't exceed 63 characters for the DNS label
        if len(service_name) > 63:
            # If too long, use a shorter name with a unique identifier
            mac = self._get_mac_address()
            if mac:
                # Use last 6 chars of MAC address
                short_id = mac.replace(':', '')[-6:]
            else:
                # Fallback to random ID
                short_id = str(uuid.uuid4())[:6]
            
            service_name = f"distiller-{short_id}"
            
        return service_name
    
    def _get_mac_address(self) -> Optional[str]:
        """
        Get the MAC address of the primary network interface.
        
        Returns:
            MAC address or None if not found
        """
        try:
            # This is platform dependent but works on Linux
            try:
                with open('/sys/class/net/eth0/address', 'r') as f:
                    return f.read().strip()
            except:
                # Try wifi interface
                with open('/sys/class/net/wlan0/address', 'r') as f:
                    return f.read().strip()
        except:
            return None
        
    async def start_service(self, port: int = 8080, service_type: str = "_http._tcp.") -> bool:
        """
        Start mDNS service advertisement.
        
        Args:
            port: Port number to advertise
            service_type: Service type (default: _http._tcp.)
            
        Returns:
            True if service started successfully
        """
        try:
            hostname = socket.gethostname()
            ip_address = self._get_ip_address()
            
            if not ip_address:
                logger.error("Failed to get IP address")
                return False
                
            logger.info(f"Starting mDNS service for {self.service_name}.{self.domain} on {ip_address}:{port}")
            
            self.async_zeroconf = AsyncZeroconf()
            
            # Ensure proper DNS formatting with trailing dots
            domain_with_dot = f"{self.domain}." if not self.domain.endswith('.') else self.domain
            
            # Construct proper service type name
            type_name = f"{service_type}{domain_with_dot}"
            
            # Construct full service name
            service_name = f"{self.service_name}.{service_type}{domain_with_dot}"
            
            # Construct server name with trailing dot
            server_name = f"{hostname}.{domain_with_dot}"
            
            self.service_info = ServiceInfo(
                type_name,
                service_name,
                addresses=[socket.inet_aton(ip_address)],
                port=port,
                properties={"path": "/"},
                server=server_name
            )
            
            await self.async_zeroconf.async_register_service(self.service_info)
            logger.info(f"mDNS service started: {self.service_name}.{self.domain}")
            return True
        except Exception as e:
            logger.error(f"Failed to start mDNS service: {str(e)}")
            return False
    
    async def stop_service(self) -> bool:
        """
        Stop mDNS service advertisement.
        
        Returns:
            True if service stopped successfully
        """
        try:
            if self.async_zeroconf and self.service_info:
                logger.info(f"Stopping mDNS service: {self.service_name}.{self.domain}")
                await self.async_zeroconf.async_unregister_service(self.service_info)
                await self.async_zeroconf.async_close()
                self.async_zeroconf = None
                self.service_info = None
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to stop mDNS service: {str(e)}")
            return False
    
    def _get_ip_address(self) -> Optional[str]:
        """
        Get the device's IP address.
        
        Returns:
            IP address or None if not found
        """
        try:
            # This creates a socket that doesn't actually connect
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Try to "connect" to a public IP (doesn't actually send packets)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
            s.close()
            return ip_address
        except Exception as e:
            logger.error(f"Failed to get IP address: {str(e)}")
            return None 