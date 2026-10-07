-- Rajasthan Government Office Order Generator
-- FINAL Supabase schema/permission patch for integrated app.py
-- Run in Supabase SQL Editor.

-- ------------------------------------------------------------
-- 1. PROFILE COLUMNS REQUIRED BY app.py
-- ------------------------------------------------------------
alter table public.profiles
    add column if not exists address text;

alter table public.profiles
    add column if not exists username text;

alter table public.profiles
    add column if not exists full_name text;

alter table public.profiles
    add column if not exists mobile text;

alter table public.profiles
    add column if not exists email text;

alter table public.profiles
    add column if not exists role text default 'user';

alter table public.profiles
    add column if not exists is_active boolean default true;

-- ------------------------------------------------------------
-- 2. NORMALIZE EXISTING VALUES
-- ------------------------------------------------------------
update public.profiles
set username = lower(trim(username))
where username is not null;

update public.profiles
set email = lower(trim(email))
where email is not null;

update public.profiles
set is_active = true
where is_active is null;

-- ------------------------------------------------------------
-- 3. UNIQUENESS
-- ------------------------------------------------------------
-- Prevent two application accounts from using the same Login ID.
create unique index if not exists profiles_username_unique
    on public.profiles (lower(username));

-- Prevent duplicate saved bundle for the same user/module.
create unique index if not exists module_data_user_module_unique
    on public.module_data (user_id, module)
    where module not like '__activity__%' and module not like '__visitor__%';

-- ------------------------------------------------------------
-- 4. SERVICE ROLE PERMISSIONS
-- ------------------------------------------------------------
grant usage on schema public to service_role;
grant select, insert, update, delete on table public.profiles to service_role;
grant select, insert, update, delete on table public.module_data to service_role;

-- ------------------------------------------------------------
-- 5. VERIFY TABLE STRUCTURE
-- ------------------------------------------------------------
select column_name, data_type
from information_schema.columns
where table_schema = 'public'
  and table_name = 'profiles'
order by ordinal_position;

select column_name, data_type
from information_schema.columns
where table_schema = 'public'
  and table_name = 'module_data'
order by ordinal_position;

-- ------------------------------------------------------------
-- IMPORTANT
-- ------------------------------------------------------------
-- 1. SUPABASE_SERVICE_ROLE_KEY must remain only in Streamlit Secrets.
-- 2. Never upload that key to GitHub.
-- 3. Existing profiles.user_id values must be valid auth.users(id).
-- 4. If the unique index creation reports duplicate rows, stop and
--    clean those duplicate (user_id,module) rows before rerunning it.
-- 5. The integrated app.py has a compatibility fallback, but the unique
--    index above is strongly recommended for atomic upsert behavior.
