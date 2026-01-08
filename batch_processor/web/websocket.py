"""
WebSocket endpoints for real-time progress updates.

This module provides WebSocket connections for real-time progress tracking
of file processing tasks, allowing clients to receive live updates.
"""

import json
import logging
import asyncio
from typing import Dict, Set
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.routing import APIRouter
import redis.asyncio as redis

from ..config.settings import get_config
from ..services.progress_tracker import ProgressTracker
from .auth import get_current_user
from .models import ProgressUpdate


logger = logging.getLogger(__name__)

# Create router for WebSocket endpoints
router = APIRouter(tags=["websocket"])

# Connection manager for WebSocket connections
class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        # Store active connections by task_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.redis_client: redis.Redis = None
        self.pubsub_task: asyncio.Task = None
        
    async def initialize_redis(self):
        """Initialize Redis connection for pub/sub."""
        if self.redis_client is None:
            try:
                config = get_config()
                self.redis_client = redis.from_url(config.redis.url)
                
                # Test the connection
                await self.redis_client.ping()
                logger.info("Redis connection established successfully")
                
                # Start pub/sub listener
                if self.pubsub_task is None:
                    self.pubsub_task = asyncio.create_task(self._listen_for_updates())
                    
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. WebSocket will work in polling-only mode.")
                self.redis_client = None
    
    async def connect(self, websocket: WebSocket, task_id: str):
        """Accept a WebSocket connection and add it to the task's connection pool."""
        await websocket.accept()
        
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        
        self.active_connections[task_id].add(websocket)
        logger.info(f"WebSocket connected for task {task_id}. Total connections: {len(self.active_connections[task_id])}")
    
    def disconnect(self, websocket: WebSocket, task_id: str):
        """Remove a WebSocket connection from the task's connection pool."""
        if task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            
            # Clean up empty connection sets
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
        
        logger.info(f"WebSocket disconnected for task {task_id}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
    
    async def broadcast_to_task(self, task_id: str, message: str):
        """Broadcast a message to all connections for a specific task."""
        if task_id not in self.active_connections:
            return
        
        # Create a copy of the set to avoid modification during iteration
        connections = self.active_connections[task_id].copy()
        
        for websocket in connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                # Remove failed connection
                self.disconnect(websocket, task_id)
    
    async def _listen_for_updates(self):
        """Listen for Redis pub/sub messages and broadcast to WebSocket clients."""
        if self.redis_client is None:
            logger.info("Redis not available, skipping pub/sub listener")
            return
            
        try:
            pubsub = self.redis_client.pubsub()
            
            # Subscribe to all progress channels
            await pubsub.psubscribe("progress_channel:*")
            
            logger.info("Started listening for Redis pub/sub messages")
            
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    try:
                        # Extract task_id from channel name
                        channel = message["channel"].decode()
                        task_id = channel.split(":")[-1]
                        
                        # Parse and broadcast the message
                        data = json.loads(message["data"])
                        await self.broadcast_to_task(task_id, json.dumps(data))
                        
                    except Exception as e:
                        logger.error(f"Error processing pub/sub message: {e}")
                        
        except Exception as e:
            logger.error(f"Error in pub/sub listener: {e}")
            # Reset Redis client on connection failure
            self.redis_client = None
    
    async def get_current_progress(self, task_id: str) -> dict:
        """Get current progress for a task from Redis."""
        try:
            if self.redis_client is None:
                await self.initialize_redis()
                
            if self.redis_client is not None:
                progress_tracker = ProgressTracker(self.redis_client)
                return await progress_tracker.get_progress_async(task_id)
            else:
                logger.warning("Redis not available, cannot get current progress")
                return None
        except Exception as e:
            logger.error(f"Error getting current progress: {e}")
            return None


# Global connection manager
manager = ConnectionManager()


async def get_websocket_user(websocket: WebSocket, token: str = None) -> str:
    """
    Authenticate WebSocket connection.
    
    For WebSocket connections, we'll use a simple token-based auth
    or allow anonymous connections for now. In production, you might
    want to implement proper WebSocket authentication.
    """
    # For now, allow anonymous connections
    # In production, implement proper WebSocket authentication
    return "anonymous"


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    task_id: str,
    token: str = None
):
    """
    WebSocket endpoint for real-time progress updates.
    
    Clients can connect to this endpoint to receive real-time updates
    about task progress, including:
    - Progress percentage
    - Processed row counts
    - Error counts
    - Estimated time remaining
    - Current operation status
    """
    user = await get_websocket_user(websocket, token)
    
    # Initialize Redis connection if needed
    await manager.initialize_redis()
    
    # Connect to WebSocket
    await manager.connect(websocket, task_id)
    
    try:
        # Send current progress immediately upon connection
        current_progress = await manager.get_current_progress(task_id)
        if current_progress:
            await manager.send_personal_message(
                json.dumps(current_progress),
                websocket
            )
        else:
            # Send initial status
            initial_status = {
                "task_id": task_id,
                "progress": 0.0,
                "processed_rows": 0,
                "total_rows": 0,
                "error_count": 0,
                "status": "connected",
                "timestamp": datetime.utcnow().isoformat()
            }
            await manager.send_personal_message(
                json.dumps(initial_status),
                websocket
            )
        
        # Keep connection alive and handle client messages
        status_request_count = 0  # Track status requests to prevent spam
        max_status_requests = 100  # Limit status requests per connection
        
        while True:
            try:
                # Wait for client messages (ping/pong, etc.)
                data = await websocket.receive_text()
                
                # Handle client messages
                try:
                    message = json.loads(data)
                    
                    if message.get("type") == "ping":
                        # Respond to ping with pong
                        pong_response = {
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await manager.send_personal_message(
                            json.dumps(pong_response),
                            websocket
                        )
                    
                    elif message.get("type") == "get_status":
                        # Prevent status request spam
                        status_request_count += 1
                        if status_request_count > max_status_requests:
                            error_response = {
                                "type": "error",
                                "message": "Too many status requests",
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            await manager.send_personal_message(
                                json.dumps(error_response),
                                websocket
                            )
                            break
                        
                        # Send current progress with error handling
                        try:
                            current_progress = await manager.get_current_progress(task_id)
                            if current_progress:
                                await manager.send_personal_message(
                                    json.dumps(current_progress),
                                    websocket
                                )
                            else:
                                # Send fallback status if progress unavailable
                                fallback_status = {
                                    "task_id": task_id,
                                    "status": "unknown",
                                    "progress": 0.0,
                                    "timestamp": datetime.utcnow().isoformat()
                                }
                                await manager.send_personal_message(
                                    json.dumps(fallback_status),
                                    websocket
                                )
                        except Exception as e:
                            logger.error(f"Error getting progress for task {task_id}: {e}")
                            error_response = {
                                "type": "error",
                                "message": "Failed to get task status",
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            await manager.send_personal_message(
                                json.dumps(error_response),
                                websocket
                            )
                    
                except json.JSONDecodeError:
                    # Ignore invalid JSON messages
                    pass
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in WebSocket loop: {e}")
                break
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {e}")
    finally:
        manager.disconnect(websocket, task_id)
        logger.info(f"WebSocket connection closed for task {task_id}")


@router.get("/ws/info/{task_id}")
async def websocket_info(task_id: str):
    """
    Get WebSocket connection information for a task.
    
    Returns information about how to connect to the WebSocket
    for real-time progress updates.
    """
    config = get_config()
    
    return {
        "task_id": task_id,
        "websocket_url": f"ws://{config.web.host}:{config.web.port}/ws/{task_id}",
        "connection_info": {
            "protocol": "WebSocket",
            "message_format": "JSON",
            "supported_messages": [
                {
                    "type": "ping",
                    "description": "Send ping to keep connection alive"
                },
                {
                    "type": "get_status", 
                    "description": "Request current progress status"
                }
            ]
        },
        "progress_updates": {
            "automatic": True,
            "fields": [
                "task_id",
                "progress",
                "processed_rows", 
                "total_rows",
                "error_count",
                "estimated_time_remaining",
                "current_operation",
                "timestamp"
            ]
        }
    }


# Initialize the connection manager when the module is imported
async def startup_websocket():
    """Initialize WebSocket manager on startup."""
    try:
        await manager.initialize_redis()
    except Exception as e:
        logger.warning(f"WebSocket startup warning: {e}. Continuing without Redis.")


# Export the startup function for use in main app
__all__ = ["router", "startup_websocket", "manager"]