---
estimated_steps: 4
estimated_files: 3
---

# T02: Write database schema migration and async connection pool

**Slice:** S02 — Supabase auth + database + encrypted key storage
**Milestone:** M004

## Description

Create the SQL migration file that defines all 4 tables (`profiles`, `api_keys`, `screening_runs`, `screening_results`) with Row Level Security policies and the profile auto-creation trigger. Also implement the async database connection pool that key management endpoints will use. The migration file is the contract all downstream slices depend on — S03 needs `profiles`, S04 needs `api_keys`, S05/S06 need `screening_runs`/`screening_results`.

The migration targets Supabase-managed Postgres, which means: `auth.users` table exists, `auth.uid()` function exists, and RLS policies should use `to authenticated` role. The SQL file is version-controlled but applied manually via Supabase Dashboard SQL editor or `supabase db push`.

## Steps

1. **Create `apps/api/migrations/` directory and `001_initial_schema.sql`** — Write the full migration with:
   - `profiles` table: `id uuid references auth.users not null primary key`, `email text`, `tier text default 'free' not null`, `created_at timestamptz default now() not null`, `updated_at timestamptz default now() not null`
   - `api_keys` table: `id bigint generated always as identity primary key`, `user_id uuid references profiles(id) on delete cascade not null`, `provider text not null` ('alpaca' or 'finnhub'), `key_name text not null`, `encrypted_value bytea not null`, `encrypted_dek bytea not null`, `nonce bytea not null`, `dek_nonce bytea not null`, `is_paper boolean default true`, `created_at/updated_at timestamptz`, `unique(user_id, provider, key_name)`
   - `screening_runs` table: `id uuid primary key default gen_random_uuid()`, `user_id uuid references profiles(id) on delete cascade not null`, `run_type text not null`, `status text not null default 'pending'`, `params jsonb`, `error text`, `created_at timestamptz default now() not null`, `completed_at timestamptz`
   - `screening_results` table: `id bigint generated always as identity primary key`, `run_id uuid references screening_runs(id) on delete cascade not null`, `data jsonb not null`
   - Enable RLS on all 4 tables
   - RLS policies using `(select auth.uid())` subselect pattern (per Supabase best practices — subselect avoids per-row function call):
     - profiles: select + update where `id = (select auth.uid())`
     - api_keys: all operations where `user_id = (select auth.uid())`
     - screening_runs: all operations where `user_id = (select auth.uid())`
     - screening_results: select where `run_id in (select id from screening_runs where user_id = (select auth.uid()))`
   - Profile creation trigger: `handle_new_user()` function with `security definer` and `set search_path = ''`, fired `after insert on auth.users`
   - All policies use `to authenticated` role

2. **Add `asyncpg` to requirements** — Append `asyncpg>=0.29.0` to `apps/api/requirements.txt`. Install it.

3. **Create `apps/api/services/database.py`** — Implement:
   - `_pool: Optional[asyncpg.Pool] = None` module-level cache
   - `async def get_db_pool() -> asyncpg.Pool`: Creates pool from `DATABASE_URL` env var if not cached. Uses `asyncpg.create_pool(dsn=DATABASE_URL, min_size=2, max_size=10)`. Raises `ValueError` if `DATABASE_URL` not set.
   - `async def get_db() -> AsyncGenerator[asyncpg.Connection, None]`: FastAPI dependency that acquires a connection from the pool via `async with pool.acquire() as conn: yield conn`.
   - `async def close_db_pool()`: Closes the cached pool (for app shutdown).
   - Import and type hints: `from typing import AsyncGenerator, Optional` and `import asyncpg`.

4. **Verify** — Confirm asyncpg imports correctly and SQL file parses cleanly. Run existing tests to confirm nothing broke.

## Must-Haves

- [ ] `001_initial_schema.sql` contains all 4 tables with correct column types and constraints
- [ ] RLS enabled on all 4 tables with correct policies using `(select auth.uid())` subselect
- [ ] Profile creation trigger uses `security definer` and `set search_path = ''`
- [ ] `unique(user_id, provider, key_name)` constraint on `api_keys`
- [ ] `database.py` exports `get_db_pool()`, `get_db()`, and `close_db_pool()`
- [ ] `asyncpg>=0.29.0` added to `apps/api/requirements.txt`
- [ ] No changes to `pyproject.toml` or any CLI code

## Verification

- `cat apps/api/migrations/001_initial_schema.sql` — file exists with all 4 tables, RLS, trigger
- `source .venv/bin/activate && pip install asyncpg>=0.29.0 && python -c "import asyncpg; print('asyncpg OK')"` — import succeeds
- `source .venv/bin/activate && python -c "from apps.api.services.database import get_db_pool, get_db, close_db_pool; print('database module OK')"` — imports work
- `source .venv/bin/activate && python -m pytest tests/ -q` — 425 CLI tests still pass
- `source .venv/bin/activate && python -m pytest apps/api/tests/ -q` — 31 S01 tests still pass

## Observability Impact

- **Database pool health:** `get_db_pool()` raises `ValueError` with message `"DATABASE_URL environment variable is not set"` if env var missing — visible at app startup.
- **Connection pool metrics:** asyncpg pool created with `min_size=2, max_size=10` — pool exhaustion surfaces as connection timeout errors in downstream endpoint logs.
- **Schema contract:** Migration file is the source of truth for table structure. `\d profiles`, `\d api_keys`, `\d screening_runs`, `\d screening_results` in Supabase SQL editor confirms schema applied correctly.
- **RLS verification:** Queries without authenticated role return zero rows (not errors) — test by querying tables without `auth.uid()` context.
- **No runtime logging from this module** — database.py is infrastructure plumbing; observability comes from the endpoints that use it.

## Inputs

- `apps/api/requirements.txt` — file from T01 with `cryptography` already added
- `apps/api/services/__init__.py` — existing empty init

## Expected Output

- `apps/api/migrations/001_initial_schema.sql` — complete schema migration file
- `apps/api/services/database.py` — async connection pool with `get_db_pool()`, `get_db()`, `close_db_pool()`
- `apps/api/requirements.txt` — updated with `asyncpg>=0.29.0`
