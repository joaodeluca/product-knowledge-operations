import {autoSave,sameJSON} from './autosave.mjs';
import {cloudStore} from './cloud.mjs';
import {cloudConfig} from './cloud-config.mjs';
import {escape as esc,uid,newProject,newDocument,changeDocument,reviewDocument,current,markdown,publicHTML,makeBackup,readBackup,validateProject} from './model.mjs';
import {openStore,listProjects,saveProject,restoreCopies} from './storage.mjs';
const $=id=>document.getElementById(id), content=$('content'),dialog=$('dialog');
let localDB, db, project=null, dirty=false, modalAction=null, toastTimer, busy=false, actionBusy=false;
let saver=null, localCount=0, publication=null, publicationReady=false;
const channel=globalThis.BroadcastChannel?new BroadcastChannel('kw-browser-changes'):null;
const date=value=>new Date(value).toLocaleString('pt-BR');
function notify(text){$('status').textContent=text;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('status').textContent='',9000);}
function bind(id,fn){$(id)?.addEventListener('click',()=>run(fn));}
function lock(){const fields=[...document.querySelectorAll('button,input:not([type=file]),textarea')].map(el=>[el,el.disabled]);for(const [el] of fields)el.disabled=true;return ()=>{for(const [el,disabled] of fields)el.disabled=disabled;accountStatus();};}
async function run(fn){if(actionBusy||busy)return;actionBusy=true;const unlock=lock();try{await fn();}catch(e){notify(e.message||'Não foi possível concluir. Preserve seu texto e confira a versão salva.');}finally{unlock();actionBusy=false;}}
const isCloud=()=>db?.mode==='cloud';
const savedWhere=()=>isCloud()?'salvo na sua conta':'salvo neste navegador';
function accountStatus(){
 for(const id of ['projects','backup','restore'])$(id).disabled=!db;
 $('data-location').textContent=isCloud()?'Projetos na sua conta':cloudConfig?'Entre para abrir seus projetos':'Dados neste navegador';
 $('account').hidden=!cloudConfig;$('account').textContent=isCloud()?'☁ Sua conta':'☁ Entrar na conta';
 $('copy-local').hidden=!isCloud()||!localCount;
 $('storage-heading').textContent=isCloud()?'Acesse de outros dispositivos.':(cloudConfig?'Seu espaço, em qualquer dispositivo.':'Sem instalação. Sem conta.');
 $('storage-note').textContent=isCloud()?'Seu login fica salvo neste navegador. As alterações são salvas automaticamente na conta enquanto você escreve.':(cloudConfig?'Entre uma vez para abrir seus projetos e continuar de onde parou.':'Os documentos ficam neste navegador. Faça backup regularmente.');
}
function signedOutView(message=''){
 saver?.stop();saver=null;db=null;project=null;dirty=false;accountStatus();
 content.innerHTML='<section class="panel welcome"><div><p class="eyebrow">SEU WORKSPACE</p><h1>Entre e continue<br>de onde parou.</h1><p class="lead">Seus projetos ficam na sua conta. O login permanece neste navegador e as alterações são salvas automaticamente.</p><button id="start-login">Entrar na minha conta →</button><button id="retry-session" class="secondary">Tentar conexão novamente</button><p role="alert">'+esc(message)+'</p><p class="muted">Use Sair da conta em um dispositivo compartilhado. Não há cadastro público nesta prévia.</p></div></section>';
 bind('start-login',account);bind('retry-session',startCloud);
}
async function startCloud(){
 try{const remote=cloudStore(cloudConfig);const items=await remote.resume();if(!items){signedOutView();return;}db=remote;accountStatus();await projectsView(items);}
 catch(e){signedOutView(e.message);}
}
function account(){
 if(isCloud()&&db.user){modal('Sua conta','<p>'+esc(db.user.email||'Conta conectada')+'</p><p>Seu login permanece neste navegador. Sair remove o login salvo deste navegador; os projetos continuam na conta.</p>','Sair da conta',async()=>{const previous=db;try{await previous.signOut();}finally{signedOutView();}});return;}
 modal('Entrar na sua conta','<p>Entre uma vez. Seu login fica salvo neste navegador; os projetos e as alterações vão para sua conta automaticamente. Sua senha não será guardada pelo Workspace.</p><label for="account-email">E-mail</label><input id="account-email" type="email" autocomplete="username" required><label for="account-password">Senha</label><input id="account-password" type="password" autocomplete="current-password" required><p class="muted">Use Sair da conta em dispositivos compartilhados. Acesso e recuperação de senha são administrados pelo titular.</p>','Entrar',async()=>{const remote=cloudStore(cloudConfig);const items=await remote.signIn($('account-email').value,$('account-password').value);$('account-password').value='';notify('');db=remote;project=null;dirty=false;accountStatus();await projectsView(items);});
}

function modal(title,body,label,action,wide=false){
  modalAction=action;dialog.classList.toggle('wide',wide);$('dialog-content').innerHTML='<h2>'+esc(title)+'</h2>'+body+'<p id="dialog-error" role="alert"></p>';$('confirm').textContent=label;$('confirm').hidden=!action;$('cancel').textContent=action?'Cancelar':'Fechar';dialog.showModal();
}
$('cancel').onclick=()=>{if(!busy)dialog.close();};
dialog.addEventListener('cancel',e=>{if(busy)e.preventDefault();});
$('dialog-form').onsubmit=async e=>{e.preventDefault();if(busy||!modalAction)return;busy=true;const unlock=lock();try{await modalAction();dialog.close();}catch(error){$('dialog-error').textContent=error.message;}finally{unlock();busy=false;}};
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
channel?.addEventListener('message',e=>{if(project?.id===e.data)notify('Este projeto foi alterado em outra aba. Volte a Projetos e reabra antes de salvar.');});
function download(text,name,type){const url=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),60000);}
async function leave(fn){
 if(dirty&&saver){try{await saver.flush();}catch{modal('Há alterações não salvas','<p>O texto continua no editor. Cancele para baixar seu rascunho ou resolver o salvamento antes de sair.</p>','Descartar rascunho e sair',async()=>{saver.stop();saver=null;dirty=false;dialog.addEventListener('close',()=>setTimeout(()=>run(fn),0),{once:true});});return;}}
 return fn();
}
async function commit(mutator){const base=project,store=db,next=structuredClone(base);await mutator(next);validateProject(next);const saved=await saveProject(store,next,base.version);if(db!==store||project!==base)throw Error('O projeto ativo mudou. Reabra para conferir a versão salva.');project=saved;channel?.postMessage(project.id);}
async function projectsView(items){
  if(!Array.isArray(items))items=await listProjects(db);saver?.stop();saver=null;project=null;dirty=false;
  content.innerHTML='<p class="eyebrow">KNOWLEDGE WORKSPACE</p><div class="page-head"><div><h1>Seu conhecimento,<br>pronto para compartilhar.</h1><p class="lead">Transforme documentos em uma central de ajuda. Confira cada artigo e mantenha a história do que mudou.</p></div><button id="create">+ Novo projeto</button></div>'+
    (items.length?'<h2>Seus projetos <span class="pill">'+items.length+'</span></h2><div class="cards">'+items.map(p=>'<section class="panel card"><span class="eyebrow">CENTRAL DE AJUDA</span><h2>'+esc(p.name)+'</h2><p>'+p.documents.length+' artigos · '+p.documents.filter(current).length+' revisados</p><p>'+p.publications.length+' downloads HTML preservados</p><button class="secondary" data-open="'+esc(p.id)+'">Abrir projeto →</button></section>').join('')+'</div>':'<section class="panel welcome"><div><p class="eyebrow">DA PRIMEIRA NOTA À CENTRAL</p><h2>Um lugar para escrever.<br>Um jeito de manter em dia.</h2><p class="lead">Comece com seus próprios arquivos ou escreva o primeiro artigo aqui.</p><button id="create-empty">Criar meu primeiro projeto →</button></div><ol><li>Traga seus documentos Markdown ou texto.</li><li>Edite e confira a prévia de cada artigo.</li><li>Revise, publique e copie o link da central.</li><li>Continue em outro dispositivo com a mesma conta.</li></ol></section>')+
    (isCloud()?'<div class="notice"><strong>Projetos privados na sua conta.</strong> Entre na mesma conta em outro dispositivo para continuar. As alterações são salvas automaticamente. Aguarde “Salvo na sua conta” antes de fechar; sem conexão, o editor avisa e preserva o rascunho na aba. Backups continuam disponíveis.</div>':'<div class="notice"><strong>Seu trabalho fica neste navegador.</strong> Faça backup regularmente. Limpar os dados do site pode apagar estes projetos. A edição Python usa outro formato de backup.</div>');
  const create=()=>modal('Novo projeto','<p>Este nome aparecerá na central pública.</p><label for="project-name">Nome da central</label><input id="project-name" maxlength="120" required placeholder="Ex.: Ajuda do meu produto">','Criar projeto',async()=>{
    if((await listProjects(db)).length>=20)throw new Error('Limite de 20 projetos neste espaço.');
    project=await saveProject(db,newProject($('project-name').value),null);projectView();
  });
  bind('create',create);bind('create-empty',create);
  content.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>run(async()=>{project=(await listProjects(db)).find(p=>p.id===b.dataset.open);if(!project)throw new Error('Projeto não encontrado.');projectView();}));
}
function projectView(){
  saver?.stop();saver=null;dirty=false;publication=null;publicationReady=false;const count=project.documents.filter(current).length;
  content.innerHTML='<button id="back" class="secondary small">← Projetos</button><p class="eyebrow">CENTRAL DE AJUDA</p><div class="page-head"><div><h1>'+esc(project.name)+'</h1><p class="lead">'+project.documents.length+' artigos · '+count+' revisados · '+savedWhere()+'</p></div><button id="publish" '+(!project.documents.length||count!==project.documents.length?'disabled':'')+'>'+(isCloud()?'Publicar central →':'Gerar central ↓')+'</button></div><div class="steps"><span><b>01</b> Importar ou escrever</span><span><b>02</b> Conferir cada artigo</span><span><b>03</b> Publicar e compartilhar</span></div><div class="actions"><button id="import">↑ Importar documentos</button><button id="write" class="secondary">+ Escrever artigo</button><button id="review-next" class="secondary" '+(count===project.documents.length?'disabled':'')+'>Revisar próximo artigo →</button></div>'+
    (project.documents.length?'<section class="panel"><h2>Documentos</h2>'+project.documents.map(d=>'<div class="doc-row"><div><h3>'+esc(d.title)+'</h3><p class="muted">'+esc(d.filename||'Escrito no Workspace')+' · versão '+d.revision+'</p></div><span class="pill '+(current(d)?'':'pending')+'">'+(current(d)?'Revisado':d.review?'Revisão vencida':'Revisão pendente')+'</span><div class="actions"><button class="secondary small" data-edit="'+d.id+'">Editar</button><button class="secondary small" data-review="'+d.id+'">Conferir</button></div></div>').join('')+'</section>':'<div class="empty"><h2>A sua central começa aqui.</h2><p class="muted">Importe arquivos .md ou .txt, ou escreva um artigo. Tudo começa como rascunho.</p></div>')+
    (isCloud()?'<section id="publication-status" class="panel"><h2>Link da sua central</h2><p>Conferindo a publicação…</p></section>':'')+'<section class="panel"><h2>Downloads preservados</h2><button id="export-html" class="secondary small" '+(!project.documents.length||count!==project.documents.length?'disabled':'')+'>Baixar HTML (opcional)</button><p class="muted">Editar um artigo vence sua revisão. Uma central já gerada continua disponível exatamente como foi salva.</p>'+project.publications.slice().reverse().map(pub=>'<div class="doc-row"><div><h3>Central · '+esc(date(pub.at))+'</h3><p class="muted">Versão do projeto '+pub.version+'</p></div><button class="secondary small" data-download="'+pub.id+'">Baixar HTML</button></div>').join('')+(project.publications.length?'':'<p class="muted">Revise todos os artigos para gerar a primeira central.</p>')+'</section>';
  bind('back',projectsView);bind('import',()=>{$('import-files').value='';$('import-files').click();});bind('write',()=>editor(null));bind('publish',isCloud()?publishLink:exportHTML);bind('export-html',exportHTML);if(isCloud()){$('publish').disabled=true;loadPublication();}
  bind('review-next',()=>review(project.documents.find(d=>!current(d)).id,true));
  content.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>editor(b.dataset.edit));
  content.querySelectorAll('[data-review]').forEach(b=>b.onclick=()=>review(b.dataset.review,false));
  content.querySelectorAll('[data-download]').forEach(b=>b.onclick=()=>download(project.publications.find(p=>p.id===b.dataset.download).html,'central-'+b.dataset.download+'.html','text/html;charset=utf-8'));
}
function editor(id){
 saver?.stop();const doc=project.documents.find(d=>d.id===id);dirty=false;
 let target=id||uid(),uncertain=null;
 const history=()=>{const d=project.documents.find(d=>d.id===target);return d?'<details><summary>Original importado e histórico privado ('+d.history.length+')</summary><h3>Texto original</h3><pre class="history-text">'+esc(d.original)+'</pre>'+d.history.slice().reverse().map(h=>'<h3>Versão '+h.revision+' · '+esc(date(h.at))+'</h3><strong>'+esc(h.title)+'</strong><pre class="history-text">'+esc(h.body)+'</pre>').join('')+'</details>':'';};
 content.innerHTML='<button id="back-project" class="secondary small">← Central</button><div class="page-head"><div><p id="article-version" class="eyebrow">'+(doc?'VERSÃO '+doc.revision:'NOVO ARTIGO')+'</p><h1>'+(doc?'Editar artigo':'Escreva seu primeiro rascunho')+'</h1></div><div class="actions"><span id="save-state" class="save-state" role="status">'+(doc?(isCloud()?'Salvo na sua conta':'Salvo neste navegador'):'Comece a escrever · salvamento automático')+'</span><button id="save" class="secondary">Salvar agora</button></div></div><div id="save-error" role="alert" class="notice" hidden></div><button id="download-draft" class="secondary" hidden>Baixar rascunho para guardar</button><div class="editor"><section><label for="title">Título público</label><input id="title" maxlength="160" value="'+esc(doc?.title||'')+'"><label for="body">Conteúdo público · Markdown ou texto</label><textarea id="body" spellcheck="true">'+esc(doc?.body||'')+'</textarea><p class="muted">Salvamos após uma pausa na digitação. Títulos, listas, negrito, código e links HTTPS. HTML aparece como texto; imagens e anexos não são importados.</p></section><section><label>Prévia do leitor</label><div id="preview" class="preview"></div></section></div><div id="article-history">'+history()+'</div>';
 const read=()=>({title:$('title').value,body:$('body').value});
 const preview=()=>{$('preview').innerHTML='<h2>'+esc($('title').value||'Título do artigo')+'</h2>'+markdown($('body').value,project.documents);};preview();
 saver=autoSave({read,write:async({title,body})=>{
   const store=db;
   // Resolve an uncertain acknowledgement before sending anything else.
   if(uncertain){
     const actual=(await listProjects(store)).find(p=>p.id===project.id);
     if(actual&&sameJSON(actual,{...uncertain.next,version:uncertain.base.version+1}))project=actual;
     else if(!actual||actual.version!==uncertain.base.version)throw Error('Este projeto mudou em outro dispositivo. Baixe seu rascunho e reabra a versão atual; nada foi sobrescrito.');
     uncertain=null;
   }
   const old=project.documents.find(d=>d.id===target);
   if(old&&old.title===title.trim()&&old.body===body)return;
   const base=project,next=structuredClone(base);
   try{if(old)changeDocument(next.documents.find(d=>d.id===target),title,body);
   else{const d=newDocument(title,body);d.id=target;next.documents.push(d);}
   validateProject(next);}catch(e){e.retryOnChange=true;throw e;}uncertain={base,next};
   const saved=await saveProject(store,next,base.version);
   if(db!==store)throw Error('A conta mudou. Preserve seu rascunho antes de continuar.');
   project=saved;uncertain=null;channel?.postMessage(project.id);
 },onState:(state,error)=>{
   dirty=state!=='saved';
   $('save-state').textContent={pending:'Alterações pendentes…',saving:isCloud()?'Salvando na sua conta…':'Salvando…',saved:isCloud()?'Salvo na sua conta':'Salvo neste navegador',error:'Não foi possível salvar'}[state];
   $('save-error').hidden=state!=='error';$('download-draft').hidden=state!=='error';
   if(error)$('save-error').textContent=error.message+' Seu texto continua nesta aba.';
   $('save').textContent=state==='error'?'Tentar salvar novamente':'Salvar agora';
   if(state==='saved'){const d=project.documents.find(d=>d.id===target);$('article-version').textContent=d?'VERSÃO '+d.revision:'NOVO ARTIGO';$('article-history').innerHTML=history();}
 }});
 for(const key of ['title','body'])$(key).oninput=()=>{dirty=true;preview();saver.change();};
 bind('back-project',()=>leave(async()=>{const id=project.id;project=(await listProjects(db)).find(p=>p.id===id);if(!project)throw Error('Projeto não encontrado.');projectView();}));
 bind('save',()=>saver.retry());
 bind('download-draft',()=>download('# '+$('title').value+'\n\n'+$('body').value,'rascunho-workspace.md','text/markdown;charset=utf-8'));
}

function review(id,queue){
  const doc=project.documents.find(d=>d.id===id);
  modal('Conferir: '+doc.title,'<p class="muted">Versão '+doc.revision+' · '+(current(doc)?'Esta versão já foi revisada.':'A leitura e a veracidade do conteúdo são responsabilidade do operador.')+'</p><div class="preview">'+markdown(doc.body,project.documents)+'</div><label for="review-note">Nota da conferência (privada)</label><textarea id="review-note" maxlength="2000" class="short-text" required placeholder="O que você conferiu e quais limites permanecem?"></textarea><label class="check"><input id="review-check" type="checkbox" required>Conferi este artigo e seus limites. Esta é uma revisão declarada, não uma certificação independente.</label>',queue?'Registrar e continuar':'Registrar revisão',async()=>{
    if(!$('review-check').checked)throw new Error('Confirme a conferência individual.');
    const note=$('review-note').value;await commit(p=>reviewDocument(p.documents.find(d=>d.id===id),note));projectView();
    const next=queue&&project.documents.find(d=>!current(d));if(next)setTimeout(()=>review(next.id,true),0);else notify('Revisão salva para esta versão.');
  },true);
}
function helpURL(meta){const url=new URL('../help/',location.href);url.searchParams.set('id',meta.public_id);return url.href;}
async function loadPublication(){
 const id=project.id,store=db;
 try{const meta=await store.helpStatus(id);if(db!==store||project?.id!==id||!$('publication-status'))return;publication=meta;publicationReady=true;
  const canPublish=project.documents.length&&project.documents.every(current);
  $('publish').disabled=!canPublish;$('publish').textContent=meta?.live?'Atualizar publicação →':'Publicar central →';
  const newer=meta&&meta.source_version!==project.version;
  $('publication-status').innerHTML='<h2>'+(meta?.live?'Sua central está publicada':meta?'Central fora do ar':'Compartilhe sua central')+'</h2>'+
   (meta?.live?'<p>Publicado em '+esc(date(meta.published_at))+'. '+(newer?'Há alterações privadas posteriores. O link mantém a versão publicada até você atualizar.':'O link mostra a versão publicada.')+'</p>':'<p>'+(meta?'O link está desativado. Publique novamente para usar o mesmo endereço.':'Revise os artigos e publique para receber um link. Quem tiver o link poderá ler sem entrar no Workspace.')+'</p>')+
   (meta?'<label for="public-link">Link direto</label><input id="public-link" readonly value="'+esc(helpURL(meta))+'"><div class="actions"><button id="copy-link" class="secondary">Copiar link</button>'+(meta.live?'<a class="secondary" href="'+esc(helpURL(meta))+'" target="_blank" rel="noopener noreferrer">Abrir central ↗</a><button id="unpublish" class="secondary">Retirar do ar</button>':'')+'</div>':'')+
   '<p class="muted">Originais, histórico e notas de revisão continuam privados. A publicação exige uma confirmação, mesmo com o salvamento automático ligado.</p>';
  bind('copy-link',async()=>{try{await navigator.clipboard.writeText(helpURL(publication));notify('Link copiado. Pronto para compartilhar.');}catch{$('public-link').select();notify('Selecione e copie o link exibido.');}});
  bind('unpublish',()=>modal('Retirar a central do ar','<p>Novas aberturas deste link deixarão de mostrar a central. Seus projetos e versões serão preservados; você poderá publicar novamente no mesmo link. Cópias já feitas por leitores não podem ser revogadas.</p>','Retirar do ar',async()=>{await db.unpublishHelp(project.id,publication.revision);projectView();notify('Central retirada do ar.');}));
 }catch(e){if(db!==store||project?.id!==id||!$('publication-status'))return;publicationReady=false;$('publish').disabled=true;$('publication-status').innerHTML='<h2>Não foi possível conferir a publicação</h2><p>'+esc(e.message)+'</p><button id="retry-publication">Tentar novamente</button>';bind('retry-publication',loadPublication);}
}
async function publishLink(){
 if(!publicationReady)throw Error('Aguarde a conferência da publicação.');
 const selected=project,previous=publication;publicHTML(selected);
 const preview='<div class="preview publication-preview" aria-label="Prévia da central pública"><h1>'+esc(selected.name)+'</h1>'+selected.documents.map(d=>'<article><h2>'+esc(d.title)+'</h2>'+markdown(d.body,selected.documents)+'</article>').join('')+'</div>';
 modal(previous?.live?'Atualizar a central publicada':'Publicar sua central','<p>Quem tiver o link poderá ler <strong>'+esc(selected.name)+'</strong> e seus '+selected.documents.length+' artigos revisados, sem login. Originais, histórico e notas privadas não serão publicados.</p><p>'+(previous?'O endereço continua o mesmo. Somente esta versão conferida será mostrada.':'O Workspace cria e hospeda o link para você.')+'</p>'+preview+'<label class="check"><input id="publish-check" type="checkbox" required>Conferi a prévia e autorizo publicar estes títulos e textos na internet.</label>',previous?.live?'Atualizar publicação':'Publicar e obter link',async()=>{
  if(!$('publish-check').checked)throw Error('Confira e confirme os campos públicos.');
  if(project!==selected)throw Error('O projeto mudou. Feche e confira a prévia novamente.');
  try{await db.publishHelp(selected.id,selected.version,previous?.revision??0);}catch(e){throw Error(e.message+' Feche esta janela e confira a publicação antes de repetir.');}
  projectView();notify('Central publicada. Copie o link para compartilhar.');
 },true);
}
async function exportHTML(){
  const html=publicHTML(project);const url=URL.createObjectURL(new Blob([html.replace(/<script>[\s\S]*?<\/script>/g,'')],{type:'text/html'}));
  modal('Gerar a central pública','<p>Prévia de leitura; a busca funciona no arquivo baixado. Serão incluídos o nome do projeto e '+project.documents.length+' artigos revisados. Originais, histórico e notas de revisão ficam fora do arquivo.</p><iframe id="reader-preview" sandbox="" title="Prévia da central pública"></iframe><label class="check"><input id="publish-check" type="checkbox" required>Conferi a prévia e os campos públicos. O arquivo poderá ser compartilhado.</label>','Gerar e baixar HTML',async()=>{
    if(!$('publish-check').checked)throw new Error('Confira a prévia antes de gerar.');
    const pub={id:uid(),at:new Date().toISOString(),version:project.version,html};
    await commit(p=>{publicHTML(p);p.publications.push(pub);});download(html,'central-'+pub.id+'.html','text/html;charset=utf-8');projectView();notify('Central salva e download iniciado. Guarde também um backup privado.');
  },true);$('reader-preview').src=url;dialog.addEventListener('close',()=>URL.revokeObjectURL(url),{once:true});
}
$('import-files').onchange=()=>run(async()=>{
  const files=[...$('import-files').files];if(!files.length)return;
  const importingProject=project;
  if(files.length>32 || files.reduce((s,f)=>s+f.size,0)>524288)throw new Error('Importe até 32 arquivos, total de 512 KiB por lote.');
  const names=new Set(project.documents.map(d=>d.filename.toLowerCase()).filter(Boolean)),docs=[];
  for(const file of files){
    if(!/\.(md|markdown|txt)$/i.test(file.name)||file.size>131072||file.name.length>200)throw new Error('Use Markdown ou texto, até 128 KiB por arquivo e nome até 200 caracteres.');
    if(names.has(file.name.toLowerCase()))throw new Error('Arquivo repetido: '+file.name+'. Edite o artigo existente ou renomeie o novo arquivo.');names.add(file.name.toLowerCase());
    const text=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());if(text.includes('\0'))throw new Error('Arquivo contém dados binários: '+file.name);
    const heading=text.match(/^#\s+([^\r\n]+)(?:\r?\n|$)/);const title=(heading?.[1]||file.name.replace(/\.[^.]+$/,'')).trim();
    const d=newDocument(title,heading?text.slice(heading[0].length).trimStart():text,file.name);d.original=text;docs.push(d);
  }
  if(project!==importingProject)throw new Error('O projeto mudou durante a leitura. Importe os arquivos novamente no projeto desejado.');
  modal('Conferir importação','<p>'+docs.length+' artigos serão criados sem revisão. Os originais serão guardados no histórico privado.</p>'+docs.map(d=>'<details><summary>'+esc(d.filename)+' → '+esc(d.title)+'</summary><div class="preview">'+markdown(d.body,[...project.documents,...docs])+'</div></details>').join('')+'<p class="muted">HTML é mostrado como texto. Imagens e anexos não são carregados. Links locais sem artigo correspondente permanecem como texto.</p>','Importar artigos',async()=>{if(project!==importingProject)throw new Error('O projeto mudou. Cancele e importe novamente.');await commit(p=>p.documents.push(...docs));projectView();notify('Documentos importados. Confira cada artigo antes de publicar.');});
});
bind('projects',()=>leave(projectsView));
bind('account',()=>leave(account));
bind('copy-local',()=>leave(async()=>{
 const items=await listProjects(localDB);if(!items.length)throw Error('Não há projetos locais neste navegador para copiar.');
 const remote=db;if(!isCloud())throw Error('Entre na conta primeiro.');
 modal('Copiar projetos locais para a conta','<p>Serão enviadas '+items.length+' cópias completas para sua conta: documentos, originais, histórico, notas privadas e publicações. Os projetos locais serão mantidos.</p><ul>'+items.map(p=>'<li>'+esc(p.name)+'</li>').join('')+'</ul><p>As cópias recebem o sufixo “recuperado”. Confira os dados e a conta antes de enviar.</p>','Copiar para minha conta',async()=>{if(db!==remote)throw Error('A conta mudou. Cancele e confira novamente.');await restoreCopies(remote,items);await projectsView();notify('Cópias salvas na conta. Os projetos locais foram preservados.');});
}));
bind('backup',()=>leave(async()=>{
  const items=await listProjects(db);if(!items.length)throw new Error('Crie um projeto antes de fazer backup.');
  modal('Backup privado','<p>Este arquivo guarda os projetos salvos no espaço aberto: originais, artigos, histórico, notas e downloads HTML. Ele não é a central pública. Links e versões hospedadas não entram neste backup; cópias recuperadas precisam ser publicadas novamente.</p><p>Guarde em local sob seu controle. O arquivo baixado não tem criptografia. Compatível com esta edição web; separado do backup ZIP da versão Python.</p>','Baixar backup privado',async()=>{const data=await makeBackup(await listProjects(db));download(data,'workspace-web-backup-'+new Date().toISOString().slice(0,10)+'.json','application/json');notify('Download do backup iniciado. Confira o arquivo na sua pasta de downloads.');});
}));
bind('restore',()=>leave(()=>{$('restore-file').value='';$('restore-file').click();}));
$('restore-file').onchange=()=>run(async()=>{
  const f=$('restore-file').files[0];if(!f)return;if(f.size>16*1024*1024)throw new Error('Backup maior que 16 MiB.');
  const copies=await readBackup(await f.text());
  modal('Recuperar em novos projetos','<p>Integridade conferida. Serão criadas '+copies.length+' cópias, com o sufixo “recuperado”. Os projetos existentes serão preservados.</p><ul>'+copies.map(p=>'<li>'+esc(p.name)+' · '+p.documents.length+' artigos</li>').join('')+'</ul><p class="notice">Use apenas backups próprios confiáveis. O checksum detecta corrupção, mas não autentica a autoria. Revisões declaradas e publicações do backup serão preservadas.</p>','Recuperar cópias',async()=>{await restoreCopies(db,copies);await projectsView();notify('Cópias recuperadas. Os projetos anteriores foram preservados.');});
});
accountStatus();
try{localDB=await openStore();localCount=(await listProjects(localDB)).length;localDB.onversionchange=()=>localDB.close();}catch{}
if(cloudConfig)await startCloud();
else if(localDB){db=localDB;accountStatus();await projectsView();}
else content.innerHTML='<h1>Armazenamento indisponível.</h1><p>Permita o armazenamento deste site e tente novamente.</p>';
window.addEventListener('storage',e=>{if(isCloud()&&e.key===db.sessionKey){let nextUser;try{nextUser=JSON.parse(e.newValue)?.user?.id;}catch{}if(nextUser===db.user?.id)return;if(dirty)notify('O login mudou em outra aba. Preserve seu rascunho antes de continuar.');else startCloud();}});
