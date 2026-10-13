import {escape as esc,uid,newProject,newDocument,changeDocument,reviewDocument,current,markdown,publicHTML,makeBackup,readBackup,validateProject} from './model.mjs';
import {openStore,listProjects,saveProject,restoreCopies} from './storage.mjs';
const $=id=>document.getElementById(id), content=$('content'),dialog=$('dialog');
let db, project=null, dirty=false, modalAction=null, toastTimer, busy=false;
const channel=globalThis.BroadcastChannel?new BroadcastChannel('kw-browser-changes'):null;
const date=value=>new Date(value).toLocaleString('pt-BR');
function notify(text){$('status').textContent=text;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('status').textContent='',9000);}
function bind(id,fn){$(id)?.addEventListener('click',()=>run(fn));}
async function run(fn){try{await fn();}catch(e){notify(e.message||'Não foi possível concluir. Seus dados anteriores foram preservados.');}}
function modal(title,body,label,action,wide=false){
  modalAction=action;dialog.classList.toggle('wide',wide);$('dialog-content').innerHTML='<h2>'+esc(title)+'</h2>'+body+'<p id="dialog-error" role="alert"></p>';$('confirm').textContent=label;$('confirm').hidden=!action;$('cancel').textContent=action?'Cancelar':'Fechar';dialog.showModal();
}
$('cancel').onclick=()=>dialog.close();
$('dialog-form').onsubmit=async e=>{e.preventDefault();if(busy||!modalAction)return;busy=true;$('confirm').disabled=true;try{await modalAction();dialog.close();}catch(error){$('dialog-error').textContent=error.message;}finally{busy=false;$('confirm').disabled=false;}};
window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
channel?.addEventListener('message',e=>{if(project?.id===e.data)notify('Este projeto foi alterado em outra aba. Volte a Projetos e reabra antes de salvar.');});
function download(text,name,type){const url=URL.createObjectURL(new Blob([text],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),60000);}
function leave(fn){if(!dirty)return run(fn);modal('Sair sem salvar?','<p>As alterações no editor ainda não foram salvas. Você pode cancelar e guardar o texto primeiro.</p>','Descartar alterações',async()=>{dirty=false;await fn();});}
async function commit(mutator){const next=structuredClone(project);await mutator(next);validateProject(next);project=await saveProject(db,next,project.version);channel?.postMessage(project.id);}
async function projectsView(){
  const items=await listProjects(db);project=null;dirty=false;
  content.innerHTML='<p class="eyebrow">KNOWLEDGE WORKSPACE</p><div class="page-head"><div><h1>Seu conhecimento,<br>pronto para compartilhar.</h1><p class="lead">Transforme documentos em uma central de ajuda. Confira cada artigo e mantenha a história do que mudou.</p></div><button id="create">+ Novo projeto</button></div>'+
    (items.length?'<h2>Seus projetos <span class="pill">'+items.length+'</span></h2><div class="cards">'+items.map(p=>'<section class="panel card"><span class="eyebrow">CENTRAL DE AJUDA</span><h2>'+esc(p.name)+'</h2><p>'+p.documents.length+' artigos · '+p.documents.filter(current).length+' revisados</p><p>'+p.publications.length+' publicações preservadas</p><button class="secondary" data-open="'+esc(p.id)+'">Abrir projeto →</button></section>').join('')+'</div>':'<section class="panel welcome"><div><p class="eyebrow">DA PRIMEIRA NOTA À CENTRAL</p><h2>Um lugar para escrever.<br>Um jeito de manter em dia.</h2><p class="lead">Comece com seus próprios arquivos ou escreva o primeiro artigo aqui.</p><button id="create-empty">Criar meu primeiro projeto →</button></div><ol><li>Traga seus documentos Markdown ou texto.</li><li>Edite e confira a prévia de cada artigo.</li><li>Registre a revisão e baixe a central com busca.</li><li>Guarde um backup para continuar em outro navegador.</li></ol></section>')+
    '<div class="notice"><strong>Seu trabalho fica neste navegador.</strong> Limpar os dados do site, usar uma janela privada ou perder este dispositivo pode apagar os projetos. Faça backup regularmente. Esta edição não sincroniza com a versão Python e não carrega backups ZIP dela.</div>';
  const create=()=>modal('Novo projeto','<p>Este nome aparecerá na central exportada.</p><label for="project-name">Nome da central</label><input id="project-name" maxlength="120" required placeholder="Ex.: Ajuda do meu produto">','Criar projeto',async()=>{
    if((await listProjects(db)).length>=20)throw new Error('Limite de 20 projetos neste navegador.');
    project=await saveProject(db,newProject($('project-name').value),null);projectView();
  });
  bind('create',create);bind('create-empty',create);
  content.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>run(async()=>{project=(await listProjects(db)).find(p=>p.id===b.dataset.open);if(!project)throw new Error('Projeto não encontrado.');projectView();}));
}
function projectView(){
  dirty=false;const count=project.documents.filter(current).length;
  content.innerHTML='<button id="back" class="secondary small">← Projetos</button><p class="eyebrow">CENTRAL DE AJUDA</p><div class="page-head"><div><h1>'+esc(project.name)+'</h1><p class="lead">'+project.documents.length+' artigos · '+count+' revisados · salvo neste navegador</p></div><button id="publish" '+(!project.documents.length||count!==project.documents.length?'disabled':'')+'>Gerar central ↓</button></div><div class="steps"><span><b>01</b> Importar ou escrever</span><span><b>02</b> Conferir cada artigo</span><span><b>03</b> Exportar e guardar backup</span></div><div class="actions"><button id="import">↑ Importar documentos</button><button id="write" class="secondary">+ Escrever artigo</button><button id="review-next" class="secondary" '+(count===project.documents.length?'disabled':'')+'>Revisar próximo artigo →</button></div>'+
    (project.documents.length?'<section class="panel"><h2>Documentos</h2>'+project.documents.map(d=>'<div class="doc-row"><div><h3>'+esc(d.title)+'</h3><p class="muted">'+esc(d.filename||'Escrito no Workspace')+' · versão '+d.revision+'</p></div><span class="pill '+(current(d)?'':'pending')+'">'+(current(d)?'Revisado':d.review?'Revisão vencida':'Revisão pendente')+'</span><div class="actions"><button class="secondary small" data-edit="'+d.id+'">Editar</button><button class="secondary small" data-review="'+d.id+'">Conferir</button></div></div>').join('')+'</section>':'<div class="empty"><h2>A sua central começa aqui.</h2><p class="muted">Importe arquivos .md ou .txt, ou escreva um artigo. Tudo começa como rascunho.</p></div>')+
    '<section class="panel"><h2>Publicações preservadas</h2><p class="muted">Editar um artigo vence sua revisão. Uma central já gerada continua disponível exatamente como foi salva.</p>'+project.publications.slice().reverse().map(pub=>'<div class="doc-row"><div><h3>Central · '+esc(date(pub.at))+'</h3><p class="muted">Versão do projeto '+pub.version+'</p></div><button class="secondary small" data-download="'+pub.id+'">Baixar HTML</button></div>').join('')+(project.publications.length?'':'<p class="muted">Revise todos os artigos para gerar a primeira central.</p>')+'</section>';
  bind('back',projectsView);bind('import',()=>{$('import-files').value='';$('import-files').click();});bind('write',()=>editor(null));bind('publish',publish);
  bind('review-next',()=>review(project.documents.find(d=>!current(d)).id,true));
  content.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>editor(b.dataset.edit));
  content.querySelectorAll('[data-review]').forEach(b=>b.onclick=()=>review(b.dataset.review,false));
  content.querySelectorAll('[data-download]').forEach(b=>b.onclick=()=>download(project.publications.find(p=>p.id===b.dataset.download).html,'central-'+b.dataset.download+'.html','text/html;charset=utf-8'));
}
function editor(id){
  const doc=project.documents.find(d=>d.id===id);dirty=false;
  content.innerHTML='<button id="back-project" class="secondary small">← Central</button><div class="page-head"><div><p class="eyebrow">'+(doc?'VERSÃO '+doc.revision:'NOVO ARTIGO')+'</p><h1>'+(doc?'Editar artigo':'Escreva seu primeiro rascunho')+'</h1></div><div class="actions"><span id="save-state" class="save-state">'+(doc?'Versão salva':'Ainda não salvo')+'</span><button id="save">Salvar artigo</button></div></div><div class="editor"><section><label for="title">Título público</label><input id="title" maxlength="160" value="'+esc(doc?.title||'')+'"><label for="body">Conteúdo público · Markdown ou texto</label><textarea id="body" spellcheck="true">'+esc(doc?.body||'')+'</textarea><p class="muted">Títulos, listas, negrito, código e links HTTPS. HTML aparece como texto; imagens e anexos não são importados. Links entre arquivos do projeto levam ao artigo correspondente.</p></section><section><label>Prévia do leitor</label><div id="preview" class="preview"></div></section></div>'+
    (doc?'<details><summary>Original importado e histórico privado ('+doc.history.length+')</summary><h3>Texto original</h3><pre class="history-text">'+esc(doc.original)+'</pre>'+doc.history.slice().reverse().map(h=>'<h3>Versão '+h.revision+' · '+esc(date(h.at))+'</h3><strong>'+esc(h.title)+'</strong><pre class="history-text">'+esc(h.body)+'</pre>').join('')+'</details>':'');
  const preview=()=>{$('preview').innerHTML='<h2>'+esc($('title').value||'Título do artigo')+'</h2>'+markdown($('body').value,project.documents);};preview();
  for(const key of ['title','body'])$(key).oninput=()=>{dirty=true;$('save-state').textContent='Alterações não salvas';preview();};
  bind('back-project',()=>leave(projectView));
  bind('save',async()=>{
    const title=$('title').value,body=$('body').value;
    if(doc && doc.title===title.trim() && doc.body===body){dirty=false;notify('Nenhuma alteração para salvar.');return;}
    let target=id;
    await commit(p=>{if(!doc){const d=newDocument(title,body);target=d.id;p.documents.push(d);}else changeDocument(p.documents.find(d=>d.id===id),title,body);});
    dirty=false;editor(target);notify('Artigo salvo. Confira esta versão antes de gerar a central.');
  });
}
function review(id,queue){
  const doc=project.documents.find(d=>d.id===id);
  modal('Conferir: '+doc.title,'<p class="muted">Versão '+doc.revision+' · '+(current(doc)?'Esta versão já foi revisada.':'A leitura e a veracidade do conteúdo são responsabilidade do operador.')+'</p><div class="preview">'+markdown(doc.body,project.documents)+'</div><label for="review-note">Nota da conferência (privada)</label><textarea id="review-note" maxlength="2000" class="short-text" required placeholder="O que você conferiu e quais limites permanecem?"></textarea><label class="check"><input id="review-check" type="checkbox" required>Conferi este artigo e seus limites. Esta é uma revisão declarada, não uma certificação independente.</label>',queue?'Registrar e continuar':'Registrar revisão',async()=>{
    if(!$('review-check').checked)throw new Error('Confirme a conferência individual.');
    const note=$('review-note').value;await commit(p=>reviewDocument(p.documents.find(d=>d.id===id),note));projectView();
    const next=queue&&project.documents.find(d=>!current(d));if(next)setTimeout(()=>review(next.id,true),0);else notify('Revisão salva para esta versão.');
  },true);
}
async function publish(){
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
bind('backup',async()=>{
  if(dirty)throw new Error('Salve o artigo antes de fazer backup.');
  const items=await listProjects(db);if(!items.length)throw new Error('Crie um projeto antes de fazer backup.');
  modal('Backup privado','<p>Este arquivo guarda todos os projetos salvos neste navegador: originais, artigos, histórico, notas e publicações. Ele não é a central pública.</p><p>Guarde em local sob seu controle. Não há criptografia ou cópia automática na nuvem. Compatível com esta edição web; separado do backup ZIP da versão Python.</p>','Baixar backup privado',async()=>{const data=await makeBackup(await listProjects(db));download(data,'workspace-web-backup-'+new Date().toISOString().slice(0,10)+'.json','application/json');notify('Download do backup iniciado. Confira o arquivo na sua pasta de downloads.');});
});
bind('restore',()=>leave(()=>{$('restore-file').value='';$('restore-file').click();}));
$('restore-file').onchange=()=>run(async()=>{
  const f=$('restore-file').files[0];if(!f)return;if(f.size>16*1024*1024)throw new Error('Backup maior que 16 MiB.');
  const copies=await readBackup(await f.text());
  modal('Recuperar em novos projetos','<p>Integridade conferida. Serão criadas '+copies.length+' cópias, com o sufixo “recuperado”. Os projetos existentes serão preservados.</p><ul>'+copies.map(p=>'<li>'+esc(p.name)+' · '+p.documents.length+' artigos</li>').join('')+'</ul><p class="notice">Use apenas backups próprios confiáveis. O checksum detecta corrupção, mas não autentica a autoria. Revisões declaradas e publicações do backup serão preservadas.</p>','Recuperar cópias',async()=>{await restoreCopies(db,copies);await projectsView();notify('Cópias recuperadas. Os projetos anteriores foram preservados.');});
});
try{db=await openStore();db.onversionchange=()=>{db.close();notify('O armazenamento foi atualizado. Recarregue esta aba.');};await projectsView();}catch(e){content.innerHTML='<h1>Não foi possível abrir o armazenamento.</h1><p>'+esc(e.message)+'</p><p>Tente uma janela normal com armazenamento permitido. Nenhum projeto foi substituído.</p>';for(const id of ['projects','backup','restore'])$(id).disabled=true;}
