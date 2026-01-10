"""
WebSocket chat endpoint for real-time agent interaction.
"""

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.agent.agent import PerpeeAgent
from src.agent.dependencies import AgentDependencies
from src.api.schemas import (
    ChatMessage,
    create_error_message,
    create_response_message,
    create_thinking_message,
    create_welcome_message,
)
from src.database.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ConnectionManager:
    """
    Manages WebSocket connections.

    Each connection gets its own agent instance for conversation memory.
    """

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.agents: dict[str, PerpeeAgent] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        # Each connection gets its own agent for conversation memory
        self.agents[session_id] = PerpeeAgent()
        logger.info(f"WebSocket connected: {session_id}")

    def disconnect(self, session_id: str) -> None:
        """Handle a WebSocket disconnection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.agents:
            del self.agents[session_id]
        logger.info(f"WebSocket disconnected: {session_id}")

    async def send_json(self, session_id: str, data: dict[str, Any]) -> None:
        """Send JSON data to a specific connection."""
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(data)

    def get_agent(self, session_id: str) -> PerpeeAgent | None:
        """Get the agent for a session."""
        return self.agents.get(session_id)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat with the agent.

    Message flow:
    1. Client connects, receives welcome message
    2. Client sends message (type: "message", content: "...")
    3. Server sends thinking indicator
    4. Server processes with agent
    5. Server sends response (or error)

    Client message format:
        {"type": "message", "content": "Track this product: ..."}

    Server message types:
        - welcome: Connection established
        - thinking: Agent is processing
        - tool_call: Agent is calling a tool
        - tool_result: Tool execution result
        - response: Agent response
        - error: Error occurred
    """
    # Generate session ID
    session_id = str(uuid.uuid4())

    # Accept connection
    await manager.connect(websocket, session_id)

    try:
        # Send welcome message
        await manager.send_json(session_id, create_welcome_message(session_id))

        # Message loop
        while True:
            try:
                # Receive message
                raw_message = await websocket.receive_text()
                data = json.loads(raw_message)

                # Validate message
                if data.get("type") != "message":
                    await manager.send_json(
                        session_id,
                        create_error_message("Invalid message type"),
                    )
                    continue

                content = data.get("content", "").strip()
                if not content:
                    await manager.send_json(
                        session_id,
                        create_error_message("Empty message"),
                    )
                    continue

                # Validate with schema
                try:
                    ChatMessage(content=content)
                except Exception as e:
                    await manager.send_json(
                        session_id,
                        create_error_message(f"Invalid message: {e}"),
                    )
                    continue

                # Send thinking indicator
                await manager.send_json(session_id, create_thinking_message())

                # Get agent for this session
                agent = manager.get_agent(session_id)
                if not agent:
                    await manager.send_json(
                        session_id,
                        create_error_message("Session not found"),
                    )
                    continue

                # Process with agent
                async with get_session() as db_session:
                    deps = AgentDependencies(session=db_session)
                    response = await agent.chat(deps, content)

                # Send response
                if response.success:
                    await manager.send_json(
                        session_id,
                        create_response_message(response.text),
                    )
                else:
                    await manager.send_json(
                        session_id,
                        create_error_message(response.error or "Unknown error"),
                    )

            except json.JSONDecodeError:
                await manager.send_json(
                    session_id,
                    create_error_message("Invalid JSON"),
                )
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await manager.send_json(
                    session_id,
                    create_error_message(f"Error: {str(e)}"),
                )

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(session_id)


@router.get("/sessions/{session_id}/clear")
async def clear_session_memory(session_id: str):
    """
    Clear conversation memory for a session.

    Useful for starting a fresh conversation.
    """
    agent = manager.get_agent(session_id)
    if agent:
        agent.clear_memory()
        return {"message": "Memory cleared"}
    return {"message": "Session not found"}
