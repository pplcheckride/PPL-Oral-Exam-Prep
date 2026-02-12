-- Analytics data deletion playbook (admin only)
-- Use SQL editor with service/admin privileges.

-- 1) Inspect rows before deletion
-- select count(*) as rows_to_delete from public.analytics_events where license_key_hash = '<license_key_hash>';
-- select count(*) as rows_to_delete from public.analytics_events where anon_id = '<anon_id>';

-- 2) Delete by paid user hash
-- delete from public.analytics_events where license_key_hash = '<license_key_hash>';

-- 3) Delete by anonymous profile id
-- delete from public.analytics_events where anon_id = '<anon_id>';

-- 4) Optional verification
-- select count(*) as remaining from public.analytics_events where license_key_hash = '<license_key_hash>';
-- select count(*) as remaining from public.analytics_events where anon_id = '<anon_id>';
