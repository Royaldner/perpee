"""
Chat/WebSocket API schemas.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from src.api.schemas.common import BaseSchema


class MessageType(str, Enum):
    """WebSocket message types."""

    # Client -> Server
    MESSAGE = "message"  # User message

    # Server -> Client
    WELCOME = "welcome"  # Connection established
    THINKING = "thinking"  # Agent is processing
    TOOL_CALL = "tool_call"  # Agent is calling a tool
    TOOL_RESULT = "tool_result"  # Tool execution result
    RESPONSE = "response"  # Agent response
    ERROR = "error"  # Error occurred


class ChatMessage(BaseSchema):
    """Chat message from client."""

    content: str = Field(..., min_length=1, max_length=4000, description="Message content")


class WebSocketMessage(BaseSchema):
    """WebSocket message wrapper."""

    type: MessageType
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WelcomeMessage(BaseSchema):
    """Welcome message data."""

    message: str = "Connected to Perpee Agent"
    session_id: str | None = None


class ThinkingMessage(BaseSchema):
    """Thinking indicator data."""

    message: str = "Thinking..."


class ToolCallMessage(BaseSchema):
    """Tool call notification data."""

    tool_name: str
    tool_args: dict[str, Any] = Field(default_factory=dict)


class ToolResultMessage(BaseSchema):
    """Tool result data."""

    tool_name: str
    success: bool
    result: Any = None
    error: str | None = None


class ResponseMessage(BaseSchema):
    """Agent response data."""

    content: str
    tool_calls: list[ToolCallMessage] = Field(default_factory=list)


class ErrorMessage(BaseSchema):
    """Error message data."""

    message: str
    code: str | None = None


# Helper functions for creating WebSocket messages
def create_welcome_message(session_id: str | None = None) -> dict[str, Any]:
    """Create a welcome message."""
    return WebSocketMessage(
        type=MessageType.WELCOME,
        data=WelcomeMessage(session_id=session_id).model_dump(),
    ).model_dump()


def create_thinking_message() -> dict[str, Any]:
    """Create a thinking indicator message."""
    return WebSocketMessage(
        type=MessageType.THINKING,
        data=ThinkingMessage().model_dump(),
    ).model_dump()


def create_tool_call_message(tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
    """Create a tool call notification message."""
    return WebSocketMessage(
        type=MessageType.TOOL_CALL,
        data=ToolCallMessage(tool_name=tool_name, tool_args=tool_args).model_dump(),
    ).model_dump()


def create_tool_result_message(
    tool_name: str,
    success: bool,
    result: Any = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Create a tool result message."""
    return WebSocketMessage(
        type=MessageType.TOOL_RESULT,
        data=ToolResultMessage(
            tool_name=tool_name,
            success=success,
            result=result,
            error=error,
        ).model_dump(),
    ).model_dump()


def create_response_message(content: str) -> dict[str, Any]:
    """Create an agent response message."""
    return WebSocketMessage(
        type=MessageType.RESPONSE,
        data=ResponseMessage(content=content).model_dump(),
    ).model_dump()


def create_error_message(message: str, code: str | None = None) -> dict[str, Any]:
    """Create an error message."""
    return WebSocketMessage(
        type=MessageType.ERROR,
        data=ErrorMessage(message=message, code=code).model_dump(),
    ).model_dump()
