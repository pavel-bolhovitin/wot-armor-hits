---
paths:
  - "docs/release-notes/**"
---

# Release notes

- One file a release: `docs/release-notes/<version>.txt`. Only what is new since the previous release; nothing repeated from earlier notes.
- The WGMods page shows the text as one paragraph: line breaks become spaces, Markdown is not rendered. So the file is one line of plain text that reads well as it is: no title (the page shows the version itself), no `#`, `-`, `**`, backticks or links.
- Only what a player notices in the game: new features, changed UI or behavior, fixes. No logging, refactors, API use or other internals.
- Changes go in sections by the type of change, each section once, in this order: `✨ New:`, `🔄 Changed:`, `🐞 Fixed:` (the emoji is part of the label); a section with no items is left out. A section is one sentence: the label, then its items joined with `; `, ending with a full stop. With two or more items, each starts with its number: `1) `, `2) `, counted again in each section; a single item has no number. Items start in lowercase unless the first word is a UI name, and have no `;` inside. The section comes from the context, not from what the change touches: `Fixed` when something worked wrong (a bug, visual too), `Changed` when something worked as meant and now works or looks otherwise.
- One item a change: never the same change twice, under two sections or in other words.
- Items short, in English.
