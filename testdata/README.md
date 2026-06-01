# Shared Test Data

This directory contains stable, committed inputs shared by backend and exporter tests.

- `report-templates/`: formal template fixtures
- `report-dsl/`: flow and paged Report DSL fixtures
- `external-responses/`: deterministic custom-content responses
- `parameter-options/`: deterministic option responses
- `mock-server/`: deterministic responses for the optional development mock service
- `report-templates/`: includes compact fixtures and complex development-only templates

Generated databases, logs and documents belong in `.test/`, never in `testdata/` or `.runtime/`.
