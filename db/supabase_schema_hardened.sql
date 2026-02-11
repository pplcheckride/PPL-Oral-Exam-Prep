-- Hardened schema for PPL Oral Exam Prep (Supabase/Postgres)
-- License-key model (no Supabase Auth). All reads/writes should go through Edge Functions
-- using the service role key. Keep RLS enabled and DO NOT add permissive anon policies.

create extension if not exists pgcrypto;

-- =========================
-- Licenses (allowlist v1)
-- =========================
create table if not exists public.licenses (
  license_key_hash text primary key,
  status text not null default 'active' check (status in ('active', 'revoked')),
  created_at timestamptz not null default now(),
  notes text,
  -- reserved for future Gumroad fields
  gumroad_purchase_id text,
  gumroad_email text
);

-- =========================
-- Per-question progress
-- =========================
create table if not exists public.user_progress (
  id uuid primary key default gen_random_uuid(),
  license_key_hash text not null references public.licenses(license_key_hash) on delete cascade,
  question_id text not null,
  rating text not null check (rating in ('correct', 'unsure', 'wrong')),
  attempts int not null default 0,
  updated_at timestamptz not null default now(),
  unique (license_key_hash, question_id)
);

create index if not exists idx_user_progress_license on public.user_progress(license_key_hash);
create index if not exists idx_user_progress_question on public.user_progress(question_id);
create index if not exists idx_user_progress_rating on public.user_progress(rating);

-- =========================
-- Mock checkride results
-- =========================
create table if not exists public.mock_checkride_results (
  id uuid primary key default gen_random_uuid(),
  license_key_hash text not null references public.licenses(license_key_hash) on delete cascade,
  score int not null,
  total_questions int not null,
  passed boolean not null,
  time_spent_seconds int,
  questions_attempted jsonb,
  completed_at timestamptz not null default now()
);

create index if not exists idx_mock_results_license on public.mock_checkride_results(license_key_hash);
create index if not exists idx_mock_results_completed on public.mock_checkride_results(completed_at);

-- =========================
-- Optional sessions table
-- =========================
create table if not exists public.user_sessions (
  license_key_hash text primary key references public.licenses(license_key_hash) on delete cascade,
  last_sync_at timestamptz not null default now(),
  total_questions_attempted int not null default 0,
  total_study_time_seconds int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- updated_at trigger helper
create or replace function public.update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists update_user_sessions_updated_at on public.user_sessions;
create trigger update_user_sessions_updated_at
before update on public.user_sessions
for each row
execute function public.update_updated_at_column();

-- =========================
-- RLS (deny-by-default)
-- =========================
alter table public.licenses enable row level security;
alter table public.user_progress enable row level security;
alter table public.mock_checkride_results enable row level security;
alter table public.user_sessions enable row level security;

-- Do not create permissive policies for anon/authenticated.
-- Edge Functions (service role) bypass RLS.

-- =========================
-- Allowlist insert helper
-- =========================
-- Insert a license hash (sha256 hex of the raw license key):
-- insert into public.licenses (license_key_hash, status) values ('<sha256-hex>', 'active');

