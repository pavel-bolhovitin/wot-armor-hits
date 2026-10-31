# Rules for Claude

## Logging

- Keep logs minimal: only critical places. The mod logs one line when it starts and then only failures: warnings
  and errors with their tracebacks (`docs/architecture.md`, Logging).
- No info lines about the normal flow: calls, events, states, values.
- Diagnostic logs only when the user asks for them, for the time of the check; remove them when the check is done.
