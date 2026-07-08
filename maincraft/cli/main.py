"""Rich CLI for the Modpack Knowledge Engine."""

from __future__ import annotations

import logging
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from agent.orchestrator import ModpackAgent, create_agent
from config import PACKS, PackId

console = Console()
logger = logging.getLogger(__name__)

HELP_TEXT = """
[bold]Commands:[/bold]
  /set-pack <gtnh|e2e|e6|e9>  Set active modpack context
  /describe-world <text>      Update player state in session wiki
  /reindex [--skip-wiki] [--wiki-playwright]  Re-run ingestion pipeline
  /help                       Show this help
  /quit                       Exit

  Or type any question to ask the guide.
"""


def _parse_command(line: str) -> tuple[str, str]:
    """Parse a slash command. Returns (command, args)."""
    line = line.strip()
    if not line.startswith("/"):
        return ("ask", line)
    parts = line[1:].split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    return (cmd, args)


def _handle_set_pack(agent: ModpackAgent, args: str) -> ModpackAgent:
    pack_id = args.strip().lower()
    if pack_id not in PACKS:
        console.print(f"[red]Unknown pack '{pack_id}'. Choose: {', '.join(PACKS.keys())}[/red]")
        return agent
    agent.set_pack(pack_id)  # type: ignore[arg-type]
    console.print(f"[green]Active pack set to {PACKS[pack_id].display_name}[/green]")
    return agent


def _handle_describe_world(agent: ModpackAgent, args: str) -> None:
    if not args:
        console.print("[red]Usage: /describe-world <description of your current setup>[/red]")
        return
    console.print("[dim]Updating session wiki…[/dim]")
    response = agent.describe_world(args)
    console.print(Panel(Markdown(response), title="World State Updated", border_style="green"))


def _handle_reindex(args: str) -> None:
    console.print("[dim]Starting ingestion pipeline…[/dim]")
    try:
        from ingestion.chunk_and_index import ingest_all, ingest_pack

        force = "--force" in args
        skip_wiki = "--skip-wiki" in args
        wiki_playwright = "--wiki-playwright" in args
        pack = args.strip().replace("--force", "").replace("--skip-wiki", "").replace("--wiki-playwright", "").strip()
        if pack in PACKS:
            count = ingest_pack(
                pack,  # type: ignore[arg-type]
                force_download=force,
                skip_wiki=skip_wiki,
                wiki_playwright=wiki_playwright,
            )
            console.print(f"[green]Indexed {count} chunks for {pack}[/green]")
            return

        results = ingest_all(
            force_download=force,
            skip_wiki=skip_wiki,
            wiki_playwright=wiki_playwright,
        )
        for pid, count in results.items():
            console.print(f"  {pid}: {count} chunks")
        console.print("[green]Reindex complete.[/green]")
    except Exception as exc:
        console.print(f"[red]Reindex failed: {exc}[/red]")


def main() -> None:
    logging.basicConfig(level=logging.WARNING)

    console.print(Panel(
        "[bold]Modpack Knowledge Engine[/bold]\n"
        "GTNH & Enigmatica conversational guide\n\n"
        "Type /help for commands.",
        border_style="blue",
    ))

    agent = create_agent("gtnh")

    while True:
        try:
            line = Prompt.ask(f"\n[bold cyan]({agent.pack_id})[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not line.strip():
            continue

        cmd, args = _parse_command(line)

        if cmd in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break
        elif cmd == "help":
            console.print(HELP_TEXT)
        elif cmd == "set-pack":
            agent = _handle_set_pack(agent, args)
        elif cmd == "describe-world":
            _handle_describe_world(agent, args)
        elif cmd == "reindex":
            _handle_reindex(args)
        elif cmd == "ask":
            if not args:
                continue
            console.print("[dim]Thinking…[/dim]")
            response = agent.ask(args)
            console.print(Panel(Markdown(response), title="Guide", border_style="blue"))
        else:
            console.print(f"[red]Unknown command '/{cmd}'. Type /help for available commands.[/red]")


if __name__ == "__main__":
    main()
