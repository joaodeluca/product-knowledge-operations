// Portable visual document, stored in the existing versioned body field.
export const RICH_PREFIX='::knowledge-workspace-visual-1::\n';
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const check=(ok,message='Conteúdo visual inválido.')=>{if(!ok)throw Error(message);};
export function safeLink(value){try{const u=new URL(value);return u.protocol==='https:'&&!u.username&&!u.password?u.href:null;}catch{return /^#article-[a-zA-Z0-9-]{1,80}$/.test(value||'')?value:null;}}
export const safeImage=src=>typeof src==='string'&&src.length<=65536&&/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/]+={0,2}$/.test(src);
export function normalizeRich(root){
 let count=0;
 const walk=(n,depth=0)=>{
  check(n&&typeof n==='object'&&!Array.isArray(n)&&depth<=16&&++count<=5000);
  const type=n.type;check(['doc','paragraph','heading','text','bulletList','orderedList','listItem','blockquote','codeBlock','hardBreak','horizontalRule','image'].includes(type));
  const out={type};
  if(type==='text'){
   check(typeof n.text==='string');out.text=n.text;
   if(n.marks?.length){check(Array.isArray(n.marks)&&n.marks.length<=6);out.marks=n.marks.map(m=>{check(m&&['bold','italic','strike','underline','code','link'].includes(m.type));if(m.type==='link'){const href=safeLink(m.attrs?.href);check(href,'Use um link HTTPS válido.');return {type:'link',attrs:{href}};}return {type:m.type};});}
  }else if(type==='image'){
   check(safeImage(n.attrs?.src),'A imagem precisa ser enviada pelo botão Imagem (até 64 KiB após ajuste).');const alt=n.attrs?.alt||'';check(typeof alt==='string'&&alt.length<=240);out.attrs={src:n.attrs.src,alt};
  }else if(type==='heading'){check([2,3,4,5,6].includes(n.attrs?.level));out.attrs={level:n.attrs.level};}
  else if(type==='orderedList'){const start=n.attrs?.start??1;check(Number.isSafeInteger(start)&&start>=1&&start<=100000);out.attrs={start};}
  if(n.content!==undefined){check(Array.isArray(n.content)&&!['text','image','hardBreak','horizontalRule'].includes(type));out.content=n.content.map(c=>walk(c,depth+1));
   const blocks=['paragraph','heading','bulletList','orderedList','blockquote','codeBlock','horizontalRule','image'];
   const allowed=type==='doc'||type==='blockquote'||type==='listItem'?blocks:type==='bulletList'||type==='orderedList'?['listItem']:type==='codeBlock'?['text']:['text','hardBreak'];
   check(out.content.every(c=>allowed.includes(c.type)));}
  return out;
 };
 check(root?.type==='doc');return walk(root);
}
export function encodeRich(json){const text=RICH_PREFIX+JSON.stringify(normalizeRich(json));check(text.length<=131072,'Este artigo chegou ao limite de 128 KiB. Remova uma imagem ou divida o conteúdo em outro artigo.');return text;}
export function decodeRich(body){if(!body.startsWith(RICH_PREFIX))return null;return normalizeRich(JSON.parse(body.slice(RICH_PREFIX.length)));}
export function renderRich(body){
 const root=decodeRich(body);if(!root)return null;
 const render=n=>{
  if(n.type==='text'){let text=esc(n.text);for(const m of n.marks||[]){if(m.type==='link')text='<a href="'+esc(m.attrs.href)+'" rel="noreferrer">'+text+'</a>';else{const tag={bold:'strong',italic:'em',strike:'s',underline:'u',code:'code'}[m.type];text='<'+tag+'>'+text+'</'+tag+'>';}}return text;}
  if(n.type==='image')return '<img class="article-image" src="'+n.attrs.src+'" alt="'+esc(n.attrs.alt)+'" loading="lazy">';
  if(n.type==='hardBreak')return '<br>';if(n.type==='horizontalRule')return '<hr>';
  const inner=(n.content||[]).map(render).join('');if(n.type==='doc')return inner;
  const tag={paragraph:'p',heading:'h'+n.attrs?.level,bulletList:'ul',orderedList:'ol',listItem:'li',blockquote:'blockquote',codeBlock:'pre'}[n.type];
  return '<'+tag+(n.type==='orderedList'?' start="'+n.attrs.start+'"':'')+'>'+(n.type==='codeBlock'?'<code>'+inner+'</code>':inner)+'</'+tag+'>';
 };return render(root);
}
export async function prepareArticleImage(file){
 check(file&&['image/png','image/jpeg','image/webp'].includes(file.type)&&file.size<=4*1024*1024,'Escolha PNG, JPEG ou WebP de até 4 MiB.');
 const source=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=()=>reject(Error('Não foi possível ler a imagem.'));r.readAsDataURL(file);});
 const img=new Image();img.src=source;await img.decode();check(img.naturalWidth*img.naturalHeight<=24000000,'A imagem deve ter até 24 megapixels.');
 const canvas=document.createElement('canvas');let width=Math.min(1200,img.naturalWidth);
 for(let i=0;i<7;i++){
  canvas.width=width;canvas.height=Math.max(1,Math.round(img.naturalHeight*width/img.naturalWidth));const ctx=canvas.getContext('2d');ctx.drawImage(img,0,0,canvas.width,canvas.height);
  const src=canvas.toDataURL('image/webp',.78);if(src.length<=49152&&safeImage(src))return src;width=Math.round(width*.75);
 }
 throw Error('Não foi possível ajustar a imagem. Escolha uma imagem menor.');
}
