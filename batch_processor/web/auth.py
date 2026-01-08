"""
Authentication and session management for the batch Excel processor.

This module provides HTTP Basic Auth implementation and session management
functionality for user authentication and access control.
"""

import uuid
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBasicCredentials, HTTPBasic
import secrets

from ..config.settings import get_config
from ..services.logging_service import get_structured_logger


class SessionManager:
    """Manages user sessions and authentication state."""
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._session_files: Dict[str, List[str]] = {}  # Track files per session
        self.security = HTTPBasic()
        self.structured_logger = get_structured_logger(__name__)
    
    def create_session(self, username: str) -> str:
        """
        Create a new session for authenticated user.
        
        Args:
            username: Authenticated username
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        config = get_config()
        
        self._sessions[session_id] = {
            "username": username,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=config.security.session_timeout_hours),
            "last_activity": datetime.utcnow()
        }
        
        # Initialize file tracking for this session
        self._session_files[session_id] = []
        
        return session_id
    
    def add_session_file(self, session_id: str, file_path: str) -> None:
        """
        Track a file associated with a session.
        
        Args:
            session_id: Session identifier
            file_path: Path to file to track
        """
        if session_id in self._session_files:
            self._session_files[session_id].append(file_path)
    
    def get_session_files(self, session_id: str) -> List[str]:
        """
        Get all files associated with a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of file paths associated with the session
        """
        return self._session_files.get(session_id, [])
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session information by session ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data if valid, None otherwise
        """
        if session_id not in self._sessions:
            return None
        
        session = self._sessions[session_id]
        
        # Check if session has expired
        if datetime.utcnow() > session["expires_at"]:
            del self._sessions[session_id]
            return None
        
        # Update last activity
        session["last_activity"] = datetime.utcnow()
        return session
    
    def invalidate_session(self, session_id: str) -> None:
        """
        Invalidate a session and clean up associated files.
        
        Args:
            session_id: Session identifier to invalidate
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
        
        # Clean up file tracking
        if session_id in self._session_files:
            del self._session_files[session_id]
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions and clean up associated files.
        
        Returns:
            Number of sessions cleaned up
        """
        current_time = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, session in self._sessions.items()
            if current_time > session["expires_at"]
        ]
        
        for session_id in expired_sessions:
            # Clean up session data
            del self._sessions[session_id]
            
            # Clean up file tracking
            if session_id in self._session_files:
                del self._session_files[session_id]
        
        return len(expired_sessions)
    
    def authenticate_user(self, credentials: HTTPBasicCredentials = Depends(HTTPBasic())) -> str:
        """
        Authenticate user with HTTP Basic Auth.
        
        Args:
            credentials: HTTP Basic Auth credentials
            
        Returns:
            Username if authentication successful
            
        Raises:
            HTTPException: If authentication fails
        """
        config = get_config()
        
        if not config.auth.enabled:
            return "anonymous"
        
        # Check if user exists and password is correct
        if (credentials.username in config.auth.users and 
            secrets.compare_digest(
                credentials.password.encode("utf-8"),
                config.auth.users[credentials.username].encode("utf-8")
            )):
            # Log successful authentication
            self.structured_logger.log_authentication(
                user=credentials.username,
                success=True
            )
            return credentials.username
        
        # Log failed authentication
        self.structured_logger.log_authentication(
            user=credentials.username,
            success=False
        )
        
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    def create_user_session(self, username: str) -> str:
        """
        Create a session for authenticated user and return session ID.
        
        Args:
            username: Authenticated username
            
        Returns:
            Session ID for tracking user activities
        """
        return self.create_session(username)
    
    def validate_user_access(self, username: str, session_id: str) -> bool:
        """
        Validate that a user has access to a specific session.
        
        Args:
            username: Username to validate
            session_id: Session ID to check access for
            
        Returns:
            True if user has access, False otherwise
        """
        # For now, allow access to any session for authenticated users
        # In a more complex system, you might track session ownership
        return username is not None
    
    def get_user_sessions(self, username: str) -> list:
        """
        Get all active sessions for a user.
        
        Args:
            username: Username to get sessions for
            
        Returns:
            List of session IDs owned by the user
        """
        user_sessions = []
        current_time = datetime.utcnow()
        
        for session_id, session_data in self._sessions.items():
            if (session_data["username"] == username and 
                current_time <= session_data["expires_at"]):
                user_sessions.append(session_id)
        
        return user_sessions


# Global session manager instance
session_manager = SessionManager()


def get_current_user(credentials: HTTPBasicCredentials = Depends(HTTPBasic())) -> str:
    """
    Dependency to get current authenticated user.
    
    Args:
        credentials: HTTP Basic Auth credentials
        
    Returns:
        Username of authenticated user
    """
    return session_manager.authenticate_user(credentials)


def require_auth(user: str = Depends(get_current_user)) -> str:
    """
    Dependency that requires authentication.
    
    Args:
        user: Authenticated user from get_current_user
        
    Returns:
        Username of authenticated user
    """
    return user