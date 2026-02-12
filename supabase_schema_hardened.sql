-- Hardened schema for PPL Oral Exam Prep (Supabase/Postgres)
-- License-key model (no Supabase Auth). All reads/writes should go through Edge Functions
-- using the service role key. Keep RLS enabled and DO NOT add permissive anon policies.

create extension if not exists pgcrypto;

-- =========================
-- updated_at trigger helper
-- =========================
create or replace function public.update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- =========================
-- Users (canonical identity)
-- =========================
create table if not exists public.users (
  user_id uuid primary key default gen_random_uuid(),
  is_premium boolean not null default false,
  first_seen_free_at timestamptz,
  purchase_timestamp timestamptz,
  first_seen_paid_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_users_is_premium on public.users(is_premium);
create index if not exists idx_users_first_seen_free on public.users(first_seen_free_at);
create index if not exists idx_users_first_seen_paid on public.users(first_seen_paid_at);
create index if not exists idx_users_purchase_timestamp on public.users(purchase_timestamp);

drop trigger if exists update_users_updated_at on public.users;
create trigger update_users_updated_at
before update on public.users
for each row
execute function public.update_updated_at_column();

-- =========================
-- Identity mapping (anon + paid identities -> canonical user_id)
-- =========================
create table if not exists public.user_identity_map (
  id bigserial primary key,
  identity_type text not null check (identity_type in ('anon_id', 'license_key_hash')),
  identity_value text not null,
  user_id uuid not null references public.users(user_id) on delete cascade,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (identity_type, identity_value)
);

create index if not exists idx_user_identity_map_user on public.user_identity_map(user_id);
create index if not exists idx_user_identity_map_type_user on public.user_identity_map(identity_type, user_id);

drop trigger if exists update_user_identity_map_updated_at on public.user_identity_map;
create trigger update_user_identity_map_updated_at
before update on public.user_identity_map
for each row
execute function public.update_updated_at_column();

-- =========================
-- Licenses (allowlist v1)
-- =========================
create table if not exists public.licenses (
  license_key_hash text primary key,
  user_id uuid,
  status text not null default 'active' check (status in ('active', 'revoked')),
  created_at timestamptz not null default now(),
  notes text,
  -- reserved for future Gumroad fields
  gumroad_purchase_id text,
  gumroad_email text
);

alter table public.licenses add column if not exists user_id uuid;
create index if not exists idx_licenses_user_id on public.licenses(user_id);

-- Automatically allocate/ensure canonical user_id for admin-inserted licenses.
create or replace function public.ensure_license_user()
returns trigger as $$
begin
  if new.user_id is null then
    new.user_id := gen_random_uuid();
  end if;

  insert into public.users (user_id, is_premium)
  values (new.user_id, true)
  on conflict (user_id) do update
    set is_premium = true,
        updated_at = now();

  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_licenses_ensure_user on public.licenses;
create trigger trg_licenses_ensure_user
before insert or update on public.licenses
for each row
execute function public.ensure_license_user();

-- =========================
-- Per-question progress
-- =========================
create table if not exists public.user_progress (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  license_key_hash text not null references public.licenses(license_key_hash) on delete cascade,
  question_id text not null,
  rating text not null check (rating in ('correct', 'unsure', 'wrong')),
  attempts int not null default 0,
  updated_at timestamptz not null default now()
);

alter table public.user_progress add column if not exists user_id uuid;

create index if not exists idx_user_progress_user on public.user_progress(user_id);
create index if not exists idx_user_progress_license on public.user_progress(license_key_hash);
create index if not exists idx_user_progress_question on public.user_progress(question_id);
create index if not exists idx_user_progress_rating on public.user_progress(rating);

-- =========================
-- Mock checkride results
-- =========================
create table if not exists public.mock_checkride_results (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  license_key_hash text not null references public.licenses(license_key_hash) on delete cascade,
  score int not null,
  total_questions int not null,
  passed boolean not null,
  time_spent_seconds int,
  questions_attempted jsonb,
  completed_at timestamptz not null default now()
);

alter table public.mock_checkride_results add column if not exists user_id uuid;

create index if not exists idx_mock_results_license on public.mock_checkride_results(license_key_hash);
create index if not exists idx_mock_results_completed on public.mock_checkride_results(completed_at);
create index if not exists idx_mock_results_user_completed on public.mock_checkride_results(user_id, completed_at);

-- =========================
-- Optional sessions table
-- =========================
create table if not exists public.user_sessions (
  license_key_hash text primary key references public.licenses(license_key_hash) on delete cascade,
  user_id uuid,
  last_sync_at timestamptz not null default now(),
  total_questions_attempted int not null default 0,
  total_study_time_seconds int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.user_sessions add column if not exists user_id uuid;

create index if not exists idx_user_sessions_user_id on public.user_sessions(user_id);

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
  user_id uuid,
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

alter table public.analytics_events add column if not exists user_id uuid;

create index if not exists idx_analytics_occurred_at on public.analytics_events(occurred_at);
create index if not exists idx_analytics_event_name_occurred on public.analytics_events(event_name, occurred_at);
create index if not exists idx_analytics_user_tier_event_day on public.analytics_events(user_tier, event_name, occurred_at);
create index if not exists idx_analytics_user_occurred on public.analytics_events(user_id, occurred_at);
create index if not exists idx_analytics_license_occurred on public.analytics_events(license_key_hash, occurred_at);
create index if not exists idx_analytics_scenario_day on public.analytics_events(scenario_id, occurred_at);
create index if not exists idx_analytics_properties_gin on public.analytics_events using gin (properties);
create index if not exists idx_analytics_context_gin on public.analytics_events using gin (context);

-- =========================
-- Backfill canonical user_id coverage
-- =========================
with license_seeds as (
  select
    l.license_key_hash,
    coalesce(l.user_id, uim.user_id, gen_random_uuid()) as user_id
  from public.licenses l
  left join public.user_identity_map uim
    on uim.identity_type = 'license_key_hash'
   and uim.identity_value = l.license_key_hash
)
insert into public.users (user_id, is_premium)
select distinct user_id, true
from license_seeds
where user_id is not null
on conflict (user_id) do update
  set is_premium = true,
      updated_at = now();

with license_seeds as (
  select
    l.license_key_hash,
    coalesce(l.user_id, uim.user_id, gen_random_uuid()) as user_id
  from public.licenses l
  left join public.user_identity_map uim
    on uim.identity_type = 'license_key_hash'
   and uim.identity_value = l.license_key_hash
)
insert into public.user_identity_map (identity_type, identity_value, user_id)
select 'license_key_hash', license_key_hash, user_id
from license_seeds
where license_key_hash is not null
on conflict (identity_type, identity_value) do update
  set user_id = excluded.user_id,
      updated_at = now();

update public.licenses l
set user_id = uim.user_id
from public.user_identity_map uim
where uim.identity_type = 'license_key_hash'
  and uim.identity_value = l.license_key_hash
  and (l.user_id is null or l.user_id is distinct from uim.user_id);

with anon_seeds as (
  select distinct ae.anon_id
  from public.analytics_events ae
  where ae.anon_id is not null
),
resolved as (
  select
    s.anon_id as identity_value,
    coalesce(linked_license.user_id, existing_anon.user_id, gen_random_uuid()) as user_id
  from anon_seeds s
  left join public.user_identity_map existing_anon
    on existing_anon.identity_type = 'anon_id'
   and existing_anon.identity_value = s.anon_id
  left join lateral (
    select lm.user_id
    from public.analytics_events ae2
    join public.user_identity_map lm
      on lm.identity_type = 'license_key_hash'
     and lm.identity_value = ae2.license_key_hash
    where ae2.anon_id = s.anon_id
      and ae2.license_key_hash is not null
    order by ae2.occurred_at asc
    limit 1
  ) linked_license on true
)
insert into public.users (user_id)
select distinct user_id
from resolved
on conflict (user_id) do nothing;

with anon_seeds as (
  select distinct ae.anon_id
  from public.analytics_events ae
  where ae.anon_id is not null
),
resolved as (
  select
    s.anon_id as identity_value,
    coalesce(linked_license.user_id, existing_anon.user_id, gen_random_uuid()) as user_id
  from anon_seeds s
  left join public.user_identity_map existing_anon
    on existing_anon.identity_type = 'anon_id'
   and existing_anon.identity_value = s.anon_id
  left join lateral (
    select lm.user_id
    from public.analytics_events ae2
    join public.user_identity_map lm
      on lm.identity_type = 'license_key_hash'
     and lm.identity_value = ae2.license_key_hash
    where ae2.anon_id = s.anon_id
      and ae2.license_key_hash is not null
    order by ae2.occurred_at asc
    limit 1
  ) linked_license on true
)
insert into public.user_identity_map (identity_type, identity_value, user_id)
select 'anon_id', identity_value, user_id
from resolved
on conflict (identity_type, identity_value) do update
  set user_id = excluded.user_id,
      updated_at = now();

update public.user_progress up
set user_id = uim.user_id
from public.user_identity_map uim
where uim.identity_type = 'license_key_hash'
  and uim.identity_value = up.license_key_hash
  and (up.user_id is null or up.user_id is distinct from uim.user_id);

update public.mock_checkride_results mr
set user_id = uim.user_id
from public.user_identity_map uim
where uim.identity_type = 'license_key_hash'
  and uim.identity_value = mr.license_key_hash
  and (mr.user_id is null or mr.user_id is distinct from uim.user_id);

update public.user_sessions us
set user_id = uim.user_id
from public.user_identity_map uim
where uim.identity_type = 'license_key_hash'
  and uim.identity_value = us.license_key_hash
  and (us.user_id is null or us.user_id is distinct from uim.user_id);

with event_resolution as (
  select
    ae.id,
    coalesce(lm.user_id, am.user_id) as resolved_user_id
  from public.analytics_events ae
  left join public.user_identity_map lm
    on lm.identity_type = 'license_key_hash'
   and lm.identity_value = ae.license_key_hash
  left join public.user_identity_map am
    on am.identity_type = 'anon_id'
   and am.identity_value = ae.anon_id
)
update public.analytics_events ae
set user_id = er.resolved_user_id
from event_resolution er
where ae.id = er.id
  and er.resolved_user_id is not null
  and (ae.user_id is null or ae.user_id is distinct from er.resolved_user_id);

insert into public.users (user_id)
select distinct src.user_id
from (
  select user_id from public.licenses where user_id is not null
  union
  select user_id from public.user_progress where user_id is not null
  union
  select user_id from public.mock_checkride_results where user_id is not null
  union
  select user_id from public.user_sessions where user_id is not null
  union
  select user_id from public.analytics_events where user_id is not null
) src
on conflict (user_id) do nothing;

with free_seen as (
  select user_id, min(occurred_at) as first_seen_free_at
  from public.analytics_events
  where user_id is not null
    and user_tier = 'free'
  group by user_id
),
paid_seen as (
  select user_id, min(occurred_at) as first_seen_paid_at
  from public.analytics_events
  where user_id is not null
    and user_tier = 'paid'
  group by user_id
),
purchase_seen as (
  select user_id, min(occurred_at) as purchase_timestamp
  from public.analytics_events
  where user_id is not null
    and event_name = 'license_exchange_success'
  group by user_id
),
licensed as (
  select distinct user_id
  from public.user_identity_map
  where identity_type = 'license_key_hash'
)
update public.users u
set
  first_seen_free_at = case
    when u.first_seen_free_at is null then fs.first_seen_free_at
    when fs.first_seen_free_at is null then u.first_seen_free_at
    else least(u.first_seen_free_at, fs.first_seen_free_at)
  end,
  first_seen_paid_at = case
    when u.first_seen_paid_at is null then coalesce(ps.first_seen_paid_at, pu.purchase_timestamp)
    when coalesce(ps.first_seen_paid_at, pu.purchase_timestamp) is null then u.first_seen_paid_at
    else least(u.first_seen_paid_at, coalesce(ps.first_seen_paid_at, pu.purchase_timestamp))
  end,
  purchase_timestamp = case
    when u.purchase_timestamp is null then pu.purchase_timestamp
    when pu.purchase_timestamp is null then u.purchase_timestamp
    else least(u.purchase_timestamp, pu.purchase_timestamp)
  end,
  is_premium = (
    coalesce(u.is_premium, false)
    or lic.user_id is not null
    or ps.user_id is not null
    or pu.user_id is not null
  ),
  updated_at = now()
from free_seen fs
full join paid_seen ps on ps.user_id = fs.user_id
full join purchase_seen pu on pu.user_id = coalesce(fs.user_id, ps.user_id)
left join licensed lic on lic.user_id = coalesce(fs.user_id, ps.user_id, pu.user_id)
where u.user_id = coalesce(fs.user_id, ps.user_id, pu.user_id, lic.user_id);

-- =========================
-- Constraint hardening (post-backfill)
-- =========================

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'licenses_user_id_fkey'
      and conrelid = 'public.licenses'::regclass
  ) then
    alter table public.licenses
      add constraint licenses_user_id_fkey
      foreign key (user_id)
      references public.users(user_id)
      on delete cascade;
  end if;
end $$;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'user_progress_user_id_fkey'
      and conrelid = 'public.user_progress'::regclass
  ) then
    alter table public.user_progress
      add constraint user_progress_user_id_fkey
      foreign key (user_id)
      references public.users(user_id)
      on delete cascade;
  end if;
end $$;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'mock_checkride_results_user_id_fkey'
      and conrelid = 'public.mock_checkride_results'::regclass
  ) then
    alter table public.mock_checkride_results
      add constraint mock_checkride_results_user_id_fkey
      foreign key (user_id)
      references public.users(user_id)
      on delete cascade;
  end if;
end $$;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'user_sessions_user_id_fkey'
      and conrelid = 'public.user_sessions'::regclass
  ) then
    alter table public.user_sessions
      add constraint user_sessions_user_id_fkey
      foreign key (user_id)
      references public.users(user_id)
      on delete cascade;
  end if;
end $$;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'analytics_events_user_id_fkey'
      and conrelid = 'public.analytics_events'::regclass
  ) then
    alter table public.analytics_events
      add constraint analytics_events_user_id_fkey
      foreign key (user_id)
      references public.users(user_id)
      on delete cascade;
  end if;
end $$;

-- Remove duplicate progress rows before migrating uniqueness to (user_id, question_id).
with ranked as (
  select
    id,
    row_number() over (
      partition by user_id, question_id
      order by updated_at desc nulls last, attempts desc, id desc
    ) as rn
  from public.user_progress
)
delete from public.user_progress up
using ranked r
where up.id = r.id
  and r.rn > 1;

alter table public.user_progress
  drop constraint if exists user_progress_license_key_hash_question_id_key;

create unique index if not exists idx_user_progress_user_question
  on public.user_progress(user_id, question_id);

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'user_progress_user_question_key'
      and conrelid = 'public.user_progress'::regclass
  ) then
    alter table public.user_progress
      add constraint user_progress_user_question_key
      unique using index idx_user_progress_user_question;
  end if;
end $$;

alter table public.licenses alter column user_id set not null;
alter table public.user_progress alter column user_id set not null;
alter table public.mock_checkride_results alter column user_id set not null;
alter table public.user_sessions alter column user_id set not null;
alter table public.analytics_events alter column user_id set not null;

-- =========================
-- Analytics KPI Views
-- =========================
create or replace view public.analytics_funnel_daily as
with base as (
  select
    date_trunc('day', occurred_at)::date as event_date,
    user_tier,
    user_id,
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
  count(distinct case when event_name = 'landing_viewed' then user_id end) as landing_users,
  count(distinct case when event_name = 'start_studying_clicked' then user_id end) as started_users,
  count(distinct case when event_name = 'upgrade_modal_viewed' then user_id end) as upgrade_modal_users,
  count(distinct case when event_name = 'upgrade_cta_clicked' then user_id end) as upgrade_cta_users,
  count(distinct case when event_name = 'license_exchange_success' then user_id end) as converted_users
from base
group by 1, 2;

create or replace view public.analytics_paid_engagement_daily as
with paid_events as (
  select
    date_trunc('day', occurred_at)::date as event_date,
    user_id,
    session_id,
    event_name
  from public.analytics_events
  where user_tier = 'paid'
)
select
  event_date,
  count(distinct user_id) as paid_dau,
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
    user_id,
    date_trunc('day', occurred_at)::date as activity_date
  from public.analytics_events
  where user_tier = 'paid'
  group by 1, 2
),
cohorts as (
  select
    user_id,
    min(activity_date) as cohort_date
  from paid_activity
  group by 1
),
retention as (
  select
    c.cohort_date,
    c.user_id,
    max(case when a.activity_date = c.cohort_date + 1 then 1 else 0 end) as retained_d1,
    max(case when a.activity_date = c.cohort_date + 7 then 1 else 0 end) as retained_d7,
    max(case when a.activity_date = c.cohort_date + 30 then 1 else 0 end) as retained_d30
  from cohorts c
  left join paid_activity a
    on a.user_id = c.user_id
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
    ae.user_id,
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
      partition by r.user_id, r.scenario_id
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
alter table public.users enable row level security;
alter table public.user_identity_map enable row level security;
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
-- Delete all user-owned data by canonical user_id:
-- delete from public.users where user_id = '<user_id-uuid>';
--
-- Optional scoped deletes:
-- delete from public.analytics_events where user_id = '<user_id-uuid>';
-- delete from public.analytics_events where license_key_hash = '<license_key_hash>';
-- delete from public.analytics_events where anon_id = '<anon_id>';
--
-- Optional: inspect rows before deleting:
-- select count(*) from public.analytics_events where user_id = '<user_id-uuid>';
-- select count(*) from public.analytics_events where license_key_hash = '<license_key_hash>';
-- select count(*) from public.analytics_events where anon_id = '<anon_id>';
