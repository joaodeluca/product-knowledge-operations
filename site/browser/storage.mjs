import {validateProject,uid,LIMIT} from './model.mjs';
const DB='knowledge-workspace-browser-v1';
export async function openStore() {
  if(!globalThis.indexedDB) throw new Error('Este navegador não oferece armazenamento local. Use outro navegador.');
  return new Promise((resolve,reject)=>{
    const req=indexedDB.open(DB,1);
    req.onupgradeneeded=()=>req.result.createObjectStore('projects',{keyPath:'id'});
    req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);
    req.onblocked=()=>reject(new Error('Feche outras abas deste Workspace e tente novamente.'));
  });
}
export async function listProjects(db) {
  return new Promise((resolve,reject)=>{const r=db.transaction('projects').objectStore('projects').getAll();r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
}
export async function saveProject(db,project,expectedVersion) {
  validateProject(project);
  return new Promise((resolve,reject)=>{
    const tx=db.transaction('projects','readwrite'),store=tx.objectStore('projects');let reason, saved;
    const req=store.getAll();
    req.onsuccess=()=>{
      if((req.result.find(p=>p.id===project.id)?.version??null)!==expectedVersion){reason=new Error('Este projeto mudou em outra aba. Guarde seu texto, volte a Projetos e reabra a versão atual.');tx.abort();return;}
      saved=structuredClone(project);saved.version=(expectedVersion??0)+1;
      const projects=req.result.filter(p=>p.id!==saved.id).concat(saved);
      if(projects.length>20 || new TextEncoder().encode(JSON.stringify({projects})).length>LIMIT){reason=new Error('Limite local: 20 projetos e 8 MiB no total. Seus dados anteriores foram preservados.');tx.abort();return;}
      store.put(saved);
    };
    tx.oncomplete=()=>resolve(saved);tx.onabort=()=>reject(reason||tx.error||new Error('Não foi possível salvar. Faça backup; confira o espaço disponível.'));tx.onerror=()=>{};
  });
}
export async function restoreCopies(db,projects) {
  projects.forEach(validateProject);
  const copies=projects.map(p=>({...structuredClone(p),id:uid(),name:(p.name+' · recuperado').slice(0,120),version:1}));
  return new Promise((resolve,reject)=>{
    const tx=db.transaction('projects','readwrite'),store=tx.objectStore('projects');
    const all=store.getAll();all.onsuccess=()=>{const projects=[...all.result,...copies];if(projects.length>20 || new TextEncoder().encode(JSON.stringify({projects})).length>LIMIT){tx.abort();return;}copies.forEach(p=>store.add(p));};
    tx.oncomplete=()=>resolve(copies);tx.onabort=()=>reject(new Error('Restauração não salva. Limite de 20 projetos/8 MiB no total ou espaço insuficiente; os projetos anteriores permanecem.'));tx.onerror=()=>{};
  });
}
