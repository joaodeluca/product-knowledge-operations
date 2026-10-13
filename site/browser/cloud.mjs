import {validateProject,uid} from './model.mjs';
export function cloudStore(config,{fetcher=globalThis.fetch,now=Date.now,storage=globalThis.localStorage,locks=globalThis.navigator?.locks}={}) {
  const url=new URL(config.url);
  if(url.protocol!=='https:'||!/^([a-z0-9-]+)\.supabase\.co$/.test(url.hostname)||url.port||url.username||url.password||url.pathname!=='/'||url.search||url.hash)throw Error('Endereço da conta não configurado corretamente.');
  if(!/^sb_publishable_[A-Za-z0-9_-]+$/.test(config.publishableKey))throw Error('Use somente a chave pública publishable da conta.');
  const sessionKey='kw-account-v1:'+url.hostname;
  let session=null,expires=0,refreshing=null,generation=0,owner=null;
  function clear(){session=null;expires=0;generation++;storage?.removeItem(sessionKey);}
  function load(){
    if(!storage)return;
    const raw=storage.getItem(sessionKey);
    if(!raw){session=null;expires=0;return;}
    try{const v=JSON.parse(raw);if(typeof v.access_token!=='string'||typeof v.refresh_token!=='string'||typeof v.user?.id!=='string'||!Number.isFinite(v.expiresAt))throw Error();session=v;expires=v.expiresAt;}
    catch{clear();}
  }
  load();
  async function request(path,data,token,write=false) {
    let response;
    try{response=await fetcher(url.origin+path,{method:'POST',headers:{apikey:config.publishableKey,'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:JSON.stringify(data),credentials:'omit',cache:'no-store',redirect:'error',signal:AbortSignal.timeout(25000)});}
    catch{throw Error(write?'Sem confirmação do servidor. Ele pode ter salvo a alteração. Preserve seu texto e reabra o projeto antes de tentar novamente.':'Não foi possível conectar à conta. Confira a conexão e tente novamente.');}
    if(!response.ok){
      if(response.status===409)throw Error('Este projeto mudou em outro dispositivo. Preserve seu texto, volte a Projetos e reabra a versão atual.');
      if(response.status===401 || (response.status===400 && path.includes('/auth/v1/token'))){throw Object.assign(Error('Sessão expirada ou dados de acesso inválidos. Entre novamente.'),{authExpired:true});}
      if(response.status===403)throw Error('Esta conta não tem acesso ao Workspace.');
      if(response.status===413)throw Error('Limite de armazenamento da conta atingido.');
      const body=await response.json().catch(()=>({}));
      if(body.code==='23514'){
        const publicationErrors={'Review every article before publishing':'Revise a versão atual de todos os artigos antes de publicar.','Publication exceeds 2 MiB':'Esta central excede o limite público de 2 MiB.','Publication history limit reached':'Esta central chegou ao limite de 20 versões publicadas. As versões existentes foram preservadas.','Publication storage limit reached':'O histórico de centrais publicadas atingiu o limite de 8 MiB da conta.'};
        throw Error(publicationErrors[body.message]||'Dados ou limite da conta inválidos. São permitidos 20 projetos e 8 MiB no total.');
      }
      throw Error(write?'O servidor não confirmou a gravação. Preserve seu texto e confira a lista de projetos antes de repetir.':'Não foi possível abrir a conta. Tente novamente mais tarde.');
    }
    return response.status===204?null:response.json();
  }
  function accept(value){
    if(!value?.access_token||!value?.refresh_token||!value?.user?.id)throw Error('Resposta de autenticação inválida.');
    expires=now()+Math.max(0,Number(value.expires_in||0)-30)*1000;
    session={access_token:value.access_token,refresh_token:value.refresh_token,user:{id:value.user.id,email:value.user.email},expiresAt:expires};
    try{storage?.setItem(sessionKey,JSON.stringify(session));}catch{clear();throw Error('Permita o armazenamento deste site para manter seu login.');}
  }
  async function token(){
    const renew=async()=>{
      load();if(!session)throw Error('Entre na sua conta para continuar.');
      if(owner&&session.user.id!==owner)throw Error('A conta mudou em outra aba. Preserve seu rascunho e entre novamente.');
      if(now()>=expires){
        const turn=generation,raw=storage?.getItem(sessionKey);
        try{const value=await request('/auth/v1/token?grant_type=refresh_token',{refresh_token:session.refresh_token});
          if(turn!==generation || (storage&&storage.getItem(sessionKey)!==raw))throw Error('O login mudou durante a conexão. Entre novamente.');accept(value);
        }catch(e){if(e.authExpired&&(!storage||storage.getItem(sessionKey)===raw))clear();throw e;}
      }
      return session.access_token;
    };
    if(!refreshing)refreshing=(locks?locks.request(sessionKey,renew):renew()).finally(()=>refreshing=null);
    return refreshing;
  }
  async function rpc(name,args,write=false){
    const access=await token();
    try{return await request('/rest/v1/rpc/'+name,args,access,write);}
    catch(e){if(e.authExpired){load();if(session?.access_token===access)clear();}throw e;}
  }
  function helpMeta(value,nullable=false){
    if(value===null&&nullable)return null;
    if(!value||! /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i.test(value.public_id)||!Number.isSafeInteger(value.revision)||value.revision<1||typeof value.live!=='boolean'||!Number.isSafeInteger(value.source_version)||value.source_version<1||typeof value.published_at!=='string'||!Number.isFinite(Date.parse(value.published_at)))throw Error('Confirmação de publicação inesperada. Reabra o projeto para conferir.');
    return value;
  }
  return {mode:'cloud',sessionKey,
    async resume(){load();if(!session)return null;owner=session.user.id;return this.listProjects();},
    get user(){return session?{id:session.user.id,email:session.user.email}:null;},
    async signIn(email,password){accept(await request('/auth/v1/token?grant_type=password',{email,password}));owner=session.user.id;const access=session.access_token;try{return await this.listProjects();}catch(e){load();if(session?.access_token===access)clear();throw e;}},
    async signOut(){load();const access=session?.access_token;clear();if(access)await request('/auth/v1/logout?scope=local',{},access);},
    async helpStatus(projectId){return helpMeta(await rpc('kw_help_status',{p_project_id:projectId}),true);},
    async publishHelp(projectId,version,revision){const result=helpMeta(await rpc('kw_publish_help',{p_project_id:projectId,p_expected_version:version,p_expected_publication_revision:revision},true));if(!result.live||result.source_version!==version)throw Error('Publicação não confirmada. Reabra o projeto para conferir.');return result;},
    async unpublishHelp(projectId,revision){const result=helpMeta(await rpc('kw_unpublish_help',{p_project_id:projectId,p_expected_publication_revision:revision},true),true);if(result?.live)throw Error('Retirada não confirmada. Reabra o projeto para conferir.');return result;},
    async listProjects(){const projects=await rpc('kw_list_projects',{});if(!Array.isArray(projects))throw Error('Resposta de projetos inválida.');projects.forEach(validateProject);return projects;},
    async saveProject(project,expectedVersion){validateProject(project);const saved=await rpc('kw_save_project',{p_project:project,p_expected_version:expectedVersion},true);validateProject(saved);if(saved.id!==project.id||saved.version!==(expectedVersion??0)+1)throw Error('Confirmação inesperada. Reabra o projeto antes de continuar.');return saved;},
    async restoreCopies(projects){projects.forEach(validateProject);const copies=projects.map(p=>({...structuredClone(p),id:uid(),name:(p.name+' · recuperado').slice(0,120),version:1}));const saved=await rpc('kw_restore_projects',{p_projects:copies},true);if(!Array.isArray(saved)||saved.length!==copies.length)throw Error('Confirmação inesperada da recuperação. Confira a lista antes de repetir.');saved.forEach(validateProject);return saved;}
  };
}
