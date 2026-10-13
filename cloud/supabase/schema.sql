-- Apply only to a newly authorized personal Supabase project.
-- No public signup or member provisioning is performed by this migration.
begin;
create schema if not exists kw_private;
revoke all on schema kw_private from public, anon, authenticated;
create table if not exists kw_private.members (user_id uuid primary key references auth.users(id) on delete cascade);
create table if not exists kw_private.workspaces (
  owner_id uuid primary key references auth.users(id) on delete cascade,
  projects jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);
alter table kw_private.members enable row level security;
alter table kw_private.workspaces enable row level security;
revoke all on all tables in schema kw_private from public, anon, authenticated;
-- Only the functions below can read/write these tables. No anonymous table access.
create or replace function kw_private.owner() returns uuid language plpgsql security definer set search_path='' as $$
declare who uuid:=auth.uid();
begin
  if who is null or not exists(select 1 from kw_private.members where user_id=who) then
    raise sqlstate '42501' using message='Workspace membership required';
  end if;
  return who;
end $$;

create or replace function kw_private.valid_text(v jsonb, maximum integer, nonempty boolean default false)
returns boolean language sql immutable set search_path='' as $$
  select coalesce(jsonb_typeof(v)='string' and length(v#>>'{}')<=maximum and (not nonempty or length(btrim(v#>>'{}'))>0),false)
$$;
create or replace function kw_private.valid_number(v jsonb, minimum bigint default 0)
returns boolean language plpgsql immutable set search_path='' as $$
begin
  return coalesce(jsonb_typeof(v)='number' and (v#>>'{}')::numeric between minimum and 9007199254740991 and trunc((v#>>'{}')::numeric)=(v#>>'{}')::numeric,false);
exception when others then return false;
end $$;
create or replace function kw_private.valid_id(v jsonb) returns boolean language sql immutable set search_path='' as $$
 select coalesce(jsonb_typeof(v)='string' and (v#>>'{}') ~ '^[a-zA-Z0-9-]{1,80}$',false)
$$;
create or replace function kw_private.assert_project(p jsonb) returns void language plpgsql set search_path='' as $$
declare d jsonb; h jsonb; pub jsonb; ids text[]:='{}'; filenames text[]:='{}';
begin
 if jsonb_typeof(p) is distinct from 'object' or not kw_private.valid_id(p->'id') or not kw_private.valid_text(p->'name',120,true)
 or not kw_private.valid_text(p->'createdAt',40) or not kw_private.valid_number(p->'version')
 or jsonb_typeof(p->'documents') is distinct from 'array' or jsonb_typeof(p->'publications') is distinct from 'array' then
   raise check_violation using message='Invalid project';
 end if;
 if jsonb_array_length(p->'documents')>50 or jsonb_array_length(p->'publications')>20 then raise check_violation using message='Project quota exceeded';end if;
 for d in select value from jsonb_array_elements(p->'documents') loop
  if not kw_private.valid_id(d->'id') or (d->>'id')=any(ids) or not kw_private.valid_text(d->'title',160,true)
   or not kw_private.valid_text(d->'body',131072) or not kw_private.valid_text(d->'original',131072)
   or not kw_private.valid_text(d->'filename',200) or not kw_private.valid_number(d->'revision',1)
   or jsonb_typeof(d->'history') is distinct from 'array' then raise check_violation using message='Invalid document';end if;
  ids:=array_append(ids,d->>'id');
  if d->>'filename'<>'' then
    if lower(d->>'filename')=any(filenames) then raise check_violation using message='Duplicate filename';end if;
    filenames:=array_append(filenames,lower(d->>'filename'));
  end if;
  if not (d ? 'review') then raise check_violation using message='Missing review';end if;
  if d->'review'<>'null'::jsonb then
    if not kw_private.valid_number(d#>'{review,revision}',1) or (d#>>'{review,revision}')::numeric>(d->>'revision')::numeric
      or not kw_private.valid_text(d#>'{review,note}',2000) or not kw_private.valid_text(d#>'{review,at}',40) then raise check_violation using message='Invalid review';end if;
  end if;
  for h in select value from jsonb_array_elements(d->'history') loop
    if not kw_private.valid_text(h->'title',160) or not kw_private.valid_text(h->'body',131072)
      or not kw_private.valid_text(h->'at',40) or not kw_private.valid_number(h->'revision',1)
      or (h->>'revision')::numeric >= (d->>'revision')::numeric then raise check_violation using message='Invalid history';end if;
  end loop;
 end loop;
 for pub in select value from jsonb_array_elements(p->'publications') loop
  if not kw_private.valid_id(pub->'id') or not kw_private.valid_text(pub->'at',40)
   or not kw_private.valid_text(pub->'html',2097152) or not kw_private.valid_number(pub->'version') then raise check_violation using message='Invalid publication';end if;
 end loop;
end $$;
create or replace function kw_private.assert_workspace(p jsonb) returns void language plpgsql set search_path='' as $$
begin
 if jsonb_array_length(p)>20 or octet_length(p::text)>8388608 then raise check_violation using message='Workspace quota exceeded';end if;
end $$;

create or replace function public.kw_list_projects() returns jsonb language plpgsql security definer set search_path='' as $$
declare who uuid:=kw_private.owner(); result jsonb;
begin
 select projects into result from kw_private.workspaces where owner_id=who;
 return coalesce(result,'[]'::jsonb);
end $$;

create or replace function public.kw_save_project(p_project jsonb,p_expected_version bigint) returns jsonb language plpgsql security definer set search_path='' as $$
declare who uuid:=kw_private.owner(); items jsonb; old jsonb; saved jsonb;
begin
 perform kw_private.assert_project(p_project);
 if p_expected_version<0 or p_expected_version>9007199254740990 or (p_project->>'version')::bigint<>coalesce(p_expected_version,0) then raise check_violation using message='Invalid expected version';end if;
 insert into kw_private.workspaces(owner_id) values(who) on conflict do nothing;
 select projects into items from kw_private.workspaces where owner_id=who for update;
 select value into old from jsonb_array_elements(items) where value->>'id'=p_project->>'id';
 if (old is null and p_expected_version is not null) or (old is not null and (p_expected_version is null or (old->>'version')::bigint<>p_expected_version)) then
   raise sqlstate 'PT409' using message='Project version conflict';
 end if;
 saved:=jsonb_set(p_project,'{version}',to_jsonb(coalesce(p_expected_version,0)+1));
 select coalesce(jsonb_agg(value),'[]'::jsonb) into items from jsonb_array_elements(items) where value->>'id'<>p_project->>'id';
 items:=items||jsonb_build_array(saved);perform kw_private.assert_workspace(items);
 update kw_private.workspaces set projects=items,updated_at=now() where owner_id=who;
 return saved;
end $$;

create or replace function public.kw_restore_projects(p_projects jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare who uuid:=kw_private.owner(); items jsonb; p jsonb; ids text[]:='{}';
begin
 if jsonb_typeof(p_projects) is distinct from 'array' then raise check_violation using message='Invalid restore';end if;
 if jsonb_array_length(p_projects)<1 or jsonb_array_length(p_projects)>20 then raise check_violation using message='Restore quota exceeded';end if;
 insert into kw_private.workspaces(owner_id) values(who) on conflict do nothing;
 select projects into items from kw_private.workspaces where owner_id=who for update;
 for p in select value from jsonb_array_elements(p_projects) loop
   perform kw_private.assert_project(p);
   if (p->>'version')::bigint<>1 or (p->>'id')=any(ids) or exists(select 1 from jsonb_array_elements(items) where value->>'id'=p->>'id') then raise sqlstate 'PT409' using message='Restore id conflict';end if;
   ids:=array_append(ids,p->>'id');
 end loop;
 items:=items||p_projects;perform kw_private.assert_workspace(items);
 update kw_private.workspaces set projects=items,updated_at=now() where owner_id=who;
 return p_projects;
end $$;
revoke all on all functions in schema kw_private from public, anon, authenticated;
revoke all on function public.kw_list_projects(),public.kw_save_project(jsonb,bigint),public.kw_restore_projects(jsonb) from public,anon,authenticated;
grant execute on function public.kw_list_projects(),public.kw_save_project(jsonb,bigint),public.kw_restore_projects(jsonb) to authenticated;
commit;
