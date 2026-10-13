import {Editor,StarterKit,Image} from './editor-vendor.mjs';
import {decodeRich,encodeRich,safeLink,safeImage} from './rich.mjs';
import {markdown} from './model.mjs';
export function createVisualEditor(element,body,docs,onChange){
 const SafeImage=Image.extend({parseHTML(){return [{tag:'img[src]',getAttrs:el=>safeImage(el.getAttribute('src'))?null:false}];}});
 const rich=decodeRich(body);
 return new Editor({element,injectCSS:false,enableInputRules:false,enablePasteRules:false,
  extensions:[StarterKit.configure({heading:{levels:[2,3,4,5,6]},link:{openOnClick:false,autolink:false,linkOnPaste:false,isAllowedUri:url=>!!safeLink(url)},trailingNode:false}),SafeImage.configure({allowBase64:true})],
  content:rich||markdown(body,docs)||'<p></p>',
  editorProps:{attributes:{role:'textbox','aria-label':'Conteúdo do artigo','aria-multiline':'true',spellcheck:'true'},
   transformPastedHTML:html=>html.replace(/<img\b[^>]*>/gi,''),
   handleDrop:(_view,event)=>{event.preventDefault();return true;}},
  onUpdate:({editor})=>onChange(editor)
 });
}
export const toolbarHTML='<div class="visual-toolbar" role="toolbar" aria-label="Formatação do artigo">'+[
 ['paragraph','Texto'],['heading','Título'],['bold','Negrito'],['italic','Itálico'],['underline','Sublinhar'],['bulletList','Lista'],['orderedList','Lista numerada'],['blockquote','Citação'],['codeBlock','Código'],['undo','Desfazer'],['redo','Refazer']
].map(([command,label])=>'<button type="button" class="secondary small" data-format="'+command+'">'+label+'</button>').join('')+'<button type="button" class="secondary small" id="visual-link">Link</button><button type="button" class="secondary small" id="visual-image">Imagem</button><button type="button" class="secondary small" id="visual-remove-image">Remover imagem</button></div>';
export function bindToolbar(editor,root){
 root.querySelectorAll('[data-format]').forEach(button=>{
  button.onmousedown=e=>e.preventDefault();
  button.onclick=()=>{const chain=editor.chain().focus();const c=button.dataset.format;if(c==='paragraph')chain.setParagraph().run();else if(c==='heading')chain.toggleHeading({level:2}).run();else if(c==='undo'||c==='redo')chain[c]().run();else chain['toggle'+c[0].toUpperCase()+c.slice(1)]().run();};
 });
 const update=()=>{root.querySelectorAll('[data-format]').forEach(b=>{const c=b.dataset.format;b.setAttribute('aria-pressed',String(editor.isActive(c)));if(c==='undo'||c==='redo')b.disabled=!editor.can()[c]();});root.querySelector('#visual-remove-image').disabled=!editor.isActive('image');};
 root.querySelector('#visual-remove-image').onmousedown=e=>e.preventDefault();root.querySelector('#visual-remove-image').onclick=()=>{if(editor.isActive('image'))editor.chain().focus().deleteSelection().run();};
 editor.on('transaction',update);update();
}
export {encodeRich};
