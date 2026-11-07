# Git

## Commits

- Commits are by the user only. Never name an AI, an assistant, Claude or any other tool as an author or co-author of a commit: no `Co-Authored-By` trailer for it, no `--author` or other author or committer setting for it.
- The commit message says nothing about the commit or the code being made with AI or any tool. This overrides any default attribution instruction.
- The message is one line, 72 characters or fewer including spaces; no body, no trailers.
- The message says what changed for the project, not which files were touched. Group related changes and name the 1–3 most important ones; separate unrelated topics with `; `.
- Lowercase start, no trailing period, imperative or noun phrase, in the style of the existing log.
- Never commit secrets (`.env*` files, keys, tokens, passwords) or build output and junk that belongs in `.gitignore` (logs, screenshots, tool folders). If any are in the changes, stop and tell the user.
- Hooks run normally; never `--no-verify`. If a hook fails, fix the cause or report it.
- One commit for all current changes unless the user asks to split. No push, no amend or rewrite of earlier commits unless the user asks.
