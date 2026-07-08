"""Extract recipe changes and comments from KubeJS and ZenScript files."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from config import PACKS, RAW_DIR, PackId

logger = logging.getLogger(__name__)


@dataclass
class ScriptChunk:
    pack: str
    source_file: str
    body: str
    metadata: dict = field(default_factory=dict)


# KubeJS recipe operation patterns
_KUBEJS_RECIPE_OPS = re.compile(
    r"(?:event\.recipes|recipes)\."
    r"(remove|replaceInput|replaceOutput|custom|shaped|shapeless|smelting|blasting|"
    r"campfire|cooking|stonecutting|smithing)\s*\(",
    re.IGNORECASE,
)

# ZenScript recipe patterns
_ZSCRIPT_RECIPE_OPS = re.compile(
    r"(?:mods\.|recipes\.)(?:remove|addShaped|addShapeless|removeShaped|removeShapeless|"
    r"addFurnace|removeFurnace|addBlast|removeBlast)\s*\(",
    re.IGNORECASE,
)

# Comment patterns
_JS_COMMENT = re.compile(r"//\s*(.+)")
_ZS_COMMENT = re.compile(r"//\s*(.+)")


def _extract_comments(content: str, comment_re: re.Pattern[str]) -> list[str]:
    return [m.group(1).strip() for m in comment_re.finditer(content) if m.group(1).strip()]


def _extract_recipe_ops(content: str, op_re: re.Pattern[str]) -> list[str]:
    """Extract recipe modification lines with surrounding context."""
    lines = content.splitlines()
    ops: list[str] = []
    for i, line in enumerate(lines):
        if op_re.search(line):
            # Grab the operation line and up to 2 preceding comment lines
            context_comments = []
            for j in range(max(0, i - 2), i):
                cm = _JS_COMMENT.search(lines[j])
                if cm:
                    context_comments.append(cm.group(1).strip())
            op_text = line.strip()
            if context_comments:
                ops.append(f"{'; '.join(context_comments)} → {op_text}")
            else:
                ops.append(op_text)
    return ops


def _parse_kubejs_file(path: Path, pack: str) -> list[ScriptChunk]:
    content = path.read_text(encoding="utf-8", errors="replace")
    rel = str(path)
    chunks: list[ScriptChunk] = []

    comments = _extract_comments(content, _JS_COMMENT)
    recipe_ops = _extract_recipe_ops(content, _KUBEJS_RECIPE_OPS)

    if comments:
        body = f"# Script comments: {path.name}\n\n" + "\n".join(f"- {c}" for c in comments)
        chunks.append(ScriptChunk(
            pack=pack,
            source_file=rel,
            body=body,
            metadata={"pack": pack, "type": "recipe_change", "source_file": rel, "subtype": "comment"},
        ))

    if recipe_ops:
        body = f"# Recipe changes: {path.name}\n\n" + "\n".join(f"- {op}" for op in recipe_ops)
        chunks.append(ScriptChunk(
            pack=pack,
            source_file=rel,
            body=body,
            metadata={"pack": pack, "type": "recipe_change", "source_file": rel, "subtype": "recipe_op"},
        ))

    return chunks


def _parse_zenscript_file(path: Path, pack: str) -> list[ScriptChunk]:
    content = path.read_text(encoding="utf-8", errors="replace")
    rel = str(path)
    chunks: list[ScriptChunk] = []

    comments = _extract_comments(content, _ZS_COMMENT)
    recipe_ops = _extract_recipe_ops(content, _ZSCRIPT_RECIPE_OPS)

    if comments:
        body = f"# Script comments: {path.name}\n\n" + "\n".join(f"- {c}" for c in comments)
        chunks.append(ScriptChunk(
            pack=pack,
            source_file=rel,
            body=body,
            metadata={"pack": pack, "type": "recipe_change", "source_file": rel, "subtype": "comment"},
        ))

    if recipe_ops:
        body = f"# Recipe changes: {path.name}\n\n" + "\n".join(f"- {op}" for op in recipe_ops)
        chunks.append(ScriptChunk(
            pack=pack,
            source_file=rel,
            body=body,
            metadata={"pack": pack, "type": "recipe_change", "source_file": rel, "subtype": "recipe_op"},
        ))

    return chunks


def parse_scripts(pack_id: PackId, raw_dir: Path | None = None) -> list[ScriptChunk]:
    """Parse KubeJS or ZenScript files for a pack."""
    pack = PACKS[pack_id]
    raw_dir = raw_dir or RAW_DIR / pack_id
    chunks: list[ScriptChunk] = []

    for script_dir in pack.script_dirs:
        base = raw_dir / script_dir
        if not base.exists():
            logger.debug("Script dir not found: %s", base)
            continue

        for f in sorted(base.rglob("*")):
            if not f.is_file():
                continue
            suffix = f.suffix.lower()
            if suffix in (".js", ".ts"):
                chunks.extend(_parse_kubejs_file(f, pack_id))
            elif suffix == ".zs":
                chunks.extend(_parse_zenscript_file(f, pack_id))

    logger.info("Parsed %d script chunks from %s", len(chunks), pack_id)
    return chunks


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for pid in ("e2e", "e6", "e9"):
        chunks = parse_scripts(pid)  # type: ignore[arg-type]
        print(f"{pid}: {len(chunks)} script chunks")
