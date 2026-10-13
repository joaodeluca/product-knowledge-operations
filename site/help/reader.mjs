import {escape as esc,markdown} from '../browser/model.mjs';
export const validPublicId=id=>typeof id==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id);
export async function loadPublic(config,id,fetcher=globalThis.fetch){
 if(!validPublicId(id))throw Error('Link inválido. Confira o endereço recebido.');
 if(!config)throw Error('Publicação indisponível neste momento.');
 let response;
 try{response=await fetcher(config.url+'/rest/v1/rpc/kw_read_help',{method:'POST',headers:{apikey:config.publishableKey,'Content-Type':'application/json'},body:JSON.stringify({p_public_id:id}),credentials:'omit',cache:'no-store',redirect:'error',signal:AbortSignal.timeout(20000)});}
 catch{throw Error('Não foi possível conectar. Confira sua conexão e tente novamente.');}
 if(response.status===404)throw Error('Esta central não está disponível. Ela pode ter sido retirada do ar.');
 if(!response.ok)throw Error('Não foi possível abrir a central. Tente novamente mais tarde.');
 const p=await response.json();
 if(typeof p?.name!=='string'||!Array.isArray(p.documents)||!p.documents.length||p.documents.length>50||!Array.isArray(p.links)||p.links.length>50)throw Error('Publicação inválida.');
 const ids=new Set();for(const d of p.documents){if(!d||typeof d.id!=='string'||!/^[a-zA-Z0-9-]{1,80}$/.test(d.id)||ids.has(d.id)||typeof d.title!=='string'||typeof d.body!=='string')throw Error('Publicação inválida.');ids.add(d.id);}
 for(const l of p.links)if(!ids.has(l.id)||typeof l.filename!=='string')throw Error('Publicação inválida.');
 return p;
}
export function renderPublic(p){
 return '<header><p class="eyebrow">CENTRAL DE AJUDA</p><h1>'+esc(p.name)+'</h1><p class="muted">Versão publicada · '+esc(new Date(p.published_at).toLocaleDateString('pt-BR'))+'</p><label for="search">O que você procura?</label><input id="search" type="search" placeholder="Buscar nos artigos" autocomplete="off"><p id="results" role="status"></p><nav aria-label="Artigos"><ul>'+p.documents.map(d=>'<li data-link="'+esc(d.id)+'"><a href="#article-'+esc(d.id)+'">'+esc(d.title)+'</a></li>').join('')+'</ul></nav></header><section id="articles">'+p.documents.map(d=>'<article id="article-'+esc(d.id)+'"><h2>'+esc(d.title)+'</h2>'+markdown(d.body,p.links)+'</article>').join('')+'</section><p id="empty" hidden>Nenhum artigo encontrado. Tente outra palavra.</p>';
}
export const matches=(text,query)=>{
 const norm=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 return norm(query).split(/\s+/).filter(Boolean).every(word=>norm(text).includes(word));
};
