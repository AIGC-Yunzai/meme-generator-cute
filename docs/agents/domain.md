# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

Layout: **single-context**. One `GLOSSARY.md` and one `docs/adr/` at the repo root.

## Before exploring, read these

- **`GLOSSARY.md`** at the repo root, or
- **`GLOSSARY-MAP.md`** at the repo root if it exists: it points at one `GLOSSARY.md` per context. Read each one relevant to the topic.
- **`docs/adr/`**: read ADRs that touch the area you're about to work in.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily when terms or decisions actually get resolved.

## File structure

```
/
├── GLOSSARY.md          ← not yet created
├── docs/adr/            ← not yet created
├── docs/agents/         ← this config
├── memes/<meme_name>/   ← one meme: __init__.py + images/
└── tools/
```

## Terms this repo already relies on

`AGENTS.md` carries the working vocabulary for this codebase; treat it as the de-facto glossary until `GLOSSARY.md` exists. Terms that are easy to confuse and that the skills should not paraphrase freely:

- **meme key** — the first argument to `add_meme`, the key in the upstream `manager._memes` registry (e.g. `last_order_think`). Not the directory name.
- **keywords** — `Meme` metadata used as trigger words by downstream adapters. Lowercase snake_case list, distinct from the key.
- **`TEXT_AREA`** — the `draw_text` rectangle inside the speech bubble of a meme's material image.
- **blocker** — `tools/render_meme.py --list` exiting non-zero. Distinct from a warning.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `GLOSSARY.md` (or `AGENTS.md` in the interim). Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal: either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders), but worth reopening because…_
