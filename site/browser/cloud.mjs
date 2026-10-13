import {validateProject,uid} from './model.mjs';
export function cloudStore(config,{fetcher=globalThis.fetch,now=Date.now}={}) {
  const url=new URL(config.url);
  if(url.protocol!=='https:'||!/^([a-z0-9-]+)\.supabase\.co$/.test(url.hostname)||url.port||url.username||url.password||url.pathname!=='/'||url.search||url.hash)throw Error('Endereço da conta não configurado corretamente.');
  if(!/^sb_publishable_[A-Za-z0-9_-]+$/.test(config.publishableKey))throw Error('Use somente a chave pública publishable da conta.');
  let session=null,expires=0,refreshing=null;
  async function request(path,data,token,write=false) {
    let response;
    try{response=await fetcher(url.origin+path,{method:'POST',headers:{apikey:config.publishableKey,'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:JSON.stringify(data),credentials:'omit',cache:'no-store',redirect:'error',signal:AbortSignal.timeout(25000)});}
    catch{throw Error(write?'Sem confirmação do servidor. Ele pode ter salvo a alteração. Preserve seu texto e reabra o projeto antes de tentar novamente.':'Não foi possível conectar à conta. Confira a conexão e tente novamente.');}
    if(!response.ok){
      if(response.status===409)throw Error('Este projeto mudou em outro dispositivo. Preserve seu texto, volte a Projetos e reabra a versão atual.');
      if(response.status===401){session=null;throw Error('Sessão expirada ou dados de acesso inválidos. Entre novamente.');}
      if(response.status===403)throw Error('Esta conta não tem acesso ao Workspace.');
      if(response.status===413)throw Error('Limite de armazenamento da conta atingido.');
      const body=await response.json().catch(()=>({}));
      if(body.code==='23514')throw Error('Dados ou limite da conta inválidos. São permitidos 20 projetos e 8 MiB no total.');
      throw Error(write?'O servidor não confirmou a gravação. Preserve seu texto e confira a lista de projetos antes de repetir.':'Não foi possível abrir a conta. Tente novamente mais tarde.');
    }
    return response.status===204?null:response.json();
  }
  function accept(value){if(!value?.access_token||!value?.refresh_token||!value?.user?.id)throw Error('Resposta de autenticação inválida.');session=value;expires=now()+Math.max(0,Number(value.expires_in||0)-30)*1000;}
  async function token(){
    if(!session)throw Error('Entre na sua conta para continuar.');
    if(now()>=expires){if(!refreshing)refreshing=request('/auth/v1/token?grant_type=refresh_token',{refresh_token:session.refresh_token}).then(accept).catch(e=>{session=null;throw e;}).finally(()=>refreshing=null);await refreshing;}
    return session.access_token;
  }
  async function rpc(name,args,write=false){return request('/rest/v1/rpc/'+name,args,await token(),write);}
  return {mode:'cloud',
    get user(){return session?{id:session.user.id,email:session.user.email}:null;},
    async signIn(email,password){accept(await request('/auth/v1/token?grant_type=password',{email,password}));try{return await this.listProjects();}catch(e){session=null;throw e;}},
    async signOut(){const access=session?.access_token;session=null;expires=0;if(access)await request('/auth/v1/logout?scope=local',{},access);},
    async listProjects(){const projects=await rpc('kw_list_projects',{});if(!Array.isArray(projects))throw Error('Resposta de projetos inválida.');projects.forEach(validateProject);return projects;},
    async saveProject(project,expectedVersion){validateProject(project);const saved=await rpc('kw_save_project',{p_project:project,p_expected_version:expectedVersion},true);validateProject(saved);if(saved.id!==project.id||saved.version!==(expectedVersion??0)+1)throw Error('Confirmação inesperada. Reabra o projeto antes de continuar.');return saved;},
    async restoreCopies(projects){projects.forEach(validateProject);const copies=projects.map(p=>({...structuredClone(p),id:uid(),name:(p.name+' · recuperado').slice(0,120),version:1}));const saved=await rpc('kw_restore_projects',{p_projects:copies},true);if(!Array.isArray(saved)||saved.length!==copies.length)throw Error('Confirmação inesperada da recuperação. Confira a lista antes de repetir.');saved.forEach(validateProject);return saved;}
  };
}
