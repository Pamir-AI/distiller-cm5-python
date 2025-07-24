"""
Session Manager for WiFi Setup

Manages user setup sessions with automatic cleanup and state tracking
for seamless user experience across network transitions.
"""

import time
import uuid
import logging
import threading
from typing import Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Setup session status states"""
    INITIATED = "initiated"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class SetupSession:
    """Setup session data container"""
    session_id: str
    target_ssid: str
    start_time: float
    status: SessionStatus
    user_agent: Optional[str] = None
    target_password_hash: Optional[str] = None  # For validation, not storage
    success_page_cached: bool = False
    connection_details: Optional[Dict[str, Any]] = None
    last_activity: Optional[float] = None
    
    def __post_init__(self):
        if self.last_activity is None:
            self.last_activity = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['status'] = self.status.value
        return data
    
    def is_expired(self, timeout_seconds: int = 1800) -> bool:  # 30 minutes
        """Check if session has expired"""
        return time.time() - self.start_time > timeout_seconds
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = time.time()


class SessionManager:
    """Manages WiFi setup sessions with automatic cleanup"""
    
    def __init__(self, cleanup_interval: int = 300):  # 5 minutes
        self.sessions: Dict[str, SetupSession] = {}
        self.cleanup_interval = cleanup_interval
        self._lock = threading.RLock()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        logger.info("Session cleanup thread started")
    
    def _cleanup_worker(self):
        """Background worker for session cleanup"""
        while self._running:
            try:
                self.cleanup_expired_sessions()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")
                time.sleep(self.cleanup_interval)
    
    def create_session(
        self, 
        target_ssid: str, 
        user_agent: Optional[str] = None,
        target_password_hash: Optional[str] = None
    ) -> str:
        """Create a new setup session and return session ID"""
        with self._lock:
            session_id = str(uuid.uuid4())
            session = SetupSession(
                session_id=session_id,
                target_ssid=target_ssid,
                start_time=time.time(),
                status=SessionStatus.INITIATED,
                user_agent=user_agent,
                target_password_hash=target_password_hash
            )
            
            self.sessions[session_id] = session
            logger.info(f"Created setup session {session_id} for SSID '{target_ssid}'")
            return session_id
    
    def get_session(self, session_id: str) -> Optional[SetupSession]:
        """Get session by ID"""
        with self._lock:
            session = self.sessions.get(session_id)
            if session and session.is_expired():
                self.expire_session(session_id)
                return None
            if session:
                session.update_activity()
            return session
    
    def update_session_status(
        self, 
        session_id: str, 
        status: SessionStatus,
        connection_details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update session status and optionally connection details"""
        with self._lock:
            session = self.sessions.get(session_id)
            if not session or session.is_expired():
                return False
            
            session.status = status
            session.update_activity()
            
            if connection_details:
                session.connection_details = connection_details
            
            # Mark success page as cached when connected
            if status == SessionStatus.CONNECTED:
                session.success_page_cached = True
                
            logger.info(f"Updated session {session_id} status to {status.value}")
            return True
    
    def mark_success_page_cached(self, session_id: str) -> bool:
        """Mark that success page has been cached for session"""
        with self._lock:
            session = self.sessions.get(session_id)
            if session and not session.is_expired():
                session.success_page_cached = True
                session.update_activity()
                return True
            return False
    
    def get_sessions_by_ssid(self, ssid: str) -> list[SetupSession]:
        """Get all active sessions for a specific SSID"""
        with self._lock:
            active_sessions = []
            for session in self.sessions.values():
                if (session.target_ssid == ssid and 
                    not session.is_expired() and 
                    session.status in [SessionStatus.CONNECTING, SessionStatus.CONNECTED]):
                    active_sessions.append(session)
            return active_sessions
    
    def get_connecting_sessions(self) -> list[SetupSession]:
        """Get all sessions currently in connecting state"""
        with self._lock:
            return [
                session for session in self.sessions.values()
                if (session.status == SessionStatus.CONNECTING and 
                    not session.is_expired())
            ]
    
    def expire_session(self, session_id: str) -> bool:
        """Expire a specific session"""
        with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session.status = SessionStatus.EXPIRED
                logger.info(f"Expired session {session_id}")
                return True
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions and return count removed"""
        with self._lock:
            expired_ids = []
            for session_id, session in self.sessions.items():
                if session.is_expired() or session.status == SessionStatus.EXPIRED:
                    expired_ids.append(session_id)
            
            for session_id in expired_ids:
                del self.sessions[session_id]
            
            if expired_ids:
                logger.info(f"Cleaned up {len(expired_ids)} expired sessions")
            
            return len(expired_ids)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics for monitoring"""
        with self._lock:
            stats = {
                "total_sessions": len(self.sessions),
                "by_status": {},
                "oldest_session": None,
                "newest_session": None
            }
            
            # Count by status
            for session in self.sessions.values():
                status = session.status.value
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # Find oldest and newest
            if self.sessions:
                sessions_by_time = sorted(self.sessions.values(), key=lambda s: s.start_time)
                stats["oldest_session"] = sessions_by_time[0].start_time
                stats["newest_session"] = sessions_by_time[-1].start_time
            
            return stats
    
    def shutdown(self):
        """Shutdown session manager and cleanup thread"""
        self._running = False
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        logger.info("Session manager shutdown complete")


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def shutdown_session_manager():
    """Shutdown global session manager"""
    global _session_manager
    if _session_manager:
        _session_manager.shutdown()
        _session_manager = None