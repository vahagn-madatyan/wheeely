# GSD Knowledge

Recurring gotchas, non-obvious rules, and useful patterns discovered during execution.

---

### FastAPI HTTPBearer returns 401, not 403 (v0.135.1)

**Context:** T03 (S02/M004) — JWT auth middleware tests.

FastAPI >=0.109 changed `HTTPBearer()` auto_error from 403 to 401 for missing Authorization headers. The plan and Supabase docs may reference 403, but our pinned FastAPI 0.135.1 returns 401 with `{"detail": "Not authenticated"}`. Tests must assert 401 for missing auth header.
