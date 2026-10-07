"""Finite Markdown intake: dry preview, originals retained, one atomic commit."""
import re
import unicodedata
import uuid
from pathlib import Path
import engine as e

MAX_FILES = 32
MAX_BYTES = 128 * 1024
POLICY = e._hash(Path(__file__).read_bytes())
LINK = re.compile(r'(!?)\[([^\]\n]+)\]\(([^)\n]+)\)')


def prepare(desk, db, pid, data, revision):
    desk._cas(db, pid, revision)
    files = data.get('files')
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
        raise e.DeskError('batch_size', 'Escolha entre 1 e 32 arquivos Markdown.')
    if data.get('original_owned') is not True:
        raise e.DeskError('ownership_required', 'Declare que os documentos são próprios.')
    limits = e._text(data.get('limits'), 'Limites públicos do lote', 8192)
    existing = {a['slug'] for a in desk._items(db, 'articles', pid)}
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
    mapping={r['name']:r['slug']+'.html' for r in rows}
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
        if count+len(rows)>e.MAX_ITEMS: raise e.DeskError('item_limit','O lote excede 64 fontes ou artigos no projeto.',413)
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
