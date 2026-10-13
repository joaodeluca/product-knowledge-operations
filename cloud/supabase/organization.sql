-- Add categories and order. No new grants; live snapshots change only on explicit publish.
begin;
create or replace function kw_private.assert_organization(p jsonb) returns void language plpgsql set search_path='' as $$
declare c jsonb;d jsonb;cats jsonb:=coalesce(p->'categories','[]'::jsonb);ids text[]:='{}';names text[]:='{}';
begin
 if jsonb_typeof(cats) is distinct from 'array' then raise check_violation using message='Invalid categories';end if;
 if jsonb_array_length(cats)>20 then raise check_violation using message='Category quota exceeded';end if;
 for c in select value from jsonb_array_elements(cats) loop
  if jsonb_typeof(c) is distinct from 'object' or not kw_private.valid_id(c->'id') or not kw_private.valid_text(c->'name',80,true) then raise check_violation using message='Invalid category';end if;
  if c-'id'-'name'<>'{}'::jsonb or (c->>'id')=any(ids) or lower(c->>'name')=any(names) or btrim(c->>'name')<>c->>'name' then raise check_violation using message='Duplicate or invalid category';end if;
  ids:=array_append(ids,c->>'id');names:=array_append(names,lower(c->>'name'));
 end loop;
 if jsonb_typeof(p->'documents')='array' then
  for d in select value from jsonb_array_elements(p->'documents') loop
   if d ? 'categoryId' and (not kw_private.valid_text(d->'categoryId',80) or (d->>'categoryId'<>'' and not (d->>'categoryId')=any(ids))) then raise check_violation using message='Article category not found';end if;
  end loop;
 end if;
end $$;
revoke all on function kw_private.assert_organization(jsonb) from public,anon,authenticated;
create or replace function kw_private.assert_project(p jsonb) returns void language plpgsql set search_path='' as $$
declare d jsonb; h jsonb; pub jsonb; ids text[]:='{}'; filenames text[]:='{}';
begin
 perform kw_private.assert_branding(p->'branding');
 perform kw_private.assert_organization(p);
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
  docs:=docs||jsonb_build_array(jsonb_build_object('id',d->>'id','title',d->>'title','body',d->>'body')||case when coalesce(d->>'categoryId','')<>'' then jsonb_build_object('categoryId',d->>'categoryId') else '{}'::jsonb end);
 end loop;
 select string_agg(value->>'body',E'\n') into body_text from jsonb_array_elements(docs);
 -- Only aliases already written in public article text can appear in the public map.
 for d in select value from jsonb_array_elements(p->'documents') loop
  if d->>'filename'<>'' and position(lower(d->>'filename') in lower(body_text))>0 then
   links:=links||jsonb_build_array(jsonb_build_object('id',d->>'id','filename',d->>'filename'));
  end if;
 end loop;
 payload:=jsonb_build_object('name',p->>'name','documents',docs,'links',links);
 if p ? 'branding' then payload:=payload||jsonb_build_object('branding',jsonb_build_object('primaryColor',p#>>'{branding,primaryColor}','headerColor',p#>>'{branding,headerColor}','logo',p#>>'{branding,logo}'));end if;
 if p ? 'categories' then payload:=payload||jsonb_build_object('categories',(select coalesce(jsonb_agg(jsonb_build_object('id',c->>'id','name',c->>'name') order by n),'[]'::jsonb) from jsonb_array_elements(p->'categories') with ordinality as t(c,n) where exists(select 1 from jsonb_array_elements(docs) as a where a->>'categoryId'=c->>'id')));end if;
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

commit;
