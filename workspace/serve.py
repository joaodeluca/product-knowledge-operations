#!/usr/bin/env python3
"""Run an independent, single-operator editorial workspace on loopback."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
import engine
import intake
from reader import page

ROOT=Path(__file__).resolve().parent
VERSION='0.2.0'

class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self, store, port=0):
        self.store=engine._safe_path(store)
        self.store.mkdir(parents=True, exist_ok=True, mode=0o700)
        marker=engine._safe_path(self.store/'workspace.json')
        if not marker.exists() and any(self.store.iterdir()):
            raise ValueError('Use uma pasta vazia ou um workspace deste produto. Dados existentes não serão adotados.')
        if marker.exists() and json.loads(marker.read_text()) != {'product':'product-knowledge-workspace','schema':1}:
            raise ValueError('Workspace incompatível.')
        if not marker.exists():
            with marker.open('x') as f: json.dump({'product':'product-knowledge-workspace','schema':1},f)
            marker.chmod(0o600)
        self.lock=engine._safe_path(self.store/'workspace.lock').open('a')
        try: fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.lock.close(); raise ValueError('Este workspace já está aberto em outro processo.')
        try:
            super().__init__(('127.0.0.1',port),Handler)
            self.origin=f'http://127.0.0.1:{self.server_port}'
            self.cookie='pkow_'+str(self.server_port)
            self.token=secrets.token_urlsafe(32); self.bootstrap=secrets.token_urlsafe(32)
            self.desk=engine.Desk(self.store/'content.sqlite3',self.store/'releases')
            marker.write_text(json.dumps({'product':'product-knowledge-workspace','schema':1})); marker.chmod(0o600)
            self.link()
        except Exception:
            self.lock.close(); raise
    def link(self):
        path=engine._safe_path(self.store/'session.json'); tmp=self.store/('.session-'+secrets.token_hex(8))
        fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f: json.dump({'url':self.origin+'/start/'+self.bootstrap},f)
        os.replace(tmp,path)
    def server_close(self):
        super().server_close(); self.lock.close()

class Handler(BaseHTTPRequestHandler):
    server_version='KnowledgeWorkspace/'+VERSION
    def log_message(self,*args): pass
    def send(self,status,value=None,mime='application/json; charset=utf-8',extra=None):
        raw=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode()
        try:
            self.send_response(status)
            headers={'Content-Type':mime,'Content-Length':str(len(raw)),'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff','X-Frame-Options':'SAMEORIGIN','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'"}
            headers.update(extra or {})
            for k,v in headers.items(): self.send_header(k,v)
            self.end_headers()
            if self.command!='HEAD': self.wfile.write(raw)
        except (BrokenPipeError,ConnectionResetError): pass
    def error(self,status,message): self.send(status,{'error':message})
    def auth(self):
        if self.headers.get('Host')!=f'127.0.0.1:{self.server.server_port}':
            self.error(421,'Host inválido'); return False
        cookies=dict(x.strip().split('=',1) for x in self.headers.get('Cookie','').split(';') if '=' in x)
        if not secrets.compare_digest(cookies.get(self.server.cookie,'').encode(),self.server.token.encode()):
            self.error(401,'Abra a sessão local indicada em session.json.'); return False
        return True
    def do_GET(self):
        path=urlsplit(self.path); parts=path.path.strip('/').split('/')
        if self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}' and path.path=='/start/'+self.server.bootstrap:
            self.server.bootstrap=secrets.token_urlsafe(32); self.server.link()
            return self.send(303,b'',extra={'Location':'/','Set-Cookie':f'{self.server.cookie}={self.server.token}; HttpOnly; SameSite=Strict; Path=/'})
        if not self.auth(): return
        d=self.server.desk; q=parse_qs(path.query)
        try:
            if path.path=='/api/state':
                pid=q.get('project',[None])[0]
                return self.send(200,{'version':VERSION,'projects':d.projects(),'project':d.project(pid) if pid else None})
            if path.path=='/api/preview':
                p=d.project(q.get('project',[None])[0]); aid=q.get('article',[None])[0]
                a=next((a for a in p['articles'] if a['id']==aid),None)
                if not a: return self.error(404,'Artigo ausente')
                content=engine._render(a['markdown'],set())
                return self.send(200,page(a['title'],content),'text/html; charset=utf-8')
            if len(parts)==5 and parts[:2]==['api','sources'] and parts[4]=='history':
                return self.send(200,d.snapshots(parts[2],parts[3]))
            if len(parts)==5 and parts[:2]==['api','releases'] and parts[4]=='download':
                raw=d.export_release(parts[2],parts[3])
                return self.send(200,raw,'application/zip',{'Content-Disposition':'attachment; filename="help-center.zip"'})
            if len(parts)>=4 and parts[0]=='reader':
                name='/'.join(parts[3:]); raw=d.release_file(parts[1],parts[2],name)
                return self.send(200,raw,'text/html; charset=utf-8' if name.endswith('.html') else 'application/json',{'Content-Security-Policy':"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'"})
            names={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
            if path.path in names:
                name=names[path.path]; mime={'html':'text/html','js':'text/javascript','css':'text/css'}[name.split('.')[-1]]
                return self.send(200,(ROOT/'web'/name).read_bytes(),mime+'; charset=utf-8')
            self.error(404,'Página ausente')
        except engine.DeskError as e: self.error(e.status,str(e))
        except (ValueError,TypeError,KeyError): self.error(400,'Pedido inválido')
        except Exception: self.error(500,'Falha interna; confira o estado antes de tentar novamente.')
    def do_POST(self): self.mutate()
    def do_PATCH(self): self.mutate()
    def mutate(self):
        if not self.auth(): return
        if self.headers.get('Origin')!=self.server.origin or self.headers.get('X-Workspace')!='1': return self.error(403,'Origem recusada')
        if self.headers.get('Content-Type','').split(';')[0]!='application/json': return self.error(415,'Use JSON')
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=262144: return self.error(413,'Pedido acima do limite de256KiB')
            data=json.loads(self.rfile.read(n))
            if not isinstance(data,dict): return self.error(400,'Objeto obrigatório')
            parts=urlsplit(self.path).path.strip('/').split('/'); d=self.server.desk
            if parts==['api','projects'] and self.command=='POST': return self.send(201,d.create_project(data))
            pid=data.get('project_id'); rev=data.get('expected_revision')
            if parts==['api','import','preview'] and self.command=='POST': return self.send(200,intake.preview(d,pid,data,rev))
            if parts==['api','import','apply'] and self.command=='POST': return self.send(201,intake.apply(d,pid,data,rev))
            fns={'sources':(d.create_source,d.update_source),'procedures':(d.create_procedure,d.update_procedure),'articles':(d.create_article,d.update_article)}
            if len(parts)==2 and parts[0]=='api' and parts[1] in fns and self.command=='POST': return self.send(201,fns[parts[1]][0](pid,data,rev))
            if len(parts)==3 and parts[0]=='api' and parts[1] in fns and self.command=='PATCH': return self.send(200,fns[parts[1]][1](pid,parts[2],data,rev))
            if len(parts)==4 and parts[:2]==['api','articles'] and parts[3]=='review' and self.command=='POST': return self.send(200,d.review_article(pid,parts[2],data,rev))
            if parts==['api','publish'] and self.command=='POST':
                if data.get('public_fields_reviewed') is not True: return self.error(400,'Confirme a revisão dos campos destinados ao leitor.')
                return self.send(201,d.publish(pid,data,rev))
            if parts==['api','activate'] and self.command=='POST': return self.send(200,d.rollback(pid,data.get('release_id'),data,rev))
            self.error(404,'Ação ausente')
        except engine.DeskError as e: self.error(e.status,str(e))
        except (ValueError,TypeError,KeyError): self.error(400,'Pedido inválido')
        except Exception: self.error(500,'Falha interna; confira o estado antes de tentar novamente.')

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--store',type=Path,required=True); p.add_argument('--port',type=int,default=0); p.add_argument('--open',action='store_true')
    args=p.parse_args(); os.umask(0o077)
    if not 0<=args.port<=65535: p.error('Porta inválida')
    try: server=Server(args.store.absolute(),args.port)
    except (ValueError,OSError,engine.DeskError) as e: p.exit(2,str(e)+'\n')
    print(f'Workspace {VERSION} em {server.origin}\nSessão privada: {server.store / "session.json"}\nCtrl+C encerra; os dados permanecem na pasta escolhida.',flush=True)
    if args.open:
        import webbrowser
        webbrowser.open(json.loads((server.store/'session.json').read_text())['url'])
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
if __name__=='__main__': main()
