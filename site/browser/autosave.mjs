// JSONB can return object keys in a different order; arrays remain ordered.
export function sameJSON(a,b){
 if(a===b)return true;
 if(!a||!b||typeof a!=='object'||typeof b!=='object'||Array.isArray(a)!==Array.isArray(b))return false;
 const keys=Object.keys(a);return keys.length===Object.keys(b).length&&keys.every(k=>Object.hasOwn(b,k)&&sameJSON(a[k],b[k]));
}
// One write at a time. Input received during a write is saved in the next pass.
export function autoSave({read,write,onState,delay=900,schedule=setTimeout,cancel=clearTimeout}) {
  let timer,flight=null,changed=false,stopped=false,failure=null;
  function state(name,error){onState(name,error);}
  async function drain(){
    while(changed&&!stopped){
      changed=false;const value=read();state('saving');
      try{await write(value);}catch(error){changed=true;failure=error;state('error',error);throw error;}
    }
    if(!stopped)state('saved');
  }
  function flush(){
    cancel(timer);
    if(failure)return Promise.reject(failure);
    if(!flight)flight=drain().finally(()=>flight=null);
    return flight;
  }
  return {
    get pending(){return changed||!!flight;},
    change(){if(stopped)return;changed=true;cancel(timer);if(failure?.retryOnChange)failure=null;if(failure){state('error',failure);return;}state('pending');timer=schedule(()=>flush().catch(()=>{}),delay);},
    flush,
    retry(){failure=null;return flush();},
    stop(){stopped=true;cancel(timer);},
  };
}
