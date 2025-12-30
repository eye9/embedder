"""
Authentication and session management for the batch Excel processor.

This module provides HTTP Basic Auth implementation and session management
functionality for user authentication and access control.
"""

import uuid
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBasicCredentials, HTTPBasic
import secrets

from ..config.settings import get_config


class SessionManager:
    """Manages user sessions and authentication state."""
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self.security = HTTPBasic()
    
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
        
        return session_id
    
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
        Invalidate a session.
        
        Args:
            session_id: Session identifier to invalidate
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        current_time = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, session in self._sessions.items()
            if current_time > session["expires_at"]
        ]
        
        for session_id in expired_sessions:
            del self._sessions[session_id]
        
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
            return credentials.username
        
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


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