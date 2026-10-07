"""Allowlist-only reader export. Internal records never enter the public manifest."""
import html
import json
import hashlib
import base64

STYLE = '''body{font:17px/1.65 system-ui,sans-serif;color:#20352f;background:#fbfaf6;margin:0}main{max-width:900px;margin:auto;padding:40px 24px 80px}h1{font-size:clamp(28px,5vw,46px);line-height:1.15}h2{margin-top:36px}a{color:#116346;overflow-wrap:anywhere}p,li{overflow-wrap:anywhere}pre{background:#eee;padding:18px;overflow:auto;border-radius:10px}table{display:block;overflow:auto;border-collapse:collapse}td,th{padding:8px;border:1px solid #ccc}nav{border-bottom:1px solid #ddd;padding-bottom:20px}aside{background:#eeeee5;padding:16px;border-left:3px solid #b49b61}footer{margin-top:48px;font-size:13px;color:#64756c}img{max-width:100%}'''

def page(title, body, script=""):
    policy = "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'"
    if script:
        policy += "; script-src 'sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode() + "'"
    extra = "<script>"+script+"</script>" if script else ""
    return ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="'+html.escape(policy, quote=True)+'"><title>'+html.escape(title)+'</title><style>'+STYLE+'</style></head><body><main>'+body+'<footer>Conteúdo mantido pelo responsável por esta central.</footer></main>'+extra+'</body></html>').encode()

def build(project, release_id, render, digest, encode, now):
    files={}; search=[]; paths={'articles/'+a['slug']+'.html' for a in project['articles']}; links=[]
    for a in project['articles']:
        name='articles/'+a['slug']+'.html'
        files[name]=page(a['title'], '<nav><a href="../index.html">← Central de ajuda</a></nav><h1>'+html.escape(a['title'])+'</h1>'+render(a['markdown'], paths)+'<aside><strong>Limites deste procedimento</strong><p>'+html.escape(a['limits'])+'</p></aside>')
        search.append({'title':a['title'],'text':a['markdown']+' '+a['limits'],'href':name})
        links.append('<li><a href="'+name+'">'+html.escape(a['title'])+'</a></li>')
    data=json.dumps(search,ensure_ascii=True).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    script='const documents='+data+';'+SEARCH_SCRIPT
    files['index.html']=page(project['name'], '<nav>Central de ajuda</nav><h1>'+html.escape(project['name'])+'</h1><div id="search" hidden><label for="query">Buscar nos artigos</label><input id="query" type="search" placeholder="Digite uma dúvida ou palavra" maxlength="200" style="display:block;width:100%;box-sizing:border-box;padding:14px;font:inherit;margin:10px 0"><button id="clear" type="button">Limpar busca</button><p id="result-status" role="status" aria-live="polite"></p><ul id="results"></ul></div><section id="all-articles"><h2>Todos os artigos</h2><ul>'+''.join(links)+'</ul></section><noscript>A busca precisa de JavaScript; todos os artigos continuam disponíveis abaixo.</noscript>',script)
    # Do not export project purpose/authority, source text, evidence, reviewer,
    # revision notes or source titles. The selected reader text can still be
    # sensitive: the operator must inspect the preview before sharing.
    manifest={'schema_version':1,'id':release_id,'format':'public-reader-only','created_at':now(),'files':[{'path':p,'bytes':len(b),'sha256':digest(b)} for p,b in sorted(files.items())]}
    files['manifest.json']=(encode(manifest)+'\n').encode()
    if sum(map(len,files.values()))>8*1024*1024:
        raise ValueError('Central acima do limite de8MiB')
    return files,manifest


SEARCH_SCRIPT = r"""
'use strict';
const normal=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('pt-BR');
const records=documents.map(d=>({...d,normalized:normal(d.title+' '+d.text),heading:normal(d.title)}));
const query=document.getElementById('query'),results=document.getElementById('results'),status=document.getElementById('result-status');
document.getElementById('search').hidden=false;
function search(){
 const terms=normal(query.value.trim()).split(/\s+/).filter(Boolean);
 results.replaceChildren();document.getElementById('all-articles').hidden=terms.length>0;
 if(!terms.length){status.textContent='Busca local, sem envio de dados.';return;}
 const found=records.filter(d=>terms.every(t=>d.normalized.includes(t))).sort((a,b)=>terms.filter(t=>b.heading.includes(t)).length-terms.filter(t=>a.heading.includes(t)).length);
 status.textContent=found.length?found.length+' artigo(s) encontrado(s).':'Nenhum artigo encontrado. Tente outra palavra.';
 for(const d of found){const li=document.createElement('li'),a=document.createElement('a'),p=document.createElement('p');a.href=d.href;a.textContent=d.title;p.textContent=d.text.replace(/\s+/g,' ').slice(0,220);li.append(a,p);results.append(li);}
}
query.addEventListener('input',search);document.getElementById('clear').addEventListener('click',()=>{query.value='';search();query.focus();});search();
"""
