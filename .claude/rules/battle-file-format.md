---
paths:
  - "src/**/*.py"
---

# Battle file format

- The mod's code works only with the latest format. No backward compatibility in it: no version checks, no branches, fields or fallbacks for old files.
- A file of an old format is converted when it is read, on the fly and only in memory (`data/migrations/`). Never write over an old file: it stays on disk as it is, also when its battle is saved again.
- A converter is a separate file, one step from one format to the next: `data/migrations/v<N>_to_v<N+1>.py`, plain JSON data in, plain JSON data out, registered in `data/migrations/__init__.py`.
- A converter is not tied to the mod's code: it imports nothing of the mod and keeps its own copy of the names and rules it needs, so later changes of the code never touch it. Client modules are fine when the data needs them.
- What cannot be converted gets the default value: leave the hole for the field's default, never fail on missing or broken data.
- `FORMAT_VERSION` grows only once a release: a format not released yet changes in place, without a new version; when it already has a converter, change that converter too.
- A format change after a release: raise `FORMAT_VERSION`, add its converter, and change the code to the new format only.
