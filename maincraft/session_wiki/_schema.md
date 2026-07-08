---
title: Session Wiki Schema
---

# Session Wiki Schema

This directory is the **dynamic memory** for the Modpack Knowledge Engine.
The LLM reads and writes markdown files here to track the player's specific world state.

## Conventions

### File types

| File | Purpose |
|------|---------|
| `index.md` | Catalog of all wiki pages — read this first |
| `log.md` | Append-only chronological journal |
| `_schema.md` | This file — conventions the agent follows |
| `<entity>.md` | Player state pages (e.g. `progression.md`, `base_infrastructure.md`) |

### Entity page frontmatter

```yaml
---
pack: gtnh          # active modpack: gtnh | e2e | e6 | e9
tags: [power, fluids]
current_tier: LV
updated: 2026-07-08
---
```

### Log entry format

```
## [2026-07-08] update | base_infrastructure
Player built a steam boiler setup with 2 LV turbines.
```

### Agent workflows

1. **Before advising on progression**: read `index.md`, then relevant entity pages.
2. **When learning new player info**: update the entity page, refresh `index.md`, append to `log.md`.
3. **Never delete pages** — mark stale sections with `> [stale]` prefix instead.
