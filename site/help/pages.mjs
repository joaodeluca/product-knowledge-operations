import {escape as esc,markdown,logoHTML,articleGroups} from '../browser/model.mjs';
import {matches} from './reader.mjs';
// Query routes work on static hosting, including refreshes and shared deep links.
export function helpHref(id,{article,category,q}={}){
 const params=new URLSearchParams({id});
 if(article)params.set('article',article);else if(category!==undefined&&category!==null)params.set('category',category);
 if(q?.trim())params.set('q',q.trim().slice(0,200));
 return '?'+params.toString();
}
export function readRoute(url){const u=new URL(url);return {id:u.searchParams.get('id'),article:u.searchParams.get('article')||(u.hash.startsWith('#article-')?u.hash.slice(9):null),category:u.searchParams.get('category'),q:(u.searchParams.get('q')||'').slice(0,200)};}
export function articleText(d,links=[]){return markdown(d.body,links).replace(/<\/(?:p|h[1-6]|li|pre|blockquote)>|<br\s*\/?>/g,' ').replace(/<[^>]*>/g,'').replace(/&(amp|lt|gt|quot|#39);/g,(_,x)=>({amp:'&',lt:'<',gt:'>',quot:'"','#39':"'"}[x])).replace(/\s+/g,' ').trim();}
export function articleBody(p,d,id){return markdown(d.body,p.links).replace(/href="#article-([a-zA-Z0-9-]+)"/g,(_,target)=>'href="'+esc(helpHref(id,{article:target}))+'"');}
export function renderPage(p,route){
 const {id,article,category,q}=route,groups=articleGroups(p),ordered=groups.flatMap(g=>g.documents),doc=ordered.find(d=>d.id===article),group=doc?groups.find(g=>g.documents.includes(doc)):groups.find(g=>g.id===category);
 const href=options=>esc(helpHref(id,options));
 const link=(label,options,extra='')=>'<a data-route href="'+href(options)+'" '+extra+'>'+esc(label)+'</a>';
 const sidebar='<aside class="reader-sidebar"><nav aria-label="Categorias">'+link('Todos os artigos',{},!article&&category===null&&!q?'aria-current="page"':'')+groups.map(g=>link((g.name||'Artigos')+' · '+g.documents.length,{category:g.id},group===g?'aria-current="page"':'')).join('')+'</nav></aside>';
 const cards=docs=>'<div class="reader-cards">'+docs.map(d=>'<a data-route class="reader-card" href="'+href({article:d.id})+'"><span class="card-title">'+esc(d.title)+' <span aria-hidden="true">↗</span></span><span class="card-summary">'+esc(articleText(d,p.links).slice(0,150))+'</span></a>').join('')+'</div>';
 let content,title=p.name;
 const home=link('Central de ajuda',{});
 if(q.trim()){
  const found=ordered.filter(d=>matches(d.title+' '+articleText(d,p.links)+' '+(groups.find(g=>g.documents.includes(d))?.name||''),q));
  title='Busca · '+p.name;content='<div class="reader-breadcrumb">'+home+'</div><h1>Resultados da busca</h1><p role="status">'+found.length+' artigo(s) para “'+esc(q.trim())+'”</p>'+(found.length?cards(found):'<div class="reader-empty"><h2>Nenhum artigo encontrado</h2><p>Tente outras palavras ou navegue pelas categorias.</p></div>')+link('Limpar busca',{});
 }else if(article){
  if(!doc){title='Artigo indisponível · '+p.name;content='<div class="reader-breadcrumb">'+home+'</div><h1>Este artigo não está disponível</h1><p>Ele pode ter sido retirado da central. Confira os outros artigos publicados.</p>'+link('Ver todos os artigos',{});}
  else{
   title=doc.title+' · '+p.name;const i=ordered.indexOf(doc),prev=ordered[i-1],next=ordered[i+1],minutes=Math.max(1,Math.ceil(articleText(doc,p.links).split(/\s+/).length/200));
   content='<nav class="reader-breadcrumb" aria-label="Caminho">'+home+'<span aria-hidden="true"> / </span>'+link(group.name||'Artigos',{category:group.id})+'</nav><article class="reader-article"><p class="eyebrow">'+esc(group.name||'ARTIGO')+'</p><h1>'+esc(doc.title)+'</h1><div class="reader-meta"><span>'+minutes+' min de leitura</span><button id="copy-article" type="button">Copiar link do artigo</button></div><p id="copy-status" role="status"></p><input id="article-url" aria-label="Link deste artigo" readonly hidden><div class="reader-body">'+articleBody(p,doc,id)+'</div></article><nav class="reader-pagination" aria-label="Outros artigos">'+(prev?link('← Anterior: '+prev.title,{article:prev.id}):'<span></span>')+(next?link('Próximo: '+next.title+' →',{article:next.id}):'')+'</nav>';
  }
 }else if(category!==null){
  title=(group?.name||'Categoria')+' · '+p.name;content='<div class="reader-breadcrumb">'+home+'</div><h1>'+esc(group?.name|| (group?'Artigos':'Categoria indisponível'))+'</h1>'+(group?'<p class="reader-description">'+group.documents.length+' artigo(s) nesta categoria</p>'+cards(group.documents):'<p>Esta categoria não está mais disponível.</p>'+link('Ver todos os artigos',{}));
 }else{content='<p class="eyebrow">ENCONTRE SUA RESPOSTA</p><h1>Como podemos ajudar?</h1><p class="reader-description">Explore os guias ou use a busca para encontrar o que precisa.</p>'+groups.map(g=>'<section class="reader-group"><div class="reader-group-heading"><h2>'+link(g.name||'Artigos',{category:g.id})+'</h2><span>'+g.documents.length+' artigo(s)</span></div>'+cards(g.documents)+'</section>').join('');}
 return {title,html:'<header class="reader-top"><a data-route class="reader-brand" href="'+href({})+'">'+logoHTML(p)+'<span>'+esc(p.name)+'<small>Central de ajuda</small></span></a><div class="reader-search"><label for="search">Buscar na central</label><input id="search" type="search" maxlength="200" placeholder="Busque artigos, dúvidas ou categorias" value="'+esc(q)+'" autocomplete="off"></div></header><div class="reader-layout">'+sidebar+'<section id="articles" class="reader-content" tabindex="-1">'+content+'</section></div>'};
}
