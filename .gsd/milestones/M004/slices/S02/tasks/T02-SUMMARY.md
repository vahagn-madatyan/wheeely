---
id: T02
parent: S02
milestone: M004
provides:
  - SQL migration with 4 tables (profiles, api_keys, screening_runs, screening_results), RLS policies, profile auto-creation trigger
  - Async database connection pool (get_db_pool, get_db, close_db_pool)
key_files:
  - apps/api/migrations/001_initial_schema.sql
  - apps/api/services/database.py
  - apps/api/requirements.txt
key_decisions:
  - RLS policies use (select auth.uid()) subselect pattern per Supabase best practices to avoid per-row function call overhead
  - Profile trigger extracts email from raw_user_meta_data->>'email' (standard Supabase signup metadata field)
  - Connection pool sized min_size=2, max_size=10 for free-tier Supabase (which allows ~60 direct connections)
patterns_established:
  - Migration files live in apps/api/migrations/ numbered sequentially (001_, 002_, etc.)
  - Module-level pool cache pattern with get_db_pool() / close_db_pool() lifecycle
  - FastAPI dependency via get_db() async generator that yields a connection from the pool
observability_surfaces:
  - ValueError("DATABASE_URL environment variable is not set") at startup if env var missing
  - Pool exhaustion surfaces as asyncpg connection timeout in downstream endpoint logs
  - Schema verified via \d <table_name> in Supabase SQL editor
duration: 8m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: Write database schema migration and async connection pool

**Created 4-table SQL migration with RLS and profile trigger, plus asyncpg connection pool module.**

## What Happened

Created `apps/api/migrations/001_initial_schema.sql` with all 4 tables (`profiles`, `api_keys`, `screening_runs`, `screening_results`), complete RLS policies using `(select auth.uid())` subselect pattern, and a `handle_new_user()` trigger function with `security definer` and `set search_path = ''`. Added `asyncpg>=0.29.0` to requirements and implemented `apps/api/services/database.py` with module-level pool cache, `get_db_pool()`, `get_db()` FastAPI dependency, and `close_db_pool()` shutdown helper.

## Verification

- `python -c "import asyncpg; print('asyncpg OK')"` — ✅ asyncpg 0.31.0 imports
- `python -c "from apps.api.services.database import get_db_pool, get_db, close_db_pool; print('database module OK')"` — ✅ all 3 exports work
- `python -m pytest tests/ -q` — ✅ 425 CLI tests pass
- `python -m pytest apps/api/tests/ -q` — ✅ 42 API tests pass (31 S01 + 11 T01 encryption)
- `python -m pytest apps/api/tests/test_encryption.py -v` — ✅ 11 encryption tests pass (T01 unbroken)
- SQL file inspected: all 4 tables present, RLS enabled on all 4, 11 policies use `(select auth.uid())`, trigger uses `security definer set search_path = ''`, `unique(user_id, provider, key_name)` on api_keys

### Slice-level verification (partial — T02 is intermediate):
- ✅ `python -m pytest apps/api/tests/test_encryption.py -v` — 11 passed
- ⬜ `python -m pytest apps/api/tests/test_auth.py -v` — not yet created (T03)
- ⬜ `python -m pytest apps/api/tests/test_keys_endpoints.py -v` — not yet created (T04)
- ✅ `python -m pytest tests/ -q` — 425 passed
- ✅ `python -m pytest apps/api/tests/ -q` — 42 passed

## Diagnostics

- **database.py** has no runtime logging (intentional — it's infrastructure plumbing). Observability comes from downstream endpoints that use the pool.
- Missing `DATABASE_URL` raises `ValueError` with clear message at pool creation time.
- Pool is not created until first `get_db_pool()` call (lazy init), so import alone never fails.
- `close_db_pool()` is idempotent — safe to call even if pool was never created.

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `apps/api/migrations/001_initial_schema.sql` — Full schema migration: 4 tables, RLS policies, profile trigger
- `apps/api/services/database.py` — Async connection pool with get_db_pool(), get_db(), close_db_pool()
- `apps/api/requirements.txt` — Added `asyncpg>=0.29.0`
- `.gsd/milestones/M004/slices/S02/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
