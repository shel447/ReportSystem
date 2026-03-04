# REPORT SYSTEM KNOWLEDGE BASE

**Generated:** 2026-03-04
**Commit:** Not available (working directory)
**Branch:** master

## OVERVIEW
Intelligent Report System: FastAPI/Python backend with single-page frontend, supporting automated report generation and scheduling.

## STRUCTURE
```
./
├── check_db_local.py    # Database inspection utility
├── migrate_db.py        # Migration utility for feedbacks table 
├── migrate_submitter.py # Migration utility for submitter column
├── design/              # Design documentation
├── src/
│   ├── backend/         # FastAPI application
│   └── frontend/        # Single-page app (index.html)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Main entry point | src/backend/main.py | FastAPI bootstrapping, API routers |
| Database models | src/backend/models.py | SQLAlchemy definitions, relationships |
| API Routes | src/backend/routers/ | Individual route modules by feature |
| Frontend | src/frontend/index.html | Heavy SPA with embedded CSS/JS |
| Configuration | src/backend/requirements.txt | Python deps, no env or config files |
| Design docs | design/ | Architecture specs and business reqs |

## CONVENTIONS
- No tests - missing crucial test infrastructure
- Hardcoded db path without proper config
- No .env or config files for environment settings
- Root-level migration scripts (not in a /scripts folder)
- Single-file frontend with all CSS/JS embedded

## ANTI-PATTERNS (THIS PROJECT)
- Database file committed to git (should be in .gitignore)
- No separation of concerns between frontend/backend directories
- No CORS middleware despite API-Frontend integration
- Synchronous DB operations despite using FastAPI (async framework)
- Missing standard Python project files (pyproject.toml, testing framework)

## UNIQUE STYLES
- 1100+ line single-page HTML app
- llm_mock.py for development/testing of LLM features
- API endpoints directly exposed without API versioning

## COMMANDS
```bash
# Start application
cd src/backend && python main.py

# Alternative start (requires uvicorn installed)
uvicorn src.backend.main:app --reload

# Install dependencies
pip install -r src/backend/requirements.txt
```

## NOTES
- SQLite database in version control - move to .env/config location
- Frontend served from backend directory via FastAPI StaticFiles
- Missing proper error handling throughout codebase