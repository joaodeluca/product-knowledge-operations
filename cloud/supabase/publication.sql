-- Additive migration for the authorized personal project. Publishes no existing data.
begin;
create table if not exists kw_private.help_sites (
 owner_id uuid not null references auth.users(id) on delete cascade,
 project_id text not null,
 public_id uuid not null default gen_random_uuid() unique,
 revision bigint not null default 0,
 live boolean not null default false,
 versions jsonb not null default '[]'::jsonb,
 primary key(owner_id,project_id)
);
alter table kw_private.help_sites enable row level security;
revoke all on kw_private.help_sites from public,anon,authenticated;

create or replace function kw_private.help_metadata(s kw_private.help_sites) returns jsonb
language sql immutable set search_path='' as $$
 select jsonb_build_object('public_id',s.public_id,'revision',s.revision,'live',s.live,
 'source_version',s.versions->-1->'source_version','published_at',s.versions->-1->'published_at')
$$;

create or replace function public.kw_help_status(p_project_id text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare who uuid:=kw_private.owner(); s kw_private.help_sites;
begin
 select * into s from kw_private.help_sites where owner_id=who and project_id=p_project_id;
 if not found then return null;end if;
 return kw_private.help_metadata(s);
end $$;

create or replace function public.kw_publish_help(p_project_id text,p_expected_version bigint,p_expected_publication_revision bigint) returns jsonb
language plpgsql security definer set search_path='' as $$
declare who uuid:=kw_private.owner();items jsonb;p jsonb;d jsonb;s kw_private.help_sites;
 docs jsonb:='[]'::jsonb;links jsonb:='[]'::jsonb;body_text text;payload jsonb;entry jsonb;new_versions jsonb;total bigint;
begin
 -- Same lock as private saves: a reviewed snapshot cannot race with an edit.
 select projects into items from kw_private.workspaces where owner_id=who for update;
 select value into p from jsonb_array_elements(items) where value->>'id'=p_project_id;
 if p is null or p_expected_version is null or (p->>'version')::bigint<>p_expected_version then
  raise sqlstate 'PT409' using message='Project version conflict';end if;
 perform kw_private.assert_project(p);
 if jsonb_array_length(p->'documents')=0 then raise check_violation using message='Review every article before publishing';end if;
 for d in select value from jsonb_array_elements(p->'documents') loop
  if d#>'{review,revision}' is distinct from d->'revision' then raise check_violation using message='Review every article before publishing';end if;
  docs:=docs||jsonb_build_array(jsonb_build_object('id',d->>'id','title',d->>'title','body',d->>'body'));
 end loop;
 select string_agg(value->>'body',E'\n') into body_text from jsonb_array_elements(docs);
 -- Only aliases already written in public article text can appear in the public map.
 for d in select value from jsonb_array_elements(p->'documents') loop
  if d->>'filename'<>'' and position(lower(d->>'filename') in lower(body_text))>0 then
   links:=links||jsonb_build_array(jsonb_build_object('id',d->>'id','filename',d->>'filename'));
  end if;
 end loop;
 payload:=jsonb_build_object('name',p->>'name','documents',docs,'links',links);
 if octet_length(payload::text)>2097152 then raise check_violation using message='Publication exceeds 2 MiB';end if;
 select * into s from kw_private.help_sites where owner_id=who and project_id=p_project_id;
 if found and s.live and s.versions->-1->>'source_version'=p_expected_version::text then return kw_private.help_metadata(s);end if;
 if p_expected_publication_revision is distinct from coalesce(s.revision,0) then raise sqlstate 'PT409' using message='Publication version conflict';end if;
 if s.public_id is null then
  insert into kw_private.help_sites(owner_id,project_id) values(who,p_project_id) returning * into s;
 end if;
 new_versions:=s.versions;
 if new_versions->-1->>'source_version' is distinct from p_expected_version::text then
  if jsonb_array_length(new_versions)>=20 then raise check_violation using message='Publication history limit reached';end if;
  entry:=jsonb_build_object('source_version',p_expected_version,'published_at',now(),'payload',payload);
  new_versions:=new_versions||jsonb_build_array(entry);
 end if;
 select coalesce(sum(octet_length(h.versions::text)),0) into total from kw_private.help_sites h where h.owner_id=who and h.project_id<>p_project_id;
 if total+octet_length(new_versions::text)>8388608 then raise check_violation using message='Publication storage limit reached';end if;
 update kw_private.help_sites set live=true,revision=revision+1,versions=new_versions
 where owner_id=who and project_id=p_project_id returning * into s;
 return kw_private.help_metadata(s);
end $$;

create or replace function public.kw_unpublish_help(p_project_id text,p_expected_publication_revision bigint) returns jsonb
language plpgsql security definer set search_path='' as $$
declare who uuid:=kw_private.owner();s kw_private.help_sites;
begin
 perform 1 from kw_private.workspaces where owner_id=who for update;
 select * into s from kw_private.help_sites where owner_id=who and project_id=p_project_id;
 if not found then return null;end if;
 if not s.live then return kw_private.help_metadata(s);end if;
 if p_expected_publication_revision is distinct from s.revision then raise sqlstate 'PT409' using message='Publication version conflict';end if;
 update kw_private.help_sites set live=false,revision=revision+1 where owner_id=who and project_id=p_project_id returning * into s;
 return kw_private.help_metadata(s);
end $$;

create or replace function public.kw_read_help(p_public_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare result jsonb;
begin
 perform set_config('response.headers','[{"Cache-Control":"no-store"},{"X-Robots-Tag":"noindex"}]',true);
 select (versions->-1->'payload')||jsonb_build_object('published_at',versions->-1->'published_at') into result
 from kw_private.help_sites where public_id=p_public_id and live=true;
 if result is null then raise sqlstate 'PT404' using message='Publication unavailable';end if;
 return result;
end $$;
revoke all on function kw_private.help_metadata(kw_private.help_sites) from public,anon,authenticated;
revoke all on function public.kw_help_status(text),public.kw_publish_help(text,bigint,bigint),public.kw_unpublish_help(text,bigint),public.kw_read_help(uuid) from public,anon,authenticated;
grant execute on function public.kw_help_status(text),public.kw_publish_help(text,bigint,bigint),public.kw_unpublish_help(text,bigint) to authenticated;
grant execute on function public.kw_read_help(uuid) to anon,authenticated;
commit;
