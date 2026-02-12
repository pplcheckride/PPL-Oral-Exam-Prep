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
-- Analytics events (immutable raw data)
-- =========================
create table if not exists public.analytics_events (
  id bigserial primary key,
  event_id uuid not null unique,
  event_name text not null,
  occurred_at timestamptz not null,
  received_at timestamptz not null default now(),
  anon_id text not null,
  session_id text not null,
  license_key_hash text references public.licenses(license_key_hash) on delete set null,
  user_tier text not null check (user_tier in ('free', 'paid')),
  app_version text,
  page_name text,
  mode_name text,
  scenario_id text,
  properties jsonb not null default '{}'::jsonb,
  context jsonb not null default '{}'::jsonb
);

create index if not exists idx_analytics_occurred_at on public.analytics_events(occurred_at);
create index if not exists idx_analytics_event_name_occurred on public.analytics_events(event_name, occurred_at);
create index if not exists idx_analytics_user_tier_event_day on public.analytics_events(user_tier, event_name, occurred_at);
create index if not exists idx_analytics_license_occurred on public.analytics_events(license_key_hash, occurred_at);
create index if not exists idx_analytics_scenario_day on public.analytics_events(scenario_id, occurred_at);
create index if not exists idx_analytics_properties_gin on public.analytics_events using gin (properties);
create index if not exists idx_analytics_context_gin on public.analytics_events using gin (context);

-- =========================
-- Analytics KPI Views
-- =========================
create or replace view public.analytics_funnel_daily as
with base as (
  select
    date_trunc('day', occurred_at)::date as event_date,
    user_tier,
    coalesce(license_key_hash, anon_id) as principal_id,
    event_name
  from public.analytics_events
  where event_name in (
    'landing_viewed',
    'start_studying_clicked',
    'upgrade_modal_viewed',
    'upgrade_cta_clicked',
    'license_exchange_success'
  )
)
select
  event_date,
  user_tier,
  count(distinct case when event_name = 'landing_viewed' then principal_id end) as landing_users,
  count(distinct case when event_name = 'start_studying_clicked' then principal_id end) as started_users,
  count(distinct case when event_name = 'upgrade_modal_viewed' then principal_id end) as upgrade_modal_users,
  count(distinct case when event_name = 'upgrade_cta_clicked' then principal_id end) as upgrade_cta_users,
  count(distinct case when event_name = 'license_exchange_success' then principal_id end) as converted_users
from base
group by 1, 2;

create or replace view public.analytics_paid_engagement_daily as
with paid_events as (
  select
    date_trunc('day', occurred_at)::date as event_date,
    coalesce(license_key_hash, anon_id) as principal_id,
    session_id,
    event_name
  from public.analytics_events
  where user_tier = 'paid'
)
select
  event_date,
  count(distinct principal_id) as paid_dau,
  count(distinct session_id) as paid_sessions,
  count(*) as total_paid_events,
  count(*) filter (where event_name = 'scenario_viewed') as scenario_views,
  count(*) filter (where event_name = 'scenario_rated') as scenario_ratings,
  count(*) filter (where event_name = 'mock_started') as mock_starts,
  count(*) filter (where event_name = 'mock_completed') as mock_completions,
  case
    when count(*) filter (where event_name = 'mock_started') = 0 then null
    else round(
      (count(*) filter (where event_name = 'mock_completed'))::numeric
      / nullif(count(*) filter (where event_name = 'mock_started'), 0)::numeric,
      4
    )
  end as mock_completion_rate,
  count(*) filter (where event_name = 'reference_clicked') as reference_clicks
from paid_events
group by 1;

create or replace view public.analytics_paid_retention_d1_d7_d30 as
with paid_activity as (
  select
    coalesce(license_key_hash, anon_id) as principal_id,
    date_trunc('day', occurred_at)::date as activity_date
  from public.analytics_events
  where user_tier = 'paid'
  group by 1, 2
),
cohorts as (
  select
    principal_id,
    min(activity_date) as cohort_date
  from paid_activity
  group by 1
),
retention as (
  select
    c.cohort_date,
    c.principal_id,
    max(case when a.activity_date = c.cohort_date + 1 then 1 else 0 end) as retained_d1,
    max(case when a.activity_date = c.cohort_date + 7 then 1 else 0 end) as retained_d7,
    max(case when a.activity_date = c.cohort_date + 30 then 1 else 0 end) as retained_d30
  from cohorts c
  left join paid_activity a
    on a.principal_id = c.principal_id
   and a.activity_date in (c.cohort_date + 1, c.cohort_date + 7, c.cohort_date + 30)
  group by 1, 2
)
select
  cohort_date,
  count(*) as cohort_size,
  sum(retained_d1) as retained_users_d1,
  sum(retained_d7) as retained_users_d7,
  sum(retained_d30) as retained_users_d30,
  round(sum(retained_d1)::numeric / nullif(count(*), 0)::numeric, 4) as retention_rate_d1,
  round(sum(retained_d7)::numeric / nullif(count(*), 0)::numeric, 4) as retention_rate_d7,
  round(sum(retained_d30)::numeric / nullif(count(*), 0)::numeric, 4) as retention_rate_d30
from retention
group by 1
order by 1 desc;

create or replace view public.analytics_scenario_outcomes_daily as
with rated as (
  select
    ae.id,
    date_trunc('day', ae.occurred_at)::date as event_date,
    ae.occurred_at,
    coalesce(ae.license_key_hash, ae.anon_id) as principal_id,
    ae.user_tier,
    coalesce(nullif(ae.mode_name, ''), 'unknown') as mode_name,
    ae.scenario_id,
    lower(coalesce(ae.properties ->> 'rating', '')) as rating
  from public.analytics_events ae
  where ae.event_name = 'scenario_rated'
    and ae.scenario_id is not null
    and lower(coalesce(ae.properties ->> 'rating', '')) in ('correct', 'unsure', 'wrong')
),
all_attempts as (
  select
    event_date,
    user_tier,
    mode_name,
    scenario_id,
    count(*) as all_attempts_count,
    count(*) filter (where rating = 'wrong') as all_wrong_count
  from rated
  group by 1, 2, 3, 4
),
ranked as (
  select
    r.*,
    row_number() over (
      partition by r.principal_id, r.scenario_id
      order by r.occurred_at asc, r.id asc
    ) as rn
  from rated r
),
first_attempts as (
  select
    event_date,
    user_tier,
    mode_name,
    scenario_id,
    count(*) as first_attempts_count,
    count(*) filter (where rating = 'wrong') as first_wrong_count
  from ranked
  where rn = 1
  group by 1, 2, 3, 4
)
select
  coalesce(a.event_date, f.event_date) as event_date,
  coalesce(a.user_tier, f.user_tier) as user_tier,
  coalesce(a.mode_name, f.mode_name) as mode_name,
  coalesce(a.scenario_id, f.scenario_id) as scenario_id,
  coalesce(a.all_attempts_count, 0) as all_attempts_count,
  coalesce(a.all_wrong_count, 0) as all_wrong_count,
  round(
    coalesce(a.all_wrong_count, 0)::numeric / nullif(coalesce(a.all_attempts_count, 0), 0)::numeric,
    4
  ) as all_attempt_wrong_rate,
  coalesce(f.first_attempts_count, 0) as first_attempts_count,
  coalesce(f.first_wrong_count, 0) as first_wrong_count,
  round(
    coalesce(f.first_wrong_count, 0)::numeric / nullif(coalesce(f.first_attempts_count, 0), 0)::numeric,
    4
  ) as first_attempt_wrong_rate,
  (coalesce(f.first_attempts_count, 0) >= 30) as meets_min_sample
from all_attempts a
full join first_attempts f
  on a.event_date = f.event_date
 and a.user_tier = f.user_tier
 and a.mode_name = f.mode_name
 and a.scenario_id = f.scenario_id;

-- =========================
-- RLS (deny-by-default)
-- =========================
alter table public.licenses enable row level security;
alter table public.user_progress enable row level security;
alter table public.mock_checkride_results enable row level security;
alter table public.user_sessions enable row level security;
alter table public.analytics_events enable row level security;

-- Do not create permissive policies for anon/authenticated.
-- Edge Functions (service role) bypass RLS.

-- =========================
-- Allowlist insert helper
-- =========================
-- Insert a license hash (sha256 hex of the raw license key):
-- insert into public.licenses (license_key_hash, status) values ('<sha256-hex>', 'active');

-- =========================
-- Analytics data deletion playbook (admin-only SQL)
-- =========================
-- Delete analytics by paid user (hashed license key):
-- delete from public.analytics_events where license_key_hash = '<license_key_hash>';
--
-- Delete analytics by anonymous browser profile:
-- delete from public.analytics_events where anon_id = '<anon_id>';
--
-- Optional: inspect rows before deleting:
-- select count(*) from public.analytics_events where license_key_hash = '<license_key_hash>';
-- select count(*) from public.analytics_events where anon_id = '<anon_id>';
