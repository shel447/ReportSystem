# FRONTEND KNOWLEDGE BASE

**Generated:** 2026-03-04
**Commit:** Not available (working directory)
**Branch:** master

## OVERVIEW
Single-page application frontend with embedded CSS/JavaScript served via FastAPI static files.

## STRUCTURE
```
./src/frontend/
└── index.html         # Single-page application (1100+ lines)
```

## WHERE TO LOOK
| Component | File | Functionality |
|-----------|------|---------------|
| Main Interface | index.html | Complete SPA with all CSS/JS embedded |

## CONVENTIONS
- All CSS embedded within `<style>` tags
- All JavaScript embedded within `<script>` tags
- Direct API calls to `/api/*` endpoints
- Bootstrap CSS framework utilization
- Client-side DOM manipulation for dynamic content
- Local storage usage for client preferences/state management

## ANTI-PATTERNS (THIS PROJECT)
- Monolithic single-file application (1100+ lines) with mixed concerns
- No component separation or modularity
- No build/compilation step for assets
- No client-side routing
- No framework abstraction (plain JavaScript)
- Mix of presentation and business logic

## UNIQUE STYLES
- Entire application in single HTML file
- Heavy reliance on DOM manipulation instead of framework
- Self-contained without external build dependencies
- Direct integration with backend via `/api/*` routes
- Consistent layout maintained across all pages via embedded CSS

## COMMANDS
```bash
# No build commands - runs directly in browser
# Served by backend via FastAPI StaticFiles middleware
```

## NOTES
- Works directly by requesting from the root `/` endpoint
- Updates require backend restart to refresh cached files
- Tightly coupled with backend API contract
- Performance may degrade with complexity due to single file