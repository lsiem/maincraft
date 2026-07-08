"""Central configuration for the Modpack Knowledge Engine."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CHROMA_DIR = DATA_DIR / "chroma"
SESSION_WIKI_DIR = PROJECT_ROOT / "session_wiki"
CHROMA_COLLECTION = "modpack_static"

# ---------------------------------------------------------------------------
# Model backends
# ---------------------------------------------------------------------------
LLM_BACKEND: Literal["ollama", "openai"] = os.getenv("LLM_BACKEND", "ollama")  # type: ignore[assignment]
EMBED_BACKEND: Literal["ollama", "openai"] = os.getenv("EMBED_BACKEND", "ollama")  # type: ignore[assignment]

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
QUEST_CHUNK_BOOST = 1.5  # retrieval weight multiplier for quest chunks

# ---------------------------------------------------------------------------
# Pack registry
# ---------------------------------------------------------------------------
PackId = Literal["gtnh", "e2e", "e6", "e9"]


@dataclass(frozen=True)
class PackConfig:
    id: PackId
    display_name: str
    github_repo: str
    github_branch: str
    quest_format: Literal["betterquesting_tree", "betterquesting_json", "ftbquests_snbt"]
    script_dirs: tuple[str, ...]
    doc_source: Literal["gtnh_wiki", "enigmatica_gitbook", "none"]


PACKS: dict[PackId, PackConfig] = {
    "gtnh": PackConfig(
        id="gtnh",
        display_name="GregTech: New Horizons",
        github_repo="GTNewHorizons/GT-New-Horizons-Modpack",
        github_branch="master",
        quest_format="betterquesting_tree",
        script_dirs=(),
        doc_source="gtnh_wiki",
    ),
    "e2e": PackConfig(
        id="e2e",
        display_name="Enigmatica 2: Expert",
        github_repo="EnigmaticaModpacks/Enigmatica2Expert",
        github_branch="master",
        quest_format="betterquesting_json",
        script_dirs=("scripts",),
        doc_source="none",
    ),
    "e6": PackConfig(
        id="e6",
        display_name="Enigmatica 6",
        github_repo="EnigmaticaModpacks/Enigmatica6",
        github_branch="master",
        quest_format="ftbquests_snbt",
        script_dirs=("kubejs/server_scripts",),
        doc_source="enigmatica_gitbook",
    ),
    "e9": PackConfig(
        id="e9",
        display_name="Enigmatica 9",
        github_repo="EnigmaticaModpacks/Enigmatica9",
        github_branch="master",
        quest_format="ftbquests_snbt",
        script_dirs=("kubejs/server_scripts",),
        doc_source="enigmatica_gitbook",
    ),
}

# GTNH wiki curated page list (progression / multiblock focus)
GTNH_WIKI_PRIORITY_PAGES: list[str] = [
    "Beginner_Tips",
    "Quest_Book",
    "Steam",
    "LV",
    "MV",
    "HV",
    "EV",
    "IV",
    "LuV",
    "ZPM",
    "UV",
    "UHV",
    "Multiblock",
    "Cleanroom",
    "Distillation_Tower",
    "Electric_Blast_Furnace",
    "Large_Chemical_Reactor",
    "Fusion_Reactor",
    "Stargate",
    "Power_Generation",
    "Ore_Processing",
    "Bee_Breeding",
    "Thaumcraft",
    "Blood_Magic",
    "Applied_Energistics_2",
]

# Enigmatica GitBook llms.txt entry point
ENIGMATICA_LLMS_URL = "https://wiki.enigmatica.net/main/llms.txt"
