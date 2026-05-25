-- Complaint Analytics Dashboard shared Supabase schema
-- Run this in the Supabase SQL editor for your project.

create table if not exists public.complaints (
    id text primary key,
    created_date timestamptz not null,
    closed_date timestamptz,
    state text,
    district text,
    municipality text,
    village text,
    area text not null,
    pincode text check (pincode is null or pincode ~ '^[1-9][0-9]{5}$'),
    category text not null,
    priority text check (priority in ('Low', 'Medium', 'High')),
    status text not null default 'Pending'
        check (status in ('Pending', 'In Progress', 'Closed')),
    description text not null check (char_length(trim(description)) >= 10),
    user_contact text,
    image_path text,
    inserted_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.complaints
    add column if not exists state text;

alter table public.complaints
    add column if not exists district text;

alter table public.complaints
    add column if not exists municipality text;

alter table public.complaints
    add column if not exists village text;

alter table public.complaints
    add column if not exists pincode text;

alter table public.complaints
    add column if not exists user_contact text;

alter table public.complaints
    add column if not exists image_path text;

create index if not exists complaints_created_date_idx
    on public.complaints (created_date desc);

create index if not exists complaints_area_idx
    on public.complaints (area);

create index if not exists complaints_state_idx
    on public.complaints (state);

create index if not exists complaints_district_idx
    on public.complaints (district);

create index if not exists complaints_pincode_idx
    on public.complaints (pincode);

create index if not exists complaints_category_idx
    on public.complaints (category);

create index if not exists complaints_status_idx
    on public.complaints (status);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists set_complaints_updated_at on public.complaints;
create trigger set_complaints_updated_at
before update on public.complaints
for each row
execute function public.set_updated_at();

alter table public.complaints enable row level security;

drop policy if exists "Complaints are visible to everyone" on public.complaints;
create policy "Complaints are visible to everyone"
on public.complaints
for select
to anon, authenticated
using (true);

drop policy if exists "Anyone can create complaints" on public.complaints;
create policy "Anyone can create complaints"
on public.complaints
for insert
to anon, authenticated
with check (true);

drop policy if exists "Anyone can update complaints" on public.complaints;
create policy "Anyone can update complaints"
on public.complaints
for update
to anon, authenticated
using (true)
with check (true);

drop policy if exists "Anyone can delete complaints" on public.complaints;
create policy "Anyone can delete complaints"
on public.complaints
for delete
to anon, authenticated
using (true);
