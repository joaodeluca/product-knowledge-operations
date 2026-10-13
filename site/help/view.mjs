// Public reader never imports the authenticated store or reads browser session storage.
import {cloudConfig} from '../browser/cloud-config.mjs';
import {escape as esc} from '../browser/model.mjs';
import {loadPublic,renderPublic,matches} from './reader.mjs';
const root=document.getElementById('reader');
async function open(){
 root.innerHTML='<h1>Abrindo a central…</h1>';
 try{
  const p=await loadPublic(cloudConfig,new URL(location.href).searchParams.get('id'));
  document.title=p.name+' · Central de ajuda';root.innerHTML=renderPublic(p);
  const input=document.getElementById('search'),articles=[...root.querySelectorAll('article')],links=[...root.querySelectorAll('[data-link]')];
  input.oninput=()=>{let count=0;articles.forEach((a,i)=>{const show=matches(a.textContent,input.value);a.hidden=!show;links[i].hidden=!show;if(show)count++;});document.getElementById('results').textContent=count+' artigo(s) encontrado(s)';document.getElementById('empty').hidden=count>0;};
  const anchor=document.getElementById(location.hash.slice(1));if(anchor?.tagName==='ARTICLE')anchor.scrollIntoView();
 }catch(e){document.title='Central indisponível';root.innerHTML='<p class="eyebrow">CENTRAL DE AJUDA</p><h1>Não foi possível abrir esta central.</h1><p>'+esc(e.message)+'</p><button id="retry">Tentar novamente</button>';document.getElementById('retry').onclick=open;}
}
open();
