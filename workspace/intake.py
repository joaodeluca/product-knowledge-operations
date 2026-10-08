"""Finite Markdown intake: dry preview, originals retained, one atomic commit."""
import re
import json
import difflib
import unicodedata
import uuid
from pathlib import Path
import engine as e

MAX_FILES = 32
MAX_BYTES = 128 * 1024
POLICY = e._hash(Path(__file__).read_bytes())
LINK = re.compile(r'(!?)\[([^\]\n]+)\]\(([^)\n]+)\)')


def prepare(desk, db, pid, data, revision, *, replacing=None, link_mapping=None):
    desk._cas(db, pid, revision)
    files = data.get('files')
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
        raise e.DeskError('batch_size', 'Escolha entre 1 e 32 arquivos Markdown.')
    if data.get('original_owned') is not True:
        raise e.DeskError('ownership_required', 'Declare que os documentos são próprios.')
    limits = e._text(data.get('limits'), 'Limites públicos do lote', 8192)
    existing = {a['slug'] for a in desk._items(db, 'articles', pid) if a['id'] != replacing}
    names, slugs, rows, total = set(), set(), [], 0
    for f in files:
        if not isinstance(f, dict): raise e.DeskError('invalid_file', 'Arquivo inválido.')
        name = f.get('name')
        if not isinstance(name, str) or not 1 <= len(name) <= 120 or any(ord(c)<32 for c in name) or re.search(r'[/\\]', name) or '..' in name or not name.lower().endswith('.md'):
            raise e.DeskError('invalid_name', 'Use nomes simples de arquivos .md, sem pastas ou travessia.')
        try: original = e._content(f.get('content'), name, MAX_BYTES)
        except UnicodeError as exc: raise e.DeskError('invalid_utf8', 'Texto precisa de UTF-8 válido.') from exc
        total += len(original.encode('utf8'))
        stem = unicodedata.normalize('NFKD', name[:-3]).encode('ascii','ignore').decode().lower()
        slug = re.sub(r'[^a-z0-9]+','-',stem).strip('-')[:80]
        first = next((line for line in original.lstrip('\ufeff').splitlines() if line.strip()), '')
        heading = re.fullmatch(r'#\s+(.+)', first)
        title = heading[1] if heading else name[:-3]
        title = e._text(title, 'Título', 200)
        errors, warnings = [], []
        if name.casefold() in names: errors.append('Nome repetido no lote.')
        if not slug or slug in slugs or slug in existing: errors.append('Endereço vazio, repetido ou já existente: '+slug)
        if original.lstrip('\ufeff').startswith('---'): errors.append('Front matter não suportado; remova os metadados antes de importar.')
        names.add(name.casefold()); slugs.add(slug)
        rows.append({'name':name,'slug':slug,'title':title,'original':original,'sha256':e._hash(original),'bytes':len(original.encode()),'errors':errors,'warnings':warnings,'links_changed':0,'title_extracted':bool(heading)})
    if total > MAX_BYTES: raise e.DeskError('batch_oversize','O lote ultrapassa 128 KiB UTF-8.',413)
    mapping=dict(link_mapping or {})
    mapping.update({r['name']:r['slug']+'.html' for r in rows})
    for row in rows:
        def replace(m):
            image,label,href=m.groups()
            if image:
                row['errors'].append('Imagem exige preparação separada: '+href); return m[0]
            if re.fullmatch(r'https://[A-Za-z0-9.-]+(?::[0-9]+)?(?:/[^\s<>"\x27\\]*)?',href): return m[0]
            target=href[2:] if href.startswith('./') else href
            if target in mapping:
                row['links_changed']+=1; return '['+label+']('+mapping[target]+')'
            row['errors'].append('Link local ou formato não resolvido: '+href); return m[0]
        # Code examples are preserved, never interpreted as navigation.
        in_code=False; lines=[]
        for line in row['original'].splitlines(keepends=True):
            if line.startswith('```'): in_code=not in_code; lines.append(line); continue
            if in_code: lines.append(line); continue
            parts=re.split(r'(`[^`\n]*`)',line)
            lines.append(''.join(part if i%2 else LINK.sub(replace,part) for i,part in enumerate(parts)))
        row['markdown']=''.join(lines).lstrip('\ufeff')
        if row['title_extracted']:
            row['markdown']=re.sub(r'\A(?:[ \t]*\r?\n)*#\s+[^\r\n]+(?:\r?\n|$)', '', row['markdown'], count=1)
            if not row['markdown'].strip():
                row['errors'].append('Documento precisa de conteúdo além do título.')
        if re.search(r'^\s*\[[^\]]+\]:',row['original'],re.M) or re.search(r'\]\[[^\]]*\]',row['original']):
            row['errors'].append('Links por referência não suportados neste importador.')
        row['warnings'].append('Entra como rascunho sem revisão. Confira formatação e veracidade antes de publicar.')
    for table in ('sources','articles'):
        count=db.execute(f'SELECT COUNT(*) FROM {table} WHERE project_id=?',(pid,)).fetchone()[0]
        if count+(0 if replacing else len(rows))>e.MAX_ITEMS: raise e.DeskError('item_limit','O lote excede 64 fontes ou artigos no projeto.',413)
    digest=e._hash(e._json({'policy':POLICY,'project':pid,'revision':revision,'files':files,'limits':limits,'original_owned':True}))
    return rows,limits,digest


def preview(desk,pid,data,revision):
    with desk._lock,desk._connect() as db:
        rows,limits,digest=prepare(desk,db,pid,data,revision)
        return {'plan':digest,'project_revision':revision,'can_apply':not any(r['errors'] for r in rows),'total_bytes':sum(r['bytes'] for r in rows),'limits':limits,'files':rows}


def apply(desk,pid,data,revision):
    with desk._lock,desk._connect() as db:
        db.execute('BEGIN IMMEDIATE')
        rows,limits,digest=prepare(desk,db,pid,data,revision)
        if data.get('plan')!=digest or data.get('confirmed') is not True:
            raise e.DeskError('plan_changed','Confira e confirme a prévia exata deste lote.',409)
        if any(r['errors'] for r in rows): raise e.DeskError('batch_conflict','Lote com conflitos; nada foi importado.',409)
        added=[]
        for row in rows:
            sid='s_'+uuid.uuid4().hex; aid='a_'+uuid.uuid4().hex
            source=desk._source({'title':row['title'],'content':row['original'],'version':'import-1','original_owned':True,'evidence':'Arquivo próprio importado: '+row['name']+' · SHA256 '+row['sha256'],'limits':'Importação textual; execução e veracidade não conferidas.','files':[]})
            db.execute('INSERT INTO sources(id,project_id,data,revision) VALUES(?,?,?,1)',(sid,pid,e._json(source)))
            db.execute('INSERT INTO snapshots(source_id,revision,content,sha256,created_at,data) VALUES(?,1,?,?,?,?)',(sid,source['content'],e._hash(e._json({k:source[k] for k in ('content','files')})),e._now(),e._json(source)))
            article=desk._article(db,pid,{'title':row['title'],'slug':row['slug'],'markdown':row['markdown'],'source_ids':[sid],'limits':limits,'evidence':'Importado sem validação do procedimento; revisar contra a fonte original.'})
            db.execute('INSERT INTO articles(id,project_id,data,revision,review) VALUES(?,?,?,1,NULL)',(aid,pid,e._json(article)))
            added.append({'source_id':sid,'article_id':aid,'original_name':row['name'],'sha256':row['sha256']})
        desk._event(db,pid,'markdown_batch_imported',{'plan':digest,'files':added,'automatically_reviewed':False})
        return desk._project(db,pid)


def _update_plan(desk, db, pid, data, revision):
    desk._cas(db, pid, revision)
    aid = data.get('article_id')
    article = desk._get(db, 'articles', pid, aid, 'a')
    associations = {}
    for event in db.execute("SELECT details FROM history WHERE project_id=? AND action='markdown_batch_imported' ORDER BY id", (pid,)):
        for item in json.loads(event['details'])['files']:
            associations[item['article_id']] = item
    association = associations.get(aid)
    if not association or article['source_ids'] != [association['source_id']]:
        raise e.DeskError('not_imported', 'Atualização por arquivo exige o artigo importado e sua fonte original única.', 409)
    source = desk._get(db, 'sources', pid, association['source_id'], 's')
    if source['files']:
        raise e.DeskError('attached_source', 'Esta fonte possui anexos; use a edição manual para preservá-los.', 409)
    files = data.get('files')
    if not isinstance(files, list) or len(files) != 1 or not isinstance(files[0], dict) or files[0].get('name') != association['original_name']:
        raise e.DeskError('original_name', 'Selecione somente o arquivo original: '+association['original_name'])
    # Names come from immutable import events; destinations use current article slugs.
    articles = desk._items(db, 'articles', pid)
    mapping = {}; ambiguous = set()
    for other in articles:
        origin = associations.get(other['id'])
        if not origin: continue
        name = origin['original_name']
        if name in mapping: ambiguous.add(name)
        mapping[name] = other['slug']+'.html'
    for name in ambiguous: mapping.pop(name, None)
    request = dict(data, limits=article['limits'])
    rows, _, _ = prepare(desk, db, pid, request, revision, replacing=aid, link_mapping=mapping)
    row = rows[0]
    # Keep published addresses stable even if manually renamed after import.
    if row['slug'] != article['slug']:
        row['errors'].append('O endereço foi alterado desde a importação; use a edição manual.')
    before = {'title':article['title'], 'markdown':article['markdown'], 'original':source['content']}
    after = {'title':row['title'], 'markdown':row['markdown'], 'original':row['original']}
    changed = before != after or source['title'] != row['title']
    affected = []
    procedures = {t['id']:t for t in desk._items(db, 'procedures', pid)}
    for other in articles:
        dependencies = set(other['source_ids'])
        dependencies.update(procedures.get(other['procedure_id'], {}).get('source_ids', []))
        if source['id'] in dependencies: affected.append({'id':other['id'], 'title':other['title']})
    diffs = {key: ''.join(difflib.unified_diff(before[key].splitlines(keepends=True), after[key].splitlines(keepends=True), fromfile='Antes', tofile='Depois')) for key in before}
    digest = e._hash(e._json({'policy':POLICY,'project':pid,'revision':revision,'article_id':aid,'files':files,'original_owned':data.get('original_owned'),'before':before,'after':after}))
    result = {'plan':digest,'project_revision':revision,'can_apply':changed and not row['errors'],'changed':changed,'article_id':aid,'source_id':source['id'],'name':row['name'],'slug':article['slug'],'before':before,'after':after,'diffs':diffs,'errors':row['errors'],'affected_articles':affected,'links_changed':row['links_changed'],'limits':article['limits']}
    return result, source, article


def update_preview(desk, pid, data, revision):
    with desk._lock, desk._connect() as db:
        result, _, _ = _update_plan(desk, db, pid, data, revision)
        return result


def update_apply(desk, pid, data, revision):
    with desk._lock, desk._connect() as db:
        db.execute('BEGIN IMMEDIATE')
        plan, old_source, old_article = _update_plan(desk, db, pid, data, revision)
        if data.get('plan') != plan['plan'] or data.get('confirmed') is not True:
            raise e.DeskError('plan_changed', 'Confira e confirme esta prévia exata.', 409)
        if plan['errors']:
            raise e.DeskError('update_conflict', 'Atualização com conflitos; nada foi salvo.', 409)
        if not plan['changed']: return desk._project(db, pid)
        source = desk._source(dict(old_source, title=plan['after']['title'], content=plan['after']['original'], version='import-'+str(old_source['revision']+1), evidence='Arquivo próprio atualizado: '+plan['name']+' · SHA256 '+e._hash(plan['after']['original'])))
        article = desk._article(db, pid, dict(old_article, title=plan['after']['title'], markdown=plan['after']['markdown']))
        old_review = db.execute('SELECT review FROM articles WHERE id=? AND project_id=?',(old_article['id'],pid)).fetchone()['review']
        db.execute('UPDATE sources SET data=?,revision=revision+1 WHERE id=? AND project_id=?',(e._json(source),old_source['id'],pid))
        db.execute('INSERT INTO snapshots(source_id,revision,content,sha256,created_at,data) VALUES(?,?,?,?,?,?)',(old_source['id'],old_source['revision']+1,source['content'],e._hash(e._json({k:source[k] for k in ('content','files')})),e._now(),e._json(source)))
        db.execute('UPDATE articles SET data=?,revision=revision+1 WHERE id=? AND project_id=?',(e._json(article),old_article['id'],pid))
        desk._event(db,pid,'markdown_file_updated',{'plan':plan['plan'],'article_id':old_article['id'],'source_id':old_source['id'],'original_name':plan['name'],'original_sha256':e._hash(source['content']),'previous_article':old_article,'previous_review':json.loads(old_review) if old_review else None,'affected_articles':plan['affected_articles'],'automatically_reviewed':False})
        return desk._project(db,pid)
