#!/usr/bin/env python3
"""Reproduce exactly three own public readers from their canonical Markdown.

No network, vendor execution, private state, dist writes or existing-output reset.
Build a fresh outside-Git tree; --check confronts inputs, references and output.
"""
import argparse
import hashlib
import html
import ipaddress
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import tempfile
import unicodedata
from urllib.parse import urlsplit

DOCUMENTS = {
    'docs/excalidraw/SAVE-RESTORE.md': 'excalidraw.html',
    'docs/openrefine/TRANSFER.md': 'openrefine.html',
    'docs/renovate/VALIDATION.md': 'renovate.html',
}
OWNER = 'https://github.com/joaodeluca/product-knowledge-operations'
CSS = 'assets/reader.css'
MANIFEST = 'reader-manifest.json'
MAX_TOTAL = 8 * 1024 * 1024
MAX_FILE = 1024 * 1024
EXCAL_FILES = {'diagram.png', 'scene-original.excalidraw', 'connector-deleted.png', 'connector-recovered.png', 'manifest.json'}
OPENREF_FILES = {'source.csv', 'filtered.csv', 'full.csv', 'handoff.openrefine.tar.gz', 'check_exports.py'}


def require(condition, message):
    if not condition: raise ValueError(message)


def digest(raw): return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8') + b'\n'


def safe_path(value):
    path = Path(os.path.abspath(os.fspath(value)))
    require(not any(x.is_symlink() for x in (path, *path.parents)), 'Symlink path refused')
    return path


def private_output(root, value):
    output = safe_path(value)
    require(not output.is_relative_to(root), 'Output must be outside the source checkout')
    require(not any((p / '.git').exists() for p in (output, *output.parents)), 'Output must be outside every Git checkout')
    return output


def read_file(path):
    path = safe_path(path)
    require(path.is_file() and path.stat().st_size <= MAX_FILE, 'Missing/nonregular/oversize input: ' + path.name)
    return path.read_bytes()


def privacy(text):
    require('\x00' not in text, 'NUL in public text')
    require(not re.search(r'\b[psatohrxc]_[0-9a-fA-F]{32}\b', text), 'Private operational identifier in public text')
    require(not re.search(r'(?:/Users/|/private/(?:var|tmp)/|/var/folders/|/home/|[A-Za-z]:\\)', text), 'Private absolute path in public text')
    require(not re.search(r'(?:session|bootstrap|access_token|csrf_token|api_key|auth_token)\s*[=:]\s*[A-Za-z0-9_-]{8,}', text, re.I), 'Private session/credential in public text')


def inventory(root):
    records = {}
    require(safe_path(root).is_dir(), 'Missing public dist')
    for folder, dirs, names in os.walk(root, followlinks=False):
        for child in dirs: safe_path(Path(folder) / child)
        for name in names:
            path = Path(folder) / name
            relative = path.relative_to(root).as_posix()
            require(not relative.startswith('.') and '/.' not in relative, 'Hidden public payload refused')
            require(name.endswith(('.html', '.css', '.js', '.png', '.json', '.txt', '.md', '.csv', '.py', '.excalidraw'))
                    or relative == 'openrefine/files/handoff.openrefine.tar.gz', 'Unexpected public dist file')
            raw = read_file(path)
            if not name.endswith(('.png', '.tar.gz')): privacy(raw.decode('utf-8'))
            records[relative] = raw
    require(records and sum(map(len, records.values())) <= MAX_TOTAL, 'Inherited public payload size bound')
    return records


class Renderer:
    def __init__(self, root, source, output, inputs):
        self.root, self.source, self.output, self.inputs = root, source, output, inputs
        self.references = {}; self.reference_sets = {}; self.headings = []; self.ids = set()

    def reference(self, path):
        raw = read_file(self.root / path)
        old = self.inputs.setdefault(path, raw)
        require(old == raw, 'Input changed while reading references')
        self.references[path] = {'path': path, 'bytes': len(raw), 'sha256': digest(raw)}
        return raw

    def link(self, target, image=False):
        require(target and not re.search(r'[\s<>"\'\\]', target), 'Unsafe Markdown link')
        release_prefix = OWNER + '/releases/download/help-2026-10-05/'
        if target.startswith(release_prefix):
            name = target[len(release_prefix):]
            require(name in EXCAL_FILES - {'manifest.json'}, 'Unknown own release file')
            target = '../../dist/excalidraw/files/' + name
        parsed = urlsplit(target)
        if parsed.scheme:
            require(not image and parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password,
                    'Only ordinary public HTTPS links; images must be selected local originals')
            host = parsed.hostname.lower()
            require(host != 'localhost' and not host.endswith(('.localhost', '.local', '.internal')), 'Local URL refused')
            try: address = ipaddress.ip_address(host)
            except ValueError: address = None
            require(address is None or address.is_global, 'Private IP URL refused')
            require(not re.search(r'(session|token|secret|auth|key|bootstrap)\s*=', parsed.query, re.I), 'Credential query refused')
            return target
        require(not parsed.netloc and not parsed.query and '%' not in target and not parsed.path.startswith('/'), 'Unsafe relative link')
        if not parsed.path:
            require(parsed.fragment and not image, 'Empty/invalid local anchor')
            return target
        if self.source == 'docs/renovate/VALIDATION.md' and target in ('examples/', 'OBSERVATIONS.json'):
            require(not image, 'Renovate reference is not a local image')
            if target == 'examples/':
                folder = safe_path(self.root / 'docs/renovate/examples')
                require(folder.is_dir(), 'Missing own Renovate examples')
                files = sorted(folder.iterdir())
                require(files and len(files) <= 64, 'Invalid own example set')
                self.reference_sets['docs/renovate/examples'] = sorted(x.name for x in files)
                for path in files:
                    require(path.name.endswith('.json'), 'Unknown own example format')
                    self.reference('docs/renovate/examples/' + path.name)
                return OWNER + '/tree/main/docs/renovate/examples'
            self.reference('docs/renovate/OBSERVATIONS.json')
            return OWNER + '/blob/main/docs/renovate/OBSERVATIONS.json'
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(self.source), parsed.path))
        if resolved.startswith('dist/excalidraw/files/'):
            require(self.source == 'docs/excalidraw/SAVE-RESTORE.md' and resolved.removeprefix('dist/excalidraw/files/') in EXCAL_FILES,
                    'Unknown Excalidraw local reference')
        elif resolved.startswith('dist/openrefine/files/'):
            require(self.source == 'docs/openrefine/TRANSFER.md' and resolved.removeprefix('dist/openrefine/files/') in OPENREF_FILES,
                    'Unknown OpenRefine local reference')
        else:
            raise ValueError('Unsupported local source reference: ' + target)
        require(not image or resolved.endswith('.png'), 'Only selected local PNG images')
        self.reference(resolved)
        return resolved.removeprefix('dist/') + ('#' + parsed.fragment if parsed.fragment else '')

    def inline(self, text):
        output = []; position = 0
        token = re.compile(r'!?\[[^\]\n]*\]\([^\)\n]+\)|`[^`\n]+`|\*\*[^*\n]+\*\*|__[^_\n]+__|(?<!\*)\*[^*\n]+\*(?!\*)|(?<!\w)_[^_\n]+_(?!\w)')
        for match in token.finditer(text):
            output.append(html.escape(text[position:match.start()]))
            value = match[0]
            if value.startswith('`'): output.append('<code>' + html.escape(value[1:-1]) + '</code>')
            elif value.startswith(('**', '__')): output.append('<strong>' + html.escape(value[2:-2]) + '</strong>')
            elif value.startswith(('*', '_')): output.append('<em>' + html.escape(value[1:-1]) + '</em>')
            else:
                label, target = re.fullmatch(r'!?\[([^\]]*)\]\(([^)]+)\)', value).groups()
                image = value.startswith('!'); href = self.link(target, image)
                if image:
                    output.append('<figure><img src="' + html.escape(href, quote=True) + '" alt="' + html.escape(label, quote=True)
                                  + '" loading="lazy"><figcaption>' + html.escape(label) + '</figcaption></figure>')
                else:
                    download = ' download' if href.startswith(('excalidraw/files/', 'openrefine/files/')) else ''
                    output.append('<a href="' + html.escape(href, quote=True) + '"' + download + '>' + html.escape(label) + '</a>')
            position = match.end()
        output.append(html.escape(text[position:]))
        result = ''.join(output)
        # Unparsed constructs must not silently drop text or invent behavior.
        leftovers = token.sub('', text)
        require(not re.search(r'!?\[[^\]]*\]\(|\[\^|~~', leftovers), 'Unsupported inline Markdown construct')
        return result

    def heading(self, level, text):
        plain = re.sub(r'[`*]', '', text)
        name = unicodedata.normalize('NFKD', plain).encode('ascii', 'ignore').decode().lower()
        name = re.sub('[^a-z0-9]+', '-', name).strip('-') or 'section'
        original = name; counter = 2
        while name in self.ids: name = original + '-' + str(counter); counter += 1
        self.ids.add(name)
        if level > 1: self.headings.append({'id': name, 'title': plain, 'level': level})
        return '<h' + str(level) + ' id="' + name + '" tabindex="-1">' + self.inline(text) + '</h' + str(level) + '>'

    def render(self, markdown):
        privacy(markdown)
        lines = markdown.splitlines(); blocks = []; i = 0; title = None
        while i < len(lines):
            line = lines[i]; i += 1
            if not line.strip(): continue
            if line.startswith('```'):
                language = line[3:]
                require(bool(re.fullmatch('[A-Za-z0-9_-]*', language)), 'Unsupported fence syntax')
                content = []
                while i < len(lines) and lines[i] != '```': content.append(lines[i]); i += 1
                require(i < len(lines), 'Unclosed code fence'); i += 1
                blocks.append(('code', '<pre tabindex="0" aria-label="Código do procedimento"><code>' + html.escape('\n'.join(content)) + '</code></pre>')); continue
            match = re.fullmatch(r'(#{1,6}) (.+)', line)
            if match:
                level = len(match[1])
                if level == 1:
                    require(title is None and not blocks, 'Exactly one leading title required'); title = re.sub(r'[`*]', '', match[2])
                    blocks.append(('title', self.heading(1, match[2])))
                else:
                    require(title is not None, 'Leading title required'); blocks.append(('heading', self.heading(level, match[2])))
                continue
            require(not re.match(r'\s*(?:>|~~~|\[\^|\[[^\]]+\]:|---\s*$|\*\*\*\s*$)', line)
                    and not re.match(r' {4}|\t|<\s*(?:/?[A-Za-z]|!|\?)', line), 'Unsupported block Markdown syntax')
            if '|' in line and i < len(lines) and re.fullmatch(r'\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|?', lines[i]):
                cells = lambda row: [x.strip() for x in row.strip().strip('|').split('|')]
                header = cells(line); alignment = cells(lines[i]); i += 1
                require(len(header) == len(alignment) and len(header) <= 16, 'Invalid table columns')
                rows = []
                while i < len(lines) and '|' in lines[i] and lines[i].strip():
                    row = cells(lines[i]); i += 1; require(len(row) == len(header), 'Invalid table row')
                    rows.append('<tr>' + ''.join('<td>' + self.inline(x) + '</td>' for x in row) + '</tr>')
                blocks.append(('table', '<div class="table-wrap" tabindex="0" role="region" aria-label="Tabela do procedimento"><table><thead><tr>'
                               + ''.join('<th scope="col">' + self.inline(x) + '</th>' for x in header) + '</tr></thead><tbody>'
                               + ''.join(rows) + '</tbody></table></div>')); continue
            listed = re.match(r'^([-*]|\d+\.) (.+)', line)
            if listed:
                require(not re.match(r'\[[ xX]\] ', listed[2]), 'Task-list syntax outside this reader scope')
                kind = 'ul' if listed[1] in '-*' else 'ol'; rows = [self.inline(listed[2])]
                while i < len(lines):
                    following = re.match(r'^([-*]|\d+\.) (.+)', lines[i])
                    if not following or ('ul' if following[1] in '-*' else 'ol') != kind: break
                    require(not re.match(r'\[[ xX]\] ', following[2]), 'Task-list syntax outside this reader scope')
                    rows.append(self.inline(following[2])); i += 1
                blocks.append(('list', '<' + kind + '>' + ''.join('<li>' + x + '</li>' for x in rows) + '</' + kind + '>')); continue
            paragraph = [line]
            while i < len(lines) and lines[i].strip():
                following = lines[i]
                if following.startswith(('```', '#', '|')) or re.match(r'^([-*]|\d+\.) ', following): break
                require(not re.match(r'\s*(?:>|~~~|\[\^|\[[^\]]+\]:)', following)
                        and not re.match(r' {4}|\t|<\s*(?:/?[A-Za-z]|!|\?)', following), 'Unsupported paragraph Markdown')
                paragraph.append(following); i += 1
            content = ' '.join(paragraph)
            require(not re.search(r'<\s*(?:/?[A-Za-z]|!|\?)', content), 'Raw HTML outside a code fence is unsupported')
            rendered = self.inline(content)
            if '![' in content:
                require(bool(re.fullmatch(r'!\[[^\]]*\]\([^)]+\)', content)), 'Images must be separate known blocks')
                blocks.append(('figure', rendered))
            else:
                blocks.append(('paragraph', '<p>' + rendered + '</p>'))
        require(title is not None, 'Leading title required')
        intro = blocks.pop(0)[1]
        if blocks and blocks[0][0] == 'paragraph': intro += blocks.pop(0)[1].replace('<p>', '<p class="intro">', 1)
        toc = ''.join('<li class="toc-level-' + str(x['level']) + '"><a href="#' + x['id'] + '">' + html.escape(x['title']) + '</a></li>' for x in self.headings)
        body = ''.join(x[1] for x in blocks)
        page = ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
                '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'self\'; img-src \'self\'; base-uri \'none\'">'
                '<title>' + html.escape(title) + '</title><link rel="stylesheet" href="assets/reader.css"></head><body>'
                '<a class="skip-link" href="#main">Ir para o conteúdo</a><header class="site-header"><a class="brand" href="index.html"><span class="brand-mark" aria-hidden="true">PK</span>Conhecimento de produto</a>'
                '<nav aria-label="Navegação principal"><a href="library.html">Biblioteca</a></nav></header>'
                '<div class="reader-layout"><aside class="reader-toc"><nav aria-label="Neste procedimento"><h2>Neste procedimento</h2><ul>' + toc + '</ul></nav></aside>'
                '<main id="main" class="reader-main" tabindex="-1"><article class="reader-content"><header class="reader-intro"><p class="eyebrow">Procedimento próprio</p>'
                + intro + '<p class="reader-meta"><a href="' + OWNER + '/blob/main/' + self.source + '">Fonte Markdown pública</a> · sem aceite externo.</p></header>' + body
                + '</article></main></div><footer class="site-footer"><a href="library.html">Voltar à biblioteca</a></footer></body></html>')
        return page.encode('utf-8')


def compile_tree(root):
    root = safe_path(root); inputs = {}
    inherited = inventory(root / 'dist')
    for path, raw in inherited.items(): inputs['dist/' + path] = raw
    css = read_file(root / CSS); privacy(css.decode('utf-8')); inputs[CSS] = css
    inputs['scripts/build_readers.py'] = read_file(root / 'scripts/build_readers.py')
    output = dict(inherited); references = {}; reference_sets = {}; sources = []
    for source, target in DOCUMENTS.items():
        raw = read_file(root / source); require(len(raw) <= 256*1024, 'Markdown source size bound')
        inputs[source] = raw
        renderer = Renderer(root, source, target, inputs)
        output[target] = renderer.render(raw.decode('utf-8'))
        references.update(renderer.references); reference_sets.update(renderer.reference_sets)
        sources.append({'path': source, 'bytes': len(raw), 'sha256': digest(raw), 'output': target})
    require('index.html' in output and 'library.html' in output, 'Existing entry/library required')
    # Fixed original product pages; historical dist and canonical guides stay untouched.
    site = {'site/workspace.html': 'workspace.html', 'site/workspace-site.css': 'workspace-site.css',
            'site/workspace-entry.html': None}
    for source, target in site.items():
        raw = read_file(root / source); privacy(raw.decode('utf-8')); inputs[source] = raw
        if target: output[target] = raw
    entry = inputs['site/workspace-entry.html'].decode('utf-8')
    for target in ('index.html', 'library.html'):
        page = output[target].decode('utf-8')
        require(page.count('</head>') == 1 and page.count('</header>') == 1, 'Entry anchors ambiguous')
        page = page.replace('</head>', '<link rel="stylesheet" href="workspace-site.css"></head>')
        page = page.replace('</header>', '</header>' + entry, 1)
        output[target] = page.encode('utf-8')
    output[CSS] = css
    # Ignore inherited generated manifest; this pipeline owns its deterministic replacement.
    output.pop(MANIFEST, None)
    require(sum(map(len, output.values())) <= MAX_TOTAL, 'Generated output size bound')
    record = {'schema': 1, 'generator': 'scripts/build_readers.py', 'inputs': [{'path': p, 'bytes': len(b), 'sha256': digest(b)} for p,b in sorted(inputs.items())],
              'sources': sources, 'references': [references[p] for p in sorted(references)],
              'reference_sets': [{'path': p, 'entries': reference_sets[p]} for p in sorted(reference_sets)],
              'outputs': [{'path': p, 'bytes': len(b), 'sha256': digest(b)} for p,b in sorted(output.items())],
              'classification': 'own_public_reader_reproduction', 'remote_publication': False}
    output[MANIFEST] = canonical(record)
    require(sum(map(len, output.values())) <= MAX_TOTAL, 'Manifest/output size bound')
    return output, record


def unchanged_inputs(root, record):
    for item in record['inputs']:
        raw = read_file(root / item['path'])
        require(len(raw) == item['bytes'] and digest(raw) == item['sha256'], 'Input changed during build: ' + item['path'])
    for group in record['reference_sets']:
        folder = safe_path(root / group['path'])
        require(folder.is_dir() and sorted(x.name for x in folder.iterdir()) == group['entries'], 'Referenced example entry set changed during build')
    actual = set(inventory(root / 'dist'))
    before = {x['path'].removeprefix('dist/') for x in record['inputs'] if x['path'].startswith('dist/')}
    require(actual == before, 'Inherited input entry set changed during build')


def build(root, destination):
    root = safe_path(root); output = private_output(root, destination)
    require(not output.exists(), 'Existing output will never be overwritten')
    files, record = compile_tree(root); unchanged_inputs(root, record)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.' + output.name + '-', dir=output.parent))
    try:
        for name, raw in sorted(files.items()):
            path = temporary / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        unchanged_inputs(root, record)
        require(not output.exists(), 'Output appeared concurrently')
        os.rename(temporary, output)
    finally:
        if temporary.exists(): shutil.rmtree(temporary)
    return {'status': 'generated_temporary', 'reader_count': 3, 'files': len(files), 'manifest_sha256': digest(files[MANIFEST]), 'remote_publication': False}


def check(root, destination):
    root = safe_path(root); output = private_output(root, destination)
    require(output.is_dir(), 'Missing frozen output')
    expected, record = compile_tree(root); actual = inventory(output)
    require(set(actual) == set(expected), 'Frozen output entry set drift')
    for name, raw in expected.items(): require(actual[name] == raw, 'Frozen output/source/reference drift: ' + name)
    unchanged_inputs(root, record)
    return {'status': 'matched', 'reader_count': 3, 'files': len(expected), 'manifest_sha256': digest(expected[MANIFEST]), 'remote_publication': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True); parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    print(json.dumps(check(args.root, args.output) if args.check else build(args.root, args.output), ensure_ascii=False))

if __name__ == '__main__':
    try: main()
    except (ValueError, OSError, UnicodeError, KeyError) as error: raise SystemExit('Reader pipeline refused: ' + str(error))
