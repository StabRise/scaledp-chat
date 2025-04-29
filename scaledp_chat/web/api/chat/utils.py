from typing import Any, List

from langchain_core.messages import ChatMessage
from langgraph.graph.message import BaseMessage

from .schema import ClientMessage


def convert_to_langgraph_messages(messages: List[ClientMessage]) -> List[BaseMessage]:
    """
    Convert a list of ClientMessage objects to LangGraph BaseMessage objects.

    This function transforms client-side message objects into a format compatible
    with LangGraph's messaging system. Each message is converted to a ChatMessage
    with structured content.

    Args:
        messages (List[ClientMessage]): A list of client-side message
        objects to convert.

    Returns:
        List[BaseMessage]: A list of LangGraph BaseMessage objects, where each message
        contains the original content structured as a chat message with text content.

    Example:
        >>> client_msgs = [ClientMessage(role="user", content="Hello")]
        >>> langgraph_msgs = convert_to_langgraph_messages(client_msgs)
        >>> print(langgraph_msgs[0].content)
        [{'type': 'text', 'text': 'Hello'}]
    """
    langgraph_messages: List[BaseMessage] = []

    for message in messages:
        message_content: List[str | dict[Any, Any]] = []

        # Add text content
        message_content.append(
            {
                "type": "text",
                "text": message.content,
            },
        )

        langgraph_messages.append(
            ChatMessage(
                type="chat",
                role=message.role,
                content=message_content,
            ),
        )

    return langgraph_messages
