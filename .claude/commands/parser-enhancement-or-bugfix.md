---
name: parser-enhancement-or-bugfix
description: Workflow command scaffold for parser-enhancement-or-bugfix in maincraft.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /parser-enhancement-or-bugfix

Use this workflow when working on **parser-enhancement-or-bugfix** in `maincraft`.

## Goal

Implements enhancements or bugfixes to the BetterQuesting parser logic, such as improving prerequisite resolution, BBCode stripping, or tier inference.

## Common Files

- `maincraft/ingestion/parse_betterquesting.py`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Edit maincraft/ingestion/parse_betterquesting.py to implement the enhancement or bugfix.
- Update or refactor parsing functions as needed.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.