# BACKEND KNOWLEDGE BASE

**Generated:** 2026-03-04
**Commit:** Not available (working directory)
**Branch:** master

## OVERVIEW
FastAPI/Python backend with SQLAlchemy database integration.

## STRUCTURE
```
./src/backend/
├── main.py           # FastAPI app initialization and routing
├── models.py         # SQLAlchemy database models
├── database.py       # Database connection and initialization
├── llm_mock.py       # Mock LLM implementation for development
├── requirements.txt  # Python dependencies (FastAPI, SQLAlchemy, etc.)
└── routers/          # API routes modules
```

## WHERE TO LOOK
| Component | File | Purpose |
|-----------|------|---------|
| Application | main.py | Server initialization, router mounting, startup events |
| Models | models.py | SQLAlchemy tables: ReportInstance, Document, etc. |
| Database | database.py | Connection pool, session factory, db init |
| API | routers/ | Feature-specific API endpoints (templates, instances, etc.) |
| LLM | llm_mock.py | Development/production interface for LLM integration |

## CONVENTIONS
- No authentication/authorization implemented in core routes
- UUID primary keys using gen_id() helper
- Manual transaction management in routes
- Synchronous operations with SQLite
- Embedded Pydantic schemas in router files

## ANTI-PATTERNS (THIS PROJECT)
- Database operations without async/await despite using FastAPI
- No validation of foreign key constraints in some relations
- Direct database commits without proper error handling rollback
- Missing dependency injection for database sessions in some places
- Hardcoded database path without configuration management
- Mixed concerns: some business logic in route handlers

## UNIQUE STYLES
- Centralized UUID generator (gen_id()) for all entities
- Custom timestamp format for API responses
- Self-contained router modules with inline schemas
- Database session cleanup with try-finally blocks

## COMMANDS
```bash
# Install dependencies
pip install -r requirements.txt

# Run the backend server
python main.py

# Run development server with reloading
uvicorn main:app --reload

# Check database locally
python ../../check_db_local.py
```

## NOTES
- Uses SQLite as default database, not suitable for production
- All routers share the same database session pattern
- Missing API error response standardization
- Development vs. production LLM handling in llm_mock.py