// Browser edition: portable data and rendering, no network or dependencies.
export const FORMAT = 'knowledge-workspace-browser-1';
export const LIMIT = 8 * 1024 * 1024;
export const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const uid = () => crypto.randomUUID();
const fail = message => { throw new Error(message); };
const required = (test, message) => { if (!test) fail(message); };
const string = (v, max) => typeof v === 'string' && v.length <= max;
export const current = doc => doc.review?.revision === doc.revision;
export function newProject(name) {
  required(string(name,120) && name.trim(), 'Informe um nome com até 120 caracteres.');
  return {id:uid(), name:name.trim(), version:0, createdAt:new Date().toISOString(), documents:[], publications:[]};
}
export function newDocument(title, body='', filename='') {
  required(string(title,160) && title.trim(), 'Informe um título com até 160 caracteres.');
  required(string(body,131072), 'Documento maior que 128 KiB de texto.');
  return {id:uid(), title:title.trim(), body, filename, original:body, revision:1, review:null, history:[]};
}
export function changeDocument(doc, title, body) {
  required(string(title,160) && title.trim() && string(body,131072), 'Confira o título e o limite de texto.');
  if (doc.title===title.trim() && doc.body===body) return false;
  doc.history.push({title:doc.title,body:doc.body,revision:doc.revision,at:new Date().toISOString()});
  doc.title=title.trim(); doc.body=body; doc.revision++; return true;
}
export function reviewDocument(doc,note) {
  required(string(note,2000) && note.trim(), 'Escreva uma nota da conferência.');
  doc.review={revision:doc.revision,note:note.trim(),at:new Date().toISOString()};
}
export function validateProject(p) {
  validateBranding(p?.branding);
  required(p && /^[a-zA-Z0-9-]{1,80}$/.test(p.id) && string(p.name,120) && p.name.trim(), 'Projeto inválido.');
  required(Number.isSafeInteger(p.version) && p.version>=0 && string(p.createdAt,40), 'Versão inválida.');
  required(Array.isArray(p.documents) && p.documents.length<=50 && Array.isArray(p.publications) && p.publications.length<=20, 'Limite: 50 artigos e 20 publicações por projeto.');
  const ids=new Set(), filenames=new Set();
  for (const d of p.documents) {
    required(d && /^[a-zA-Z0-9-]{1,80}$/.test(d.id) && !ids.has(d.id), 'Identificador de artigo inválido ou repetido.'); ids.add(d.id);
    required(string(d.title,160) && d.title.trim() && string(d.body,131072) && string(d.original,131072) && string(d.filename,200), 'Artigo inválido ou muito grande.');
    required(!d.filename || !filenames.has(d.filename.toLowerCase()), 'Nome de arquivo repetido.'); if(d.filename) filenames.add(d.filename.toLowerCase());
    required(Number.isSafeInteger(d.revision) && d.revision>0 && Array.isArray(d.history), 'Histórico inválido.');
    required(d.review===null || (d.review && Number.isSafeInteger(d.review.revision) && d.review.revision>0 && d.review.revision<=d.revision && string(d.review.note,2000) && string(d.review.at,40)), 'Revisão inválida.');
    for(const h of d.history) required(h && string(h.title,160) && string(h.body,131072) && Number.isSafeInteger(h.revision) && h.revision>0 && h.revision<d.revision && string(h.at,40), 'Versão histórica inválida.');
  }
  for (const pub of p.publications) required(pub && /^[a-zA-Z0-9-]{1,80}$/.test(pub.id) && string(pub.at,40) && string(pub.html,2097152) && Number.isSafeInteger(pub.version) && pub.version>=0, 'Publicação inválida.');
  required(new TextEncoder().encode(JSON.stringify(p)).length<=LIMIT, 'Projeto chegou ao limite de 8 MiB. Faça backup e crie outro projeto.');
  return p;
}
export async function checksum(text) { return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))].map(x=>x.toString(16).padStart(2,'0')).join(''); }
export async function makeBackup(projects) {
  const payload=JSON.stringify({projects});
  required(new TextEncoder().encode(payload).length<=LIMIT,'Backup maior que 8 MiB.');
  return JSON.stringify({format:FORMAT,sha256:await checksum(payload),payload},null,2);
}
export async function readBackup(text) {
  required(new TextEncoder().encode(text).length<=LIMIT*2,'Backup muito grande.');
  const envelope=JSON.parse(text);
  required(envelope.format===FORMAT && typeof envelope.payload==='string' && await checksum(envelope.payload)===envelope.sha256,'Formato ou integridade do backup inválidos. Use um backup da edição web.');
  const data=JSON.parse(envelope.payload);
  required(Array.isArray(data.projects) && data.projects.length>0 && data.projects.length<=20,'Backup sem projetos ou acima do limite de 20.');
  const ids=new Set();
  for(const p of data.projects) { validateProject(p); required(!ids.has(p.id),'Projeto repetido no backup.');ids.add(p.id); }
  return data.projects;
}
function inline(text, docs) {
  const tokens=/`([^`\n]+)`|\[([^\]\n]+)\]\(([^)\s]+)\)|\*\*([^*\n]+)\*\*/g;
  let out='', start=0;
  for(const m of text.matchAll(tokens)) {
    out+=escape(text.slice(start,m.index)); start=m.index+m[0].length;
    if(m[1]!==undefined) out+='<code>'+escape(m[1])+'</code>';
    else if(m[4]!==undefined) out+='<strong>'+escape(m[4])+'</strong>';
    else {
      let href=null;
      try { const u=new URL(m[3]); if(u.protocol==='https:' && !u.username && !u.password) href=u.href; } catch {}
      const target=docs.find(d=>d.filename && d.filename.toLowerCase()===m[3].replace(/^\.\//,'').split('#')[0].toLowerCase());
      if(target) href='#article-'+target.id;
      out+=href?'<a href="'+escape(href)+'" rel="noreferrer">'+escape(m[2])+'</a>':escape(m[0]);
    }
  }
  return out+escape(text.slice(start));
}
export function markdown(text,docs=[]) {
  let out='',code=null,list=null;
  const endList=()=>{if(list){out+='</'+list+'>';list=null;}};
  for(const line of text.replace(/\r\n?/g,'\n').split('\n')) {
    if(line.startsWith('```')) {endList();if(code===null)code=[];else{out+='<pre><code>'+escape(code.join('\n'))+'</code></pre>';code=null;}continue;}
    if(code!==null){code.push(line);continue;}
    const h=line.match(/^(#{1,6})\s+(.+)/), li=line.match(/^\s*(?:([-*])|(\d+)\.)\s+(.+)/);
    if(li){const type=li[2]?'ol':'ul';if(list!==type){endList();out+='<'+type+'>';list=type;}out+='<li'+(li[2]?' value="'+Number(li[2])+'"':'')+'>'+inline(li[3],docs)+'</li>';continue;}
    endList();if(h)out+='<h'+Math.min(h[1].length+1,6)+'>'+inline(h[2],docs)+'</h'+Math.min(h[1].length+1,6)+'>';
    else if(line.trim()) out+='<p>'+inline(line,docs)+'</p>';
  }
  endList();if(code!==null)out+='<pre><code>'+escape(code.join('\n'))+'</code></pre>';return out;
}
export function publicHTML(p) {
  required(p.documents.length>0 && p.documents.every(current),'Revise todos os artigos salvos antes de gerar a central.');
  const b=theme(p);
  const links=p.documents.map(d=>'<li><a href="#article-'+d.id+'">'+escape(d.title)+'</a></li>').join('');
  const articles=p.documents.map(d=>'<article id="article-'+d.id+'"><h2>'+escape(d.title)+'</h2>'+markdown(d.body,p.documents)+'</article>').join('');
  // Only explicitly public fields enter this document. No originals, notes or history.
  return '<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>'+escape(p.name)+'</title><style>body{max-width:920px;margin:40px auto;padding:0 24px;font:18px/1.65 system-ui;color:#213d36;background:#fafbf8}h1,h2,h3{line-height:1.2}a{color:#236349}input{font:inherit;padding:12px;width:90%;max-width:500px;border:1px solid #70877b;border-radius:8px}article{border-top:1px solid #b4c4b9;padding:28px 0;overflow-wrap:anywhere}pre{white-space:pre-wrap;background:#e9f0e9;padding:16px}code{overflow-wrap:anywhere}[hidden]{display:none}header{border-top:6px solid '+b.primaryColor+';background:'+b.headerColor+';color:'+b.headerText+';padding:28px;border-radius:16px}header a{color:inherit}.help-logo{max-width:180px;height:80px;object-fit:contain;object-position:left}nav a{background:'+b.primaryColor+';color:'+b.primaryText+';display:inline-block;padding:8px;border-radius:8px}input{background:white;color:black}</style><header>'+logoHTML(p)+'<p>Central de ajuda</p><h1>'+escape(p.name)+'</h1><label for="search">Buscar nesta central</label><br><input id="search" type="search" placeholder="Digite palavras do artigo"><p id="count" role="status"></p><nav aria-label="Artigos"><ul>'+links+'</ul></nav></header><main>'+articles+'</main><footer>Central criada com Knowledge Workspace. Conteúdo revisado pelo operador.</footer><script>const input=document.getElementById("search"),articles=[...document.querySelectorAll("article")],links=[...document.querySelectorAll("nav li")];const norm=s=>s.normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase();input.oninput=()=>{const words=norm(input.value).split(/\\s+/).filter(Boolean);let n=0;articles.forEach((a,i)=>{const show=words.every(w=>norm(a.textContent).includes(w));a.hidden=!show;links[i].hidden=!show;if(show)n++});document.getElementById("count").textContent=n+" artigo(s) encontrado(s)"};<\/script></html>';
}

export const DEFAULT_BRANDING=Object.freeze({primaryColor:'#235e43',headerColor:'#edf3eb',logo:''});
export function validateBranding(b){
 if(b===undefined)return;
 required(b && typeof b==='object' && !Array.isArray(b) && Object.keys(b).every(k=>['primaryColor','headerColor','logo'].includes(k)), 'Aparência inválida.');
 required(/^#[0-9a-f]{6}$/i.test(b.primaryColor) && /^#[0-9a-f]{6}$/i.test(b.headerColor), 'Use cores no formato #RRGGBB.');
 required(typeof b.logo==='string' && b.logo.length<=196608,'Logo muito grande. Use uma imagem mais simples.');
 if(!b.logo)return;
 required(/^data:image\/png;base64,[A-Za-z0-9+/]+={0,2}$/.test(b.logo) && (b.logo.length-22)%4===0,'Use um logo PNG válido.');
 const raw=atob(b.logo.slice(22)),bytes=Uint8Array.from(raw,c=>c.charCodeAt(0));
 required(bytes.length>=33 && [...bytes.slice(0,8)].join(',')==='137,80,78,71,13,10,26,10' && raw.slice(12,16)==='IHDR','Logo PNG inválido.');
 const view=new DataView(bytes.buffer),w=view.getUint32(16),h=view.getUint32(20);
 required(w>0 && h>0 && w<=512 && h<=512,'Logo deve ter até 512 × 512 pixels.');
}
export function contrastText(color){
 const c=color.slice(1).match(/../g).map(x=>parseInt(x,16)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);
 return .2126*c[0]+.7152*c[1]+.0722*c[2]>.179?'#000000':'#ffffff';
}
export function theme(p){validateBranding(p.branding);const b=p.branding||DEFAULT_BRANDING;return {...b,primaryText:contrastText(b.primaryColor),headerText:contrastText(b.headerColor)};}
export function applyAppearance(root,p){const b=theme(p);for(const [key,value] of Object.entries({primary:b.primaryColor,'primary-text':b.primaryText,header:b.headerColor,'header-text':b.headerText}))root.style.setProperty('--help-'+key,value);}
export function logoHTML(p){const b=theme(p);return b.logo?'<img class="help-logo" src="'+escape(b.logo)+'" alt="Logo de '+escape(p.name)+'" width="160" height="80">':'';}
export async function prepareLogo(file){
 if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>2*1024*1024)throw Error('Escolha PNG, JPEG ou WebP de até 2 MiB.');
 const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('Não foi possível ler o arquivo.'));reader.readAsDataURL(file);});try{
  const img=new Image();img.src=data;await img.decode();
  if(img.naturalWidth*img.naturalHeight>16000000)throw Error('Use um logo com até 16 milhões de pixels.');
  const scale=Math.min(1,512/img.naturalWidth,512/img.naturalHeight),canvas=document.createElement('canvas');
  canvas.width=Math.max(1,Math.round(img.naturalWidth*scale));canvas.height=Math.max(1,Math.round(img.naturalHeight*scale));
  canvas.getContext('2d').drawImage(img,0,0,canvas.width,canvas.height);
  const logo=canvas.toDataURL('image/png');validateBranding({...DEFAULT_BRANDING,logo});return logo;
 }catch(e){throw Error(e.message.startsWith('Logo')||e.message.startsWith('Use')?e.message:'Não foi possível ler o logo. Escolha outra imagem.');}
}
