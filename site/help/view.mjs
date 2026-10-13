// Public reader never imports the authenticated store or reads browser session storage.
import {cloudConfig} from '../browser/cloud-config.mjs';
import {escape as esc,applyAppearance} from '../browser/model.mjs';
import {loadPublic} from './reader.mjs';
import {readRoute,helpHref,renderPage} from './pages.mjs';
const root=document.getElementById('reader');
async function open(){
 root.innerHTML='<h1>Abrindo a central…</h1>';
 try{
  const p=await loadPublic(cloudConfig,readRoute(location.href).id);
  function render(focus=false){
   const route=readRoute(location.href),page=renderPage(p,route);document.title=page.title;root.innerHTML=page.html;applyAppearance(root,p);
   const input=document.getElementById('search');
   input.oninput=()=>{history.replaceState(null,'',helpHref(route.id,{q:input.value}));const page=renderPage(p,readRoute(location.href)),template=document.createElement('template');template.innerHTML=page.html;document.title=page.title;document.getElementById('articles').replaceWith(template.content.querySelector('#articles'));root.querySelectorAll('[aria-current]').forEach(a=>a.removeAttribute('aria-current'));};
   const copy=document.getElementById('copy-article');if(copy)copy.onclick=async()=>{const url=new URL(helpHref(route.id,{article:route.article}),location.href).href;const shown=document.getElementById('article-url');shown.hidden=false;shown.value=url;try{await navigator.clipboard.writeText(url);document.getElementById('copy-status').textContent='Link copiado. Pronto para compartilhar.';}catch{const field=document.getElementById('article-url');field.hidden=false;field.value=url;field.select();document.getElementById('copy-status').textContent='Selecione e copie o link abaixo.';}};
   if(focus){document.getElementById('articles').focus({preventScroll:true});window.scrollTo(0,0);}
  }
  root.onclick=e=>{const a=e.target.closest('a');if(!a||e.defaultPrevented||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey||a.target)return;const u=new URL(a.href,location.href);if(u.origin!==location.origin||u.pathname!==location.pathname||u.searchParams.get('id')!==readRoute(location.href).id)return;e.preventDefault();history.pushState(null,'',u.href);render(true);};
  window.onpopstate=()=>render(true);window.onhashchange=()=>render(true);
  render();
 }catch(e){document.title='Central indisponível';root.innerHTML='<p class="eyebrow">CENTRAL DE AJUDA</p><h1>Não foi possível abrir esta central.</h1><p>'+esc(e.message)+'</p><button id="retry">Tentar novamente</button>';document.getElementById('retry').onclick=open;}
}
open();
