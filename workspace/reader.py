"""Allowlist-only reader export. Internal records never enter the public manifest."""
import html

STYLE = '''body{font:17px/1.65 system-ui,sans-serif;color:#20352f;background:#fbfaf6;margin:0}main{max-width:900px;margin:auto;padding:40px 24px 80px}h1{font-size:clamp(28px,5vw,46px);line-height:1.15}h2{margin-top:36px}a{color:#116346;overflow-wrap:anywhere}p,li{overflow-wrap:anywhere}pre{background:#eee;padding:18px;overflow:auto;border-radius:10px}table{display:block;overflow:auto;border-collapse:collapse}td,th{padding:8px;border:1px solid #ccc}nav{border-bottom:1px solid #ddd;padding-bottom:20px}aside{background:#eeeee5;padding:16px;border-left:3px solid #b49b61}footer{margin-top:48px;font-size:13px;color:#64756c}img{max-width:100%}'''

def page(title, body):
    return ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'"><title>'+html.escape(title)+'</title><style>'+STYLE+'</style></head><body><main>'+body+'<footer>Conteúdo mantido pelo responsável por esta central.</footer></main></body></html>').encode()

def build(project, release_id, render, digest, encode, now):
    files={}; paths={'articles/'+a['slug']+'.html' for a in project['articles']}; links=[]
    for a in project['articles']:
        name='articles/'+a['slug']+'.html'
        files[name]=page(a['title'], '<nav><a href="../index.html">← Central de ajuda</a></nav><h1>'+html.escape(a['title'])+'</h1>'+render(a['markdown'], paths)+'<aside><strong>Limites deste procedimento</strong><p>'+html.escape(a['limits'])+'</p></aside>')
        links.append('<li><a href="'+name+'">'+html.escape(a['title'])+'</a></li>')
    files['index.html']=page(project['name'], '<nav>Central de ajuda</nav><h1>'+html.escape(project['name'])+'</h1><ul>'+''.join(links)+'</ul>')
    # Do not export project purpose/authority, source text, evidence, reviewer,
    # revision notes or source titles. The selected reader text can still be
    # sensitive: the operator must inspect the preview before sharing.
    manifest={'schema_version':1,'id':release_id,'format':'public-reader-only','created_at':now(),'files':[{'path':p,'bytes':len(b),'sha256':digest(b)} for p,b in sorted(files.items())]}
    files['manifest.json']=(encode(manifest)+'\n').encode()
    if sum(map(len,files.values()))>8*1024*1024:
        raise ValueError('Central acima do limite de8MiB')
    return files,manifest
