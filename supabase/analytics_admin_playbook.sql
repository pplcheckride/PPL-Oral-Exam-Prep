-- Analytics/user data deletion playbook (admin only)
-- Use SQL editor with service/admin privileges.

-- 1) Inspect rows before deletion
-- select count(*) as rows_to_delete from public.analytics_events where user_id = '<user_id-uuid>';
-- select count(*) as rows_to_delete from public.analytics_events where license_key_hash = '<license_key_hash>';
-- select count(*) as rows_to_delete from public.analytics_events where anon_id = '<anon_id>';

-- 2) Delete all user-owned data by canonical user_id (preferred)
-- delete from public.users where user_id = '<user_id-uuid>';

-- 3) Optional scoped deletes
-- delete from public.analytics_events where user_id = '<user_id-uuid>';
-- delete from public.analytics_events where license_key_hash = '<license_key_hash>';
-- delete from public.analytics_events where anon_id = '<anon_id>';

-- 4) Optional verification
-- select count(*) as remaining from public.analytics_events where user_id = '<user_id-uuid>';
-- select count(*) as remaining from public.analytics_events where license_key_hash = '<license_key_hash>';
-- select count(*) as remaining from public.analytics_events where anon_id = '<anon_id>';
