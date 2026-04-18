---
applyTo: "**/*.{py,pyi,tsx,ts,jsx,js,json,md}"
description: "Use when editing Python backend or React frontend in this face-recognition project: enforce configurable runtime settings, unknown-face behavior, and Python file size limits."
---

# Project Conventions

Source of truth: [AGENTS.md](../../AGENTS.md).

## Always enforce

- Never introduce hardcoded operational values in business logic.
- Any operational value (thresholds, intervals, camera index, timeout, paths) must be editable from the React UI.
- Backend must read and use persisted configuration from local database.
- If a face is not recognized, return status `inconnu`.
- Keep periodic webcam detection interval configurable. Suggested startup value is 3 seconds, but stored and editable through configuration.
- Keep Python files under 300 lines after each change.

## Architecture guardrails

- React side: small reusable components and centralized configuration state.
- Python side: split responsibilities into camera, recognition, persistence, and API modules.
- Prefer extracting services/utilities over growing monolithic files.

## Completion checks for changes

- UI can edit the parameter.
- Backend persists and reads that parameter from local DB.
- Runtime behavior reflects persisted value without restart when possible.
- If recognition behavior was touched, include test coverage for unknown face status.
