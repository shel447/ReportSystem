# Shared Test Data

This directory contains stable, committed inputs shared by backend and exporter tests.

- `report-templates/`: formal template fixtures
- `report-dsl/`: flow and paged Report DSL fixtures
- `external-responses/`: deterministic custom-content responses
- `parameter-options/`: deterministic option responses

Generated databases, logs and documents belong in `.test/`, never in `testdata/` or `.runtime/`.
