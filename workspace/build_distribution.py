"""Build only original product source and static UI, never workspace data."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parent
FILES=('serve.py','engine.py','reader.py','intake.py','web/index.html','web/app.js','web/style.css','README.md','guide/primeiros-passos.md','guide/importar-documentos.md','guide/manter-central.md')
def build(output):
    output=Path(output).absolute()
    if output.is_relative_to(ROOT.parent): raise ValueError('Escolha saída fora do checkout.')
    values={name:(ROOT/name).read_bytes() for name in FILES}
    for name,body in values.items():
        if any(x in body for x in (b'/Users/',b'BEGIN PRIVATE KEY',b'github_pat_',b'ghp_')): raise ValueError('Referência privada no produto: '+name)
    manifest={'product':'Knowledge Workspace','version':'0.3.0','files':[{'path':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in sorted(values.items())]}
    values['distribution.json']=(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as stream:
        with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for name,body in sorted(values.items()):
                entry=zipfile.ZipInfo('knowledge-workspace/'+name,(1980,1,1,0,0,0));entry.create_system=3;entry.external_attr=0o100644<<16;entry.compress_type=zipfile.ZIP_DEFLATED;z.writestr(entry,body)
    return {'file':str(output),'bytes':output.stat().st_size,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'entries':len(values)}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);args=p.parse_args();print(json.dumps(build(args.output)))
