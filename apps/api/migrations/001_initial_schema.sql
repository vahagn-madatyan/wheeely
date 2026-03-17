-- 001_initial_schema.sql
-- Wheeely: Initial database schema for Supabase-managed Postgres
-- Apply via Supabase Dashboard SQL Editor or `supabase db push`
--
-- Depends on: auth.users table and auth.uid() function (provided by Supabase)

-- =============================================================================
-- 1. TABLES
-- =============================================================================

-- profiles: one row per authenticated user, auto-created by trigger
create table if not exists public.profiles (
    id         uuid references auth.users not null primary key,
    email      text,
    tier       text default 'free' not null,
    created_at timestamptz default now() not null,
    updated_at timestamptz default now() not null
);

-- api_keys: encrypted API keys for broker/data providers
create table if not exists public.api_keys (
    id              bigint generated always as identity primary key,
    user_id         uuid references public.profiles(id) on delete cascade not null,
    provider        text not null,          -- 'alpaca' or 'finnhub'
    key_name        text not null,          -- e.g. 'api_key', 'secret_key', 'finnhub_key'
    encrypted_value bytea not null,
    encrypted_dek   bytea not null,
    nonce           bytea not null,
    dek_nonce       bytea not null,
    is_paper        boolean default true,
    created_at      timestamptz default now() not null,
    updated_at      timestamptz default now() not null,
    unique(user_id, provider, key_name)
);

-- screening_runs: each user-initiated screening session
create table if not exists public.screening_runs (
    id           uuid primary key default gen_random_uuid(),
    user_id      uuid references public.profiles(id) on delete cascade not null,
    run_type     text not null,             -- e.g. 'put_screen', 'call_screen', 'full_pipeline'
    status       text not null default 'pending',  -- 'pending', 'running', 'completed', 'failed'
    params       jsonb,
    error        text,
    created_at   timestamptz default now() not null,
    completed_at timestamptz
);

-- screening_results: individual results within a screening run
create table if not exists public.screening_results (
    id     bigint generated always as identity primary key,
    run_id uuid references public.screening_runs(id) on delete cascade not null,
    data   jsonb not null
);

-- =============================================================================
-- 2. ROW LEVEL SECURITY
-- =============================================================================

alter table public.profiles enable row level security;
alter table public.api_keys enable row level security;
alter table public.screening_runs enable row level security;
alter table public.screening_results enable row level security;

-- profiles: users can read and update only their own profile
create policy "profiles_select_own" on public.profiles
    for select to authenticated
    using (id = (select auth.uid()));

create policy "profiles_update_own" on public.profiles
    for update to authenticated
    using (id = (select auth.uid()));

-- api_keys: full CRUD scoped to own keys
create policy "api_keys_select_own" on public.api_keys
    for select to authenticated
    using (user_id = (select auth.uid()));

create policy "api_keys_insert_own" on public.api_keys
    for insert to authenticated
    with check (user_id = (select auth.uid()));

create policy "api_keys_update_own" on public.api_keys
    for update to authenticated
    using (user_id = (select auth.uid()));

create policy "api_keys_delete_own" on public.api_keys
    for delete to authenticated
    using (user_id = (select auth.uid()));

-- screening_runs: full CRUD scoped to own runs
create policy "screening_runs_select_own" on public.screening_runs
    for select to authenticated
    using (user_id = (select auth.uid()));

create policy "screening_runs_insert_own" on public.screening_runs
    for insert to authenticated
    with check (user_id = (select auth.uid()));

create policy "screening_runs_update_own" on public.screening_runs
    for update to authenticated
    using (user_id = (select auth.uid()));

create policy "screening_runs_delete_own" on public.screening_runs
    for delete to authenticated
    using (user_id = (select auth.uid()));

-- screening_results: read-only, scoped through parent run ownership
create policy "screening_results_select_own" on public.screening_results
    for select to authenticated
    using (run_id in (select id from public.screening_runs where user_id = (select auth.uid())));

-- =============================================================================
-- 3. PROFILE AUTO-CREATION TRIGGER
-- =============================================================================

-- Automatically create a profile row when a new user signs up via Supabase Auth.
-- security definer: runs as the function owner (bypasses RLS for the insert).
-- set search_path = '': prevents search_path injection attacks.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    insert into public.profiles (id, email)
    values (new.id, new.raw_user_meta_data ->> 'email');
    return new;
end;
$$;

-- Fire after each new user is inserted into auth.users
create trigger on_auth_user_created
    after insert on auth.users
    for each row
    execute function public.handle_new_user();
