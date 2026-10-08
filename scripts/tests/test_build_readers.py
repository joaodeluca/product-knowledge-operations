"""New finite tests of the three-reader source pipeline, own isolated fixtures."""
import hashlib
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'build_readers.py'
spec = importlib.util.spec_from_file_location('build_readers', MODULE)
builder = importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)

class HTML(HTMLParser):
    def __init__(self, raw):
        super().__init__(); self.text=[]; self.tags=[]; self.feed(raw.decode())
    def handle_data(self, value): self.text.append(value)
    def handle_starttag(self, tag, attrs): self.tags.append((tag,dict(attrs)))

class ReaderPipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name).resolve()
        self.repo=self.root/'source'; self.repo.mkdir(); (self.repo/'.git').mkdir()
        (self.repo/'scripts').mkdir(); (self.repo/'scripts/build_readers.py').write_bytes(MODULE.read_bytes())
        (self.repo/'assets').mkdir(); (self.repo/'assets/reader.css').write_text('body{color:#123}img{max-width:100%}')
        (self.repo/'dist').mkdir()
        for name in ('index.html','library.html'): (self.repo/'dist'/name).write_text('<!doctype html><html><head></head><body><header>Own header</header>Own existing library</body></html>')
        for name in ('excalidraw.html','openrefine.html','renovate.html'): (self.repo/'dist'/name).write_text('<html>Obsolete own reader</html>')
        ex=self.repo/'dist/excalidraw/files'; ex.mkdir(parents=True)
        for name in builder.EXCAL_FILES:
            (ex/name).write_bytes(b'Own original image bytes' if name.endswith('.png') else b'{"type":"excalidraw","elements":[]}' if name.endswith('.excalidraw') else b'{}')
        ref=self.repo/'dist/openrefine/files'; ref.mkdir(parents=True)
        for name in builder.OPENREF_FILES: (ref/name).write_bytes(b'Own original fixture')
        for source in builder.DOCUMENTS: (self.repo/source).parent.mkdir(parents=True,exist_ok=True)
        self.ex=self.repo/'docs/excalidraw/SAVE-RESTORE.md'
        self.ex.write_text('# Draw safely\n\nUse **own original** files. Prior04/10 FAILED remains.\n\n## Added after maintenance\n\nPreserve this new sentence and all limits.\n\n![Own diagram](../../dist/excalidraw/files/diagram.png)\n\n[Original editable]('+builder.OWNER+'/releases/download/help-2026-10-05/scene-original.excalidraw)\n')
        self.ref=self.repo/'docs/openrefine/TRANSFER.md'
        self.ref.write_text('# Transfer own project\n\nNo client/economy. API127.0.0.1 csrf_token=TOKEN are public placeholders.\n\n## Steps\n\n1. Preserve IDs00001.\n2. Inspect original failure.\n\n|Case|Result|\n|---|---|\n|CSV undo|FAILED|\n\n```sh\n<script>alert("literal escaped code")</script>\n```\n\n[Own fullCSV](../../dist/openrefine/files/full.csv)\n')
        self.ren=self.repo/'docs/renovate/VALIDATION.md'
        self.ren.write_text('# Validate own configuration\n\nRE2 not loaded; no regex certification.\n\n## Own samples\n\n[Examples](examples/) [Observed controls](OBSERVATIONS.json).\n')
        examples=self.ren.parent/'examples'; examples.mkdir(); (examples/'own.json').write_text('{"automerge":false}')
        (self.ren.parent/'OBSERVATIONS.json').write_text('{"synthetic":true}')
        (self.repo/'site').mkdir()
        for name in ('workspace.html','workspace-site.css','workspace-entry.html'):
            (self.repo/'site'/name).write_bytes((MODULE.parent.parent/'site'/name).read_bytes())
        self.out=self.root/'frozen-output'

    def tearDown(self): self.tmp.cleanup()
    def build(self): return builder.build(self.repo,self.out)

    def test_product_entry_and_page_are_bound_to_manifest_without_dist_mutation(self):
        original=(self.repo/'dist/library.html').read_bytes();self.build()
        self.assertIn(b'workspace.html',(self.out/'library.html').read_bytes())
        self.assertEqual((self.out/'workspace.html').read_bytes(),(self.repo/'site/workspace.html').read_bytes())
        self.assertEqual((self.repo/'dist/library.html').read_bytes(),original)
        for path in (self.repo/'site/workspace.html',self.repo/'site/workspace-entry.html'):
            raw=path.read_bytes();path.write_bytes(raw+b'changed')
            with self.assertRaises(ValueError):builder.check(self.repo,self.out)
            path.write_bytes(raw)

    def test_three_readers_preserve_words_source_limits_and_escape_code(self):
        original={p.relative_to(self.repo/'dist').as_posix():p.read_bytes() for p in (self.repo/'dist').rglob('*') if p.is_file()}
        result=self.build(); self.assertEqual(result['reader_count'],3)
        ex=HTML((self.out/'excalidraw.html').read_bytes())
        self.assertIn('Preserve this new sentence and all limits.',''.join(ex.text))
        self.assertIn('Prior04/10 FAILED remains.',''.join(ex.text))
        self.assertNotIn(b'<p><figure>',(self.out/'excalidraw.html').read_bytes())
        ref=HTML((self.out/'openrefine.html').read_bytes())
        self.assertIn('<script>alert("literal escaped code")</script>',''.join(ref.text))
        self.assertFalse(any(tag=='script' for tag,_ in ref.tags))
        self.assertTrue(any(tag=='table' for tag,_ in ref.tags))
        self.assertTrue(any(tag=='pre' and attrs.get('tabindex')=='0' for tag,attrs in ref.tags))
        self.assertTrue(any(tag=='main' and attrs.get('id')=='main' for tag,attrs in ex.tags))
        self.assertEqual(original,{p.relative_to(self.repo/'dist').as_posix():p.read_bytes() for p in (self.repo/'dist').rglob('*') if p.is_file()})
        builder.check(self.repo,self.out)

    def test_rewrites_only_known_own_local_assets_and_canonical_renovate(self):
        self.build(); ex=HTML((self.out/'excalidraw.html').read_bytes())
        self.assertTrue(any(tag=='img' and a.get('src')=='excalidraw/files/diagram.png' for tag,a in ex.tags))
        self.assertTrue(any(tag=='a' and a.get('href')=='excalidraw/files/scene-original.excalidraw' and 'download' in a for tag,a in ex.tags))
        ren=HTML((self.out/'renovate.html').read_bytes())
        self.assertTrue(any(a.get('href')==builder.OWNER+'/tree/main/docs/renovate/examples' for _,a in ren.tags))
        self.assertTrue(any(a.get('href')==builder.OWNER+'/blob/main/docs/renovate/OBSERVATIONS.json' for _,a in ren.tags))
        manifest=json.loads((self.out/builder.MANIFEST).read_bytes())
        refs={x['path']:x for x in manifest['references']}
        raw=(self.repo/'dist/excalidraw/files/diagram.png').read_bytes()
        self.assertEqual(refs['dist/excalidraw/files/diagram.png']['sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual((self.out/'excalidraw/files/diagram.png').read_bytes(),raw)
        self.assertNotIn('timestamp',manifest); self.assertNotIn('git_head',manifest)

    def test_deterministic_two_isolated_fixture_builds(self):
        first=self.build(); other=self.root/'other-output'; second=builder.build(self.repo,other)
        self.assertEqual(first,second)
        self.assertEqual((self.out/builder.MANIFEST).read_bytes(),(other/builder.MANIFEST).read_bytes())
        for path in self.out.rglob('*'):
            if path.is_file(): self.assertEqual(path.read_bytes(),(other/path.relative_to(self.out)).read_bytes())

    def test_check_rejects_source_asset_output_or_css_drift_no_writes(self):
        self.build(); frozen={p.relative_to(self.out).as_posix():p.read_bytes() for p in self.out.rglob('*') if p.is_file()}
        for path in (self.ex,self.repo/'dist/excalidraw/files/diagram.png',self.repo/'assets/reader.css',self.out/'openrefine.html'):
            with self.subTest(path=path.name):
                raw=path.read_bytes(); path.write_bytes(raw+b'changed')
                with self.assertRaises(ValueError): builder.check(self.repo,self.out)
                path.write_bytes(raw)
        self.assertEqual(frozen,{p.relative_to(self.out).as_posix():p.read_bytes() for p in self.out.rglob('*') if p.is_file()})

    def test_missing_reference_rejects_before_output_creation(self):
        (self.repo/'dist/excalidraw/files/diagram.png').unlink()
        with self.assertRaises(ValueError): self.build()
        self.assertFalse(self.out.exists())

    def test_unsupported_markdown_rejects_without_partial_payload(self):
        original=self.ex.read_text()
        for suffix in ('\n> Quoted unsupported\n','\n[^note]: Footnote\n','\n- [x] Checklist task\n','\n```sh\nunclosed\n','\n<script>alert(1)</script>\n'):
            with self.subTest(suffix=suffix):
                self.ex.write_text(original+suffix)
                with self.assertRaises(ValueError): self.build()
                self.assertFalse(self.out.exists())

    def test_private_paths_ids_urls_unsafe_or_unmapped_links_refused(self):
        original=self.ex.read_text()
        for suffix in ('\n/Users/person/private.md\n','\np_'+'a'*32+'\n','\nhttps://host/?session=abcdefgh12345678\n',
                       '\n[bad](javascript:alert)\n','\n![remote](https://example.org/image.png)\n','\n[private](http://127.0.0.1:8795/)\n',
                       '\n[escape](../../../../private/secrets.json)\n','\n[unknown](../../dist/excalidraw/files/new-unknown.json)\n'):
            with self.subTest(suffix=suffix):
                self.ex.write_text(original+suffix)
                with self.assertRaises(ValueError): self.build()
                self.assertFalse(self.out.exists())

    def test_symlink_input_asset_or_output_refused(self):
        image=self.repo/'dist/excalidraw/files/diagram.png'; original=image.read_bytes(); image.unlink(); image.symlink_to(self.ex)
        with self.assertRaises(ValueError): self.build()
        image.unlink(); image.write_bytes(original)
        linked=self.root/'linked-output'; linked.symlink_to(self.out)
        with self.assertRaises(ValueError): builder.build(self.repo,linked)
        self.assertFalse(self.out.exists())

    def test_existing_output_and_inside_git_output_never_overwritten(self):
        self.build(); raw=(self.out/builder.MANIFEST).read_bytes()
        with self.assertRaises(ValueError): self.build()
        self.assertEqual((self.out/builder.MANIFEST).read_bytes(),raw)
        with self.assertRaises(ValueError): builder.build(self.repo,self.repo/'generated')
        elsewhere=self.root/'git-output'; elsewhere.mkdir(); (elsewhere/'.git').mkdir()
        with self.assertRaises(ValueError): builder.build(self.repo,elsewhere/'generated')

    def test_input_mutation_during_build_refuses_atomic_output(self):
        original=builder.compile_tree
        def mutate(root):
            compiled=original(root); self.ex.write_text(self.ex.read_text()+'\nChanged while building\n'); return compiled
        with patch.object(builder,'compile_tree',side_effect=mutate):
            with self.assertRaises(ValueError): self.build()
        self.assertFalse(self.out.exists())

    def test_new_example_created_during_build_refuses_partial_output(self):
        original=builder.compile_tree
        def mutate(root):
            compiled=original(root)
            (self.repo/'docs/renovate/examples/new.json').write_text('{"own":true}')
            return compiled
        with patch.object(builder,'compile_tree',side_effect=mutate):
            with self.assertRaises(ValueError): self.build()
        self.assertFalse(self.out.exists())

    def test_unexpected_output_entry_or_symlink_detected_check(self):
        self.build(); extra=self.out/'extra.json'; extra.write_text('{}')
        with self.assertRaises(ValueError): builder.check(self.repo,self.out)
        extra.unlink(); image=self.out/'excalidraw/files/diagram.png'; image.unlink(); image.symlink_to(self.ex)
        with self.assertRaises(ValueError): builder.check(self.repo,self.out)

if __name__=='__main__': unittest.main()
