-- Run this once in Supabase SQL Editor to enable live website settings.
-- It lets the admin panel publish services, prices, gallery photos, and availability rules.

create table if not exists public.site_settings (
  key text primary key,
  settings jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.site_settings enable row level security;

drop policy if exists "Public can read site settings" on public.site_settings;
create policy "Public can read site settings"
on public.site_settings
for select
using (true);

drop policy if exists "Admins can manage site settings" on public.site_settings;
create policy "Admins can manage site settings"
on public.site_settings
for all
using (
  exists (
    select 1
    from public.admin_users
    where admin_users.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.admin_users
    where admin_users.user_id = auth.uid()
  )
);

insert into public.site_settings (key, settings)
values ('main', '{}'::jsonb)
on conflict (key) do nothing;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'site-photos',
  'site-photos',
  true,
  5242880,
  array['image/jpeg','image/png','image/webp','image/gif']
)
on conflict (id) do update
set public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "Public can read site photos" on storage.objects;
create policy "Public can read site photos"
on storage.objects
for select
using (bucket_id = 'site-photos');

drop policy if exists "Admins can upload site photos" on storage.objects;
create policy "Admins can upload site photos"
on storage.objects
for insert
with check (
  bucket_id = 'site-photos'
  and exists (
    select 1
    from public.admin_users
    where admin_users.user_id = auth.uid()
  )
);

drop policy if exists "Admins can update site photos" on storage.objects;
create policy "Admins can update site photos"
on storage.objects
for update
using (
  bucket_id = 'site-photos'
  and exists (
    select 1
    from public.admin_users
    where admin_users.user_id = auth.uid()
  )
)
with check (
  bucket_id = 'site-photos'
  and exists (
    select 1
    from public.admin_users
    where admin_users.user_id = auth.uid()
  )
);

drop policy if exists "Admins can delete site photos" on storage.objects;
create policy "Admins can delete site photos"
on storage.objects
for delete
using (
  bucket_id = 'site-photos'
  and exists (
    select 1
    from public.admin_users
    where admin_users.user_id = auth.uid()
  )
);
