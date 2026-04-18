---
name: config-first-feature
description: "Use when adding or changing any runtime parameter, recognition rule, or camera behavior in this project. Ensures React UI editability, DB persistence, backend live usage, and tests for unknown face behavior."
---

# Config First Feature

Use this workflow for any feature that changes behavior of detection, recognition, camera usage, or thresholds.

## Inputs to collect

- New or updated parameter name.
- Parameter type and allowed range.
- Default value to store in DB.
- Affected backend modules and UI screens.

## Required implementation flow

1. Add or update configuration schema in local DB layer.
2. Expose read/write endpoints in backend API.
3. Wire parameter to React configuration UI.
4. Ensure backend consumes persisted value at runtime.
5. Validate behavior for unknown face status (`inconnu`) when recognition path is affected.
6. Add or update tests:
   - Unit tests for validation/matching logic.
   - Integration tests for configuration and faces endpoints.

## Guardrails

- Do not hardcode runtime values in business logic.
- Do not exceed 300 lines in modified Python files.
- Keep modules separated by responsibility (camera, recognition, persistence, API, UI).

## Definition of done

- Parameter is editable in UI.
- Parameter is persisted in local DB.
- Backend uses persisted value.
- Unknown face behavior is covered when recognition was modified.
- Modified Python files remain under 300 lines.
