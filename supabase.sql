-- Lot Ouvert : table des inscrits aux alertes. À coller une seule fois dans Supabase > SQL Editor > Run.
create table if not exists public.lo_abonnes (
  id bigint generated always as identity primary key,
  email text not null check (length(email) between 6 and 254 and email = lower(email) and email ~ '^[^@\s]+@[^@\s]+\.[a-z]{2,}$'),
  dep text not null check (dep ~ '^([0-9]{2,3}|2[AB])$'),
  metier text not null check (metier ~ '^[a-z0-9-]{2,80}$'),
  token uuid not null default gen_random_uuid() unique,
  confirme boolean not null default false,
  formule text not null default 'gratuit',
  cree_le timestamptz not null default now(),
  confirmation_envoyee_le timestamptz,
  dernier_envoi date,
  unique (email, dep, metier)
);
alter table public.lo_abonnes enable row level security;

-- Le site public peut seulement AJOUTER une inscription (e-mail, département, métier). Il ne peut rien lire ni modifier.
revoke all on public.lo_abonnes from anon, authenticated;
grant insert (email, dep, metier) on public.lo_abonnes to anon;
drop policy if exists lo_inscription on public.lo_abonnes;
create policy lo_inscription on public.lo_abonnes for insert to anon with check (true);

-- Confirmation et désinscription : uniquement avec le jeton secret reçu par e-mail.
create or replace function public.lo_confirmer(t uuid) returns boolean
language sql security definer set search_path = public as $$
  with u as (update lo_abonnes set confirme = true where token = t returning 1) select exists (select 1 from u);
$$;
create or replace function public.lo_desinscrire(t uuid) returns boolean
language sql security definer set search_path = public as $$
  with d as (delete from lo_abonnes where token = t returning 1) select exists (select 1 from d);
$$;
revoke all on function public.lo_confirmer(uuid), public.lo_desinscrire(uuid) from public;
grant execute on function public.lo_confirmer(uuid), public.lo_desinscrire(uuid) to anon;
