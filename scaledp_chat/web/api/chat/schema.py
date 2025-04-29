from typing import Any, List, Optional

from pydantic import BaseModel


class ClientAttachment(BaseModel):
    """Represents an attachment in a client message."""

    name: str
    contentType: str
    url: str


class ToolInvocation(BaseModel):
    """Represents a tool invocation within a message."""

    toolCallId: str
    toolName: str
    args: dict[str, Any]
    result: dict[str, Any]


class ClientMessage(BaseModel):
    """Represents a message from a client."""

    role: str
    content: str
    experimental_attachments: Optional[List[ClientAttachment]] = None
    toolInvocations: Optional[List[ToolInvocation]] = None


class Request(BaseModel):
    """Represents a request containing a list of client messages."""

    messages: List[ClientMessage]
