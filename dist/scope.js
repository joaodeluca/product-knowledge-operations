document.querySelector('#scope-form').addEventListener('submit',event=>{
 event.preventDefault(); const form=event.currentTarget; if(!form.reportValidity())return;
 const product=document.querySelector('#product').value.trim();
 const task=document.querySelector('#task').value.trim(); const gap=document.querySelector('#gap').value.trim();
 const error=document.querySelector('#form-error'); error.hidden=true;
 let parsed;try{parsed=new URL(product)}catch{error.textContent='Use uma URL pública completa.';error.hidden=false;return}
 if(!['https:','http:'].includes(parsed.protocol)||parsed.username||parsed.password||parsed.search||parsed.hash){error.textContent='Use uma URL pública sem senha, parâmetros de acesso ou fragmentos.';error.hidden=false;return}
 const target=new URL('https://github.com/joaodeluca/product-knowledge-operations/issues/new');
 target.searchParams.set('template','public-product-scope.yml');
 target.searchParams.set('title','[Product scope] '+task.slice(0,90));
 target.searchParams.set('product',product);
 target.searchParams.set('procedure',task);
 target.searchParams.set('gap',gap);
 if(target.href.length>6000){error.textContent='O escopo ficou longo para a página de revisão. Reduza os textos e tente novamente.';error.hidden=false;return}
 window.location.assign(target.href);
});
