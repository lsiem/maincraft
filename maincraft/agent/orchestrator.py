"""LangGraph ReAct agent orchestrator for the Modpack Knowledge Engine."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from agent.tools import ALL_TOOLS, get_active_pack, set_active_pack
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


def _get_llm():
    """Return the configured chat model."""
    from config import LLM_BACKEND, OLLAMA_BASE_URL, OLLAMA_CHAT_MODEL, OPENAI_API_KEY, OPENAI_CHAT_MODEL

    if LLM_BACKEND == "openai" and OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=OPENAI_CHAT_MODEL, api_key=OPENAI_API_KEY, temperature=0.3)
    else:
        from langchain_ollama import ChatOllama

        return ChatOllama(model=OLLAMA_CHAT_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.3)


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
        pack_name = self.pack_id
        system = SYSTEM_PROMPT.format(pack=pack_name)

        try:
            result = self._agent.invoke(
                {"messages": [SystemMessage(content=system), HumanMessage(content=question)]},
            )
            messages = result.get("messages", [])
            if messages:
                return messages[-1].content
            return "No response from agent."
        except Exception as exc:
            logger.error("Agent invocation failed: %s", exc)
            return f"Agent error: {exc}"

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


def create_agent(pack_id: PackId = "gtnh") -> ModpackAgent:
    return ModpackAgent(pack_id=pack_id)
