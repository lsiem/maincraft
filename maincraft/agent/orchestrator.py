"""LangGraph ReAct agent orchestrator for the Modpack Knowledge Engine."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from agent.tools import ALL_TOOLS, set_active_pack
from config import PackId

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert Minecraft modpack assistant, specialized in heavily altered \
progression packs like GTNH and Enigmatica. You have two memory sources: a vector database of quest \
lines, wiki facts, and custom recipes; and a local markdown wiki tracking the player's specific \
world state.

When asked a technical question or 'what's next', prioritize retrieving facts from the Questbook \
chunks in the vector DB using search_modpack_knowledge. When advising on progression, check the \
local markdown wiki (read_player_state) to understand what resources and infrastructure the player \
already has. Start by reading the 'index' page to see what player state is tracked.

Never assume default mod recipes — these packs heavily modify them. If you learn something new \
about the player's world, use update_player_state to update the markdown wiki so you don't forget.

Active modpack: {pack}
"""

TOOL_LABELS = {
    "search_modpack_knowledge": "Searching modpack knowledge…",
    "read_player_state": "Reading your world state…",
    "update_player_state": "Updating your world state…",
}


def _get_llm():
    """Return the configured chat model."""
    from config import LLM_BACKEND, OLLAMA_BASE_URL, OLLAMA_CHAT_MODEL, OPENAI_API_KEY, OPENAI_CHAT_MODEL

    if LLM_BACKEND == "openai" and OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=OPENAI_CHAT_MODEL, api_key=OPENAI_API_KEY, temperature=0.3)
    else:
        from langchain_ollama import ChatOllama

        return ChatOllama(model=OLLAMA_CHAT_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.3)


def _history_to_messages(history: list[dict[str, str]], pack_id: PackId) -> list:
    """Convert stored message dicts to LangChain message objects."""
    messages: list = [SystemMessage(content=SYSTEM_PROMPT.format(pack=pack_id))]
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    return messages


class ModpackAgent:
    """Wrapper around the LangGraph ReAct agent."""

    def __init__(self, pack_id: PackId = "gtnh") -> None:
        set_active_pack(pack_id)
        self.pack_id = pack_id
        self._agent = self._build_agent()

    def _build_agent(self):
        llm = _get_llm()
        return create_react_agent(llm, ALL_TOOLS)

    def set_pack(self, pack_id: PackId) -> None:
        self.pack_id = pack_id
        set_active_pack(pack_id)
        self._agent = self._build_agent()

    def ask(self, question: str) -> str:
        """Send a question to the agent and return the final answer."""
        return self._collect_stream(self.stream_with_history([{"role": "user", "content": question}], self.pack_id))

    def describe_world(self, description: str) -> str:
        """Route a world description through the agent to update session wiki."""
        prompt = (
            f"The player wants to update their world state. Here is what they said:\n\n"
            f'"{description}"\n\n'
            f"Read the current session wiki index and relevant pages, then update the appropriate "
            f"entity pages (progression, base_infrastructure, bottlenecks) with this new information. "
            f"Be concise and factual."
        )
        return self.ask(prompt)

    def stream_with_history(
        self,
        history: list[dict[str, str]],
        pack_id: PackId | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Stream agent events: token deltas and tool activity.

        Yields dicts with keys:
          - type: "token" | "tool" | "done" | "error"
          - content: str (for token/tool/error)
          - full: str (for done — complete assistant reply)
        """
        pack = pack_id or self.pack_id
        set_active_pack(pack)
        messages = _history_to_messages(history, pack)
        full_response = ""

        try:
            for event in self._agent.stream(
                {"messages": messages},
                stream_mode="messages",
            ):
                msg, metadata = event if isinstance(event, tuple) else (event, {})
                node = metadata.get("langgraph_node", "") if isinstance(metadata, dict) else ""

                # Tool call announcements
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for tc in msg.tool_calls:
                        name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                        label = TOOL_LABELS.get(name, f"Using {name}…")
                        yield {"type": "tool", "content": label}

                # Token streaming from LLM
                if isinstance(msg, (AIMessage, AIMessageChunk)) and msg.content and node == "agent":
                    chunk = msg.content if isinstance(msg.content, str) else str(msg.content)
                    if chunk:
                        full_response += chunk
                        yield {"type": "token", "content": chunk}

            yield {"type": "done", "content": full_response, "full": full_response}

        except Exception as exc:
            logger.error("Agent stream failed: %s", exc)
            yield {"type": "error", "content": f"Agent error: {exc}"}

    def _collect_stream(self, stream: Iterator[dict[str, Any]]) -> str:
        result = ""
        for event in stream:
            if event["type"] == "done":
                result = event.get("full", "")
            elif event["type"] == "error":
                result = event["content"]
        return result or "No response from agent."


def create_agent(pack_id: PackId = "gtnh") -> ModpackAgent:
    return ModpackAgent(pack_id=pack_id)
