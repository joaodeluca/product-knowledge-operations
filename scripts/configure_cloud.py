"""Prepare public client settings. Does not provision, deploy or read credentials."""
import argparse,json,re
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
def configure(url=None,key=None):
    origin='none'
    config=None
    if url or key:
        p=urlsplit(url or '')
        if p.scheme!='https' or not re.fullmatch(r'[a-z0-9-]+\.supabase\.co',p.hostname or '') or p.username or p.password or p.port or p.path not in ('','/') or p.query or p.fragment:
            raise ValueError('Use the HTTPS URL of the authorized Supabase project.')
        if not re.fullmatch(r'sb_publishable_[A-Za-z0-9_-]+',key or ''):
            raise ValueError('Only a public sb_publishable_ key is accepted; never a secret or service-role key.')
        origin='https://'+p.hostname
        config={'url':origin,'publishableKey':key}
    page=ROOT/'site/browser/index.html'
    source=page.read_text()
    source,count=re.subn(r"connect-src [^;]+;", "connect-src "+("'none'" if config is None else origin)+";",source)
    if count!=1:raise ValueError('Expected exactly one CSP connect-src declaration.')
    settings=ROOT/'site/browser/cloud-config.mjs'
    settings.write_text('// Public deployment settings only; no secret keys.\nexport const cloudConfig = '+json.dumps(config,ensure_ascii=False)+';\n')
    page.write_text(source)
    print('Cloud configuration disabled.' if config is None else 'Prepared public settings and exact CSP origin: '+origin)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--url');p.add_argument('--publishable-key');p.add_argument('--disable',action='store_true');a=p.parse_args()
    if a.disable and (a.url or a.publishable_key):p.error('Disable cannot be combined with settings.')
    if not a.disable and (not a.url or not a.publishable_key):p.error('Provide --url and --publishable-key, or --disable.')
    configure(a.url,a.publishable_key)
