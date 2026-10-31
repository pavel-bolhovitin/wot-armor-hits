---
paths:
  - "docs/release-notes/**"
---

# Release notes

- One file a release: `docs/release-notes/<version>.md`, headed `## Armor Hits <version>`.
- Only what a player notices in the game: new features, changed UI or behavior, fixes. No logging, refactors, API use or other internals.
- Each item starts with a label by the type of change, in this order: `New:`, `Changed:`, `Fixed:`. The label comes from the context, not from what the change touches: `Fixed:` when something worked wrong (a bug, visual too), `Changed:` when something worked as meant and now works or looks otherwise.
- One item a change: never the same change twice, under two labels or in other words.
- One line an item, short, in English; no hard line breaks.
