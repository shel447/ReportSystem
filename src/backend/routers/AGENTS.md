# ROUTER MODULES KNOWLEDGE BASE

**Generated:** 2026-03-04
**Commit:** Not available (working directory)
**Branch:** master

## OVERVIEW
API router modules with FastAPI APIRouter pattern, each responsible for specific domain features.

## STRUCTURE
```
./src/backend/routers/
├── __init__.py        # Router package initialization
├── templates.py       # Template management API
├── instances.py       # Report instance lifecycle API  
├── documents.py       # Document management (upload/remove) API
├── tasks.py           # Task automation API
├── chat.py            # Chat interface and history API
├── design.py          # Design pattern and workflow API
└── feedback.py        # User feedback collection API
```

## WHERE TO LOOK
| Router | Module | Primary Purpose |
|--------|--------|-----------------|
| templates | templates.py | CRUD ops on report templates |
| instances | instances.py | Report generation instances |
| documents | documents.py | File upload, storage, retrieval |
| tasks | tasks.py | Automated task scheduling and status |
| chat | chat.py | Chat interface with history persistence |
| design | design.py | Architecture and workflow patterns |
| feedback | feedback.py | User feedback collection/processing |

## CONVENTIONS
- Each router uses the same APIRouter prefix pattern
- Database sessions acquired via try/finally blocks
- Pydantic schemas defined inline with route handlers
- UUID primary keys generation consistent across all routers
- Response validation with Pydantic models

## ANTI-PATTERNS (THIS PROJECT)
- Database business logic mixed with API logic
- Missing input validation beyond Pydantic schema validation
- Session management repeated in each route function (not using Depends)
- No unified error handling pattern across routers
- Duplicate utility functions in multiple routers

## UNIQUE STYLES
- All routers follow identical structure: schemas -> APIRouter -> routes -> dependencies
- Heavy use of FastAPI Query parameters for optional fields
- SQLAlchemy session management wrapped in context managers
- Return dict responses without consistent wrapper objects

## COMMANDS
```bash
# No development commands specific to routers
# Routers are used by main.py when starting the server
```

## NOTES
- Each router defines its own Pydantic models inline
- Common database patterns are repeated across all modules
- No base class or mixin for common operations
- API routes use consistent naming patterns across modules