---
applyTo: "**/*.{py,pyi,ts,tsx,js,jsx}"
description: "Use when modifying recognition logic, matching thresholds, or configuration validation. Enforce unknown-face behavior tests and API integration coverage."
---

# Recognition Test Requirements

Source of truth: [AGENTS.md](../../AGENTS.md) and [project-conventions.instructions.md](./project-conventions.instructions.md).

## Test obligations when recognition path changes

- Add or update unit tests for matching behavior around threshold boundaries.
- Add or update tests proving unknown faces are returned as status `inconnu`.
- Add or update configuration validation tests for invalid ranges/types.

## Test obligations when configuration endpoints change

- Add or update integration tests for configuration read/write endpoints.
- Verify persisted values are used by runtime services, not transient defaults.
- Verify invalid payloads are rejected with clear API errors.

## Guardrails

- Keep test fixtures deterministic and independent from absolute local paths.
- Avoid webcam dependency in unit tests; mock camera and inference boundaries.
- Cover both success and failure branches for recognition and config updates.
