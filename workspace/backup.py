"""Private portable backup. Restore data only, never SQL, code or sessions."""
import argparse
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import tempfile
import zipfile

from engine import Desk, DeskError, _hash, _identifier, _json, _now, _safe_path

MAX_BYTES = 32 * 1024 * 1024
MAX_ENTRIES = 4096
FORMAT = 'knowledge-workspace-private-backup'
TABLES = {
    'projects': 'id name revision active_release_id created_at metadata',
    'sources': 'id project_id data revision',
    'snapshots': 'id source_id revision content sha256 created_at data',
    'procedures': 'id project_id data revision',
    'articles': 'id project_id data revision review',
    'releases': 'id project_id manifest manifest_sha256 created_at note',
    'history': 'id project_id action details created_at',
}


def fail(message):
    raise DeskError('invalid_backup', message)


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: fail('Chave JSON duplicada.')
            result[key] = value
        return result
    def constant(value): fail('Constante JSON inválida.')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def export(desk):
    """Read one database snapshot; release directories are immutable."""
    with desk._lock, desk._connect() as db:
        db.execute('BEGIN')
        rows = {table: [dict(row) for row in db.execute(
            f'SELECT {columns.replace(" ", ",")} FROM {table} ORDER BY rowid')]
            for table, columns in TABLES.items()}
        values = {'records.json': (_json(rows) + '\n').encode()}
        total = len(values['records.json'])
        if total > MAX_BYTES: fail('Backup excede 32 MiB descomprimidos.')
        for release in rows['releases']:
            _, files = desk._verified_release(db, release['project_id'], release['id'])
            for name, raw in files.items():
                values[f'releases/{release["project_id"]}/{release["id"]}/{name}'] = raw
                total += len(raw)
            if total > MAX_BYTES or len(values) >= MAX_ENTRIES:
                fail('Backup excede 32 MiB ou 4096 entradas.')
        manifest = {'format': FORMAT, 'version': 1, 'private': True, 'created_at': _now(),
                    'counts': {t: len(r) for t, r in rows.items()},
                    'files': [{'path': n, 'bytes': len(b), 'sha256': _hash(b)} for n, b in sorted(values.items())]}
        values['backup.json'] = (_json(manifest) + '\n').encode()
        if sum(map(len, values.values())) > MAX_BYTES: fail('Backup excede 32 MiB.')
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as z:
            for name, raw in sorted(values.items()):
                entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = 0o100600 << 16
                entry.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(entry, raw)
        if output.tell() > MAX_BYTES: fail('ZIP excede 32 MiB.')
        return output.getvalue()


def read_archive(path):
    path = _safe_path(path)
    if not path.is_file() or path.stat().st_size > MAX_BYTES: fail('ZIP ausente ou acima de 32 MiB.')
    with zipfile.ZipFile(path) as z:
        entries = z.infolist()
        if not 2 <= len(entries) <= MAX_ENTRIES: fail('Quantidade de entradas inválida.')
        if sum(x.file_size for x in entries) > MAX_BYTES: fail('Backup excede 32 MiB descomprimidos.')
        names = set()
        for entry in entries:
            name = entry.filename
            if name in names: fail('Entrada ZIP duplicada.')
            names.add(name)
            if (entry.is_dir() or entry.flag_bits & 1
                    or stat.S_IFMT(entry.external_attr >> 16) not in (0, stat.S_IFREG)
                    or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                    or not re.fullmatch(r'[A-Za-z0-9_.\-/]+', name)
                    or any(x in ('', '.', '..') for x in name.split('/'))):
                fail('Entrada ZIP não permitida.')
        if not {'backup.json', 'records.json'} <= names: fail('Manifesto ou registros ausentes.')
        values = {x.filename: z.read(x) for x in entries}
    manifest = decode(values.pop('backup.json'))
    if (not isinstance(manifest, dict) or manifest.get('format') != FORMAT
            or type(manifest.get('version')) is not int or manifest['version'] != 1
            or manifest.get('private') is not True): fail('Formato de backup incompatível.')
    records = manifest.get('files')
    if not isinstance(records, list): fail('Manifesto inválido.')
    expected = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != {'path', 'bytes', 'sha256'}:
            fail('Registro de integridade inválido.')
        name = record['path']
        if not isinstance(name, str) or name in expected: fail('Caminho duplicado no manifesto.')
        expected[name] = record
    if set(values) != set(expected): fail('Arquivos adicionais ou ausentes.')
    for name, value in values.items():
        r = expected[name]
        if type(r['bytes']) is not int or r['bytes'] != len(value) or r['sha256'] != _hash(value):
            fail('Integridade do backup divergente.')
    rows = decode(values.pop('records.json'))
    if not isinstance(rows, dict) or set(rows) != set(TABLES): fail('Tabelas incompatíveis.')
    for table, columns in TABLES.items():
        if not isinstance(rows[table], list): fail('Lista de registros inválida.')
        for row in rows[table]:
            if not isinstance(row, dict) or set(row) != set(columns.split()): fail('Colunas incompatíveis.')
            for key, value in row.items():
                integer = key == 'revision' or key == 'id' and table in ('snapshots', 'history')
                nullable = key in ('active_release_id', 'review') or table == 'snapshots' and key == 'data'
                if integer:
                    if type(value) is not int or value < 1: fail('Número de registro inválido.')
                elif not (isinstance(value, str) or nullable and value is None): fail('Valor de registro inválido.')
    if manifest.get('counts') != {t: len(r) for t, r in rows.items()}: fail('Contagens divergentes.')
    return rows, values


def validate(desk, rows, values):
    """Check relationships using the trusted schema, never import a database."""
    with desk._connect() as db:
        for table, columns in TABLES.items():
            cols = columns.split()
            db.executemany(f'INSERT INTO {table} ({",".join(cols)}) VALUES ({",".join("?" for _ in cols)})',
                           [[r[c] for c in cols] for r in rows[table]])
        if db.execute('PRAGMA foreign_key_check').fetchall(): fail('Vínculos inválidos.')
        for row in rows['projects']:
            _identifier(row['id'], 'p')
            metadata = decode(row['metadata'])
            if not isinstance(metadata, dict) or set(metadata) != {'purpose', 'authority', 'limits'}:
                fail('Metadados de projeto inválidos.')
            if any(not isinstance(x, str) for x in metadata.values()): fail('Metadados inválidos.')
            if row['active_release_id'] and not db.execute(
                    'SELECT id FROM releases WHERE id=? AND project_id=?',
                    (row['active_release_id'], row['id'])).fetchone(): fail('Publicação ativa ausente.')
        for table, prefix in (('sources', 's'), ('procedures', 't'), ('articles', 'a')):
            for row in rows[table]:
                _identifier(row['id'], prefix)
                data = decode(row['data'])
                if not isinstance(data, dict): fail('Conteúdo inválido.')
                if table == 'sources': desk._source(data)
                elif table == 'procedures': desk._procedure(db, row['project_id'], data)
                else:
                    desk._article(db, row['project_id'], data)
                    if row['review'] is not None and not isinstance(decode(row['review']), dict):
                        fail('Revisão inválida.')
        for row in rows['snapshots']:
            if row['data'] is not None:
                data = decode(row['data']); desk._source(data)
                if data['content'] != row['content'] or _hash(_json({k: data[k] for k in ('content', 'files')})) != row['sha256']:
                    fail('Histórico da fonte divergente.')
        for row in rows['history']:
            if not isinstance(decode(row['details']), dict): fail('Histórico inválido.')
        expected = set()
        for row in rows['releases']:
            _identifier(row['id'], 'r')
            manifest = decode(row['manifest'])
            if manifest.get('id') != row['id'] or manifest.get('format') != 'public-reader-only':
                fail('Identidade da publicação divergente.')
            prefix = f'releases/{row["project_id"]}/{row["id"]}/'
            for item in manifest['files'] + [{'path': 'manifest.json'}]:
                name = item['path']
                if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.\-/]+', name) or any(
                        x in ('', '.', '..') for x in name.split('/')): fail('Caminho de publicação inválido.')
                target_name = prefix + name
                if target_name in expected or target_name not in values: fail('Publicação duplicada ou incompleta.')
                expected.add(target_name)
                target = desk.releases_path.parent / target_name
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                with target.open('xb') as f: f.write(values[target_name])
                target.chmod(0o600)
            desk._verified_release(db, row['project_id'], row['id'])
        if expected != set(values): fail('Arquivos fora das publicações registradas.')
        for row in rows['projects']: desk._project(db, row['id'])


def restore(archive, destination):
    destination = _safe_path(destination)
    if destination.exists(): fail('Destino já existe. Escolha uma pasta nova, sem sobrescrita.')
    if not destination.parent.is_dir(): fail('A pasta pai do destino precisa existir.')
    try:
        rows, values = read_archive(archive)
        with tempfile.TemporaryDirectory(prefix='.workspace-restore-', dir=destination.parent) as temp:
            staging = Path(temp)
            desk = Desk(staging/'content.sqlite3', staging/'releases')
            validate(desk, rows, values)
            # Reserve exclusively; never replace an existing directory or remove it on failure.
            destination.mkdir(mode=0o700)
            os.rename(staging/'content.sqlite3', destination/'content.sqlite3')
            (destination/'content.sqlite3').chmod(0o600)
            os.rename(staging/'releases', destination/'releases')
            # Last marker: an interrupted restore is not adopted as a working workspace.
            with (destination/'workspace.json').open('x') as f:
                json.dump({'product': 'product-knowledge-workspace', 'schema': 1}, f)
            (destination/'workspace.json').chmod(0o600)
        return {'restored': str(destination), 'counts': {t: len(r) for t, r in rows.items()},
                'session': 'New session created only when serve.py starts; no credentials restored.'}
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError, sqlite3.Error,
            zipfile.BadZipFile, zipfile.LargeZipFile, NotImplementedError) as exc:
        raise DeskError('invalid_backup', 'Backup inválido ou incompatível; restauração recusada.') from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['restore'])
    parser.add_argument('archive', type=Path)
    parser.add_argument('--to', type=Path, required=True)
    args = parser.parse_args(); os.umask(0o077)
    try: print(json.dumps(restore(args.archive, args.to), ensure_ascii=False))
    except (DeskError, OSError) as exc: parser.exit(2, str(exc) + '\n')


if __name__ == '__main__': main()
