"""Local editorial workspace. Sources and reviewers are self-declared.
No network, accounts, external acceptance or billing.
"""
from __future__ import annotations

import hashlib
import base64
import binascii
import struct
import zlib
from contextlib import contextmanager
import html
import io
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import sqlite3
import threading
from datetime import datetime, timezone
import uuid
import zipfile


MAX_SOURCE_BYTES = 512 * 1024
MAX_ARTICLE_BYTES = 256 * 1024
MAX_RELEASE_BYTES = 8 * 1024 * 1024
MAX_ITEMS = 64
CLASSIFICATION = "local_editorial_workspace"


class DeskError(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _now():
    return datetime.now(timezone.utc).isoformat()


def _hash(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode("utf-8")).hexdigest()


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _identifier(value, prefix):
    if not isinstance(value, str) or not re.fullmatch(prefix + r"_[0-9a-f]{32}", value):
        raise DeskError("invalid_id", "Identificador inválido.")
    return value


def _text(value, name, maximum=8192, required=True):
    if isinstance(value, list) and all(isinstance(x, str) for x in value):
        value = "\n".join(value)
    if not isinstance(value, str) or "\x00" in value:
        raise DeskError("invalid_text", f"{name}: texto necessário, sem byte nulo.")
    if len(value.encode("utf-8")) > maximum:
        raise DeskError("oversize", f"{name}: limite de {maximum} bytes ultrapassado.", 413)
    if required and not value.strip():
        raise DeskError("required", f"{name}: campo obrigatório.")
    return value


def _content(value, name, maximum):
    value = _text(value, name, maximum)
    # Renderer is escaped as a second barrier. HTML is deliberately outside this
    # operation, including inline tags, even inside Markdown code fences.
    if re.search(r"<\s*(?:/?[A-Za-z][A-Za-z0-9:-]*(?:\s|/?>)|!|\?)", value):
        raise DeskError("unsafe_html", f"{name}: HTML não é aceito nesta mesa.")
    if re.search(r"\]\(\s*(?:javascript|data|vbscript|file):", value, re.I):
        raise DeskError("unsafe_link", f"{name}: esquema de link não permitido.")
    return value



def _png(data):
    """Finite PNG envelope and scanline check, not an image-authority claim."""
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise DeskError("invalid_png", "Assinatura PNG inválida.")
    offset, chunks, payload, expected = 8, 0, bytearray(), None
    seen_data, ended_data, ended, palette = False, False, False, False
    while offset < len(data):
        if offset + 12 > len(data) or chunks >= 256:
            raise DeskError("invalid_png", "Chunks PNG truncados ou excessivos.")
        size = struct.unpack(">I", data[offset:offset+4])[0]
        kind = data[offset+4:offset+8]
        stop = offset + 12 + size
        if stop > len(data) or not re.fullmatch(b"[A-Za-z]{4}", kind) or not 65 <= kind[2] <= 90:
            raise DeskError("invalid_png", "Chunk PNG inválido.")
        body = data[offset+8:offset+8+size]
        crc = struct.unpack(">I", data[offset+8+size:stop])[0]
        if (binascii.crc32(kind + body) & 0xffffffff) != crc:
            raise DeskError("invalid_png", "CRC PNG divergente.")
        if chunks == 0 and kind != b"IHDR":
            raise DeskError("invalid_png", "IHDR deve ser o primeiro chunk.")
        if kind == b"IHDR":
            if chunks != 0 or size != 13:
                raise DeskError("invalid_png", "IHDR duplicado/inválido.")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", body)
            if not (1 <= width <= 2048 and 1 <= height <= 2048 and width*height <= 4*1024*1024
                    and depth == 8 and color in (2, 6) and compression == filtering == interlace == 0):
                raise DeskError("unsupported_png", "Somente PNG RGB/RGBA8 não entrelaçado, até2048×2048/4M pixels.")
            stride = 1 + width * (3 if color == 2 else 4)
            expected = stride * height
            if expected > 16 * 1024 * 1024:
                raise DeskError("oversize", "Limite de scanlines PNG ultrapassado.", 413)
        elif kind == b"IDAT":
            if ended_data:
                raise DeskError("invalid_png", "IDAT deve ser consecutivo.")
            seen_data = True; payload.extend(body)
        elif kind == b"IEND":
            if size or not seen_data or stop != len(data):
                raise DeskError("invalid_png", "IEND inválido ou bytes posteriores.")
            ended = True
        elif kind == b"PLTE":
            if palette or seen_data or size == 0 or size > 768 or size % 3:
                raise DeskError("invalid_png", "PLTE inválido.")
            palette = True
        elif kind in (b"acTL", b"fcTL", b"fdAT", b"iCCP", b"zTXt", b"iTXt"):
            raise DeskError("unsupported_png", "PNG animado ou metadados comprimidos fora deste recorte.")
        elif kind == b"sRGB" and (size != 1 or body[0] > 3):
            raise DeskError("invalid_png", "sRGB inválido.")
        elif kind == b"pHYs" and (size != 9 or body[8] > 1):
            raise DeskError("invalid_png", "pHYs inválido.")
        elif kind == b"gAMA" and (size != 4 or body == b"\x00"*4):
            raise DeskError("invalid_png", "gAMA inválido.")
        elif kind == b"cHRM" and size != 32:
            raise DeskError("invalid_png", "cHRM inválido.")
        elif kind == b"tRNS" and (color != 2 or size != 6):
            raise DeskError("invalid_png", "tRNS fora do formato RGB8.")
        elif kind == b"sBIT" and (size != (3 if color == 2 else 4) or any(not 1 <= x <= 8 for x in body)):
            raise DeskError("invalid_png", "sBIT inválido.")
        elif kind[0] < 97:
            raise DeskError("unsupported_png", "Chunk crítico PNG não suportado.")
        if seen_data and kind != b"IDAT": ended_data = True
        offset = stop; chunks += 1
    if not ended or expected is None:
        raise DeskError("invalid_png", "PNG incompleto.")
    try:
        decompressor = zlib.decompressobj()
        scanlines = decompressor.decompress(bytes(payload), expected + 1)
    except zlib.error as exc:
        raise DeskError("invalid_png", "IDAT zlib inválido.") from exc
    if (len(scanlines) != expected or not decompressor.eof or decompressor.unconsumed_tail
            or decompressor.unused_data or any(scanlines[n] > 4 for n in range(0, expected, stride))):
        raise DeskError("invalid_png", "Dados PNG/filtros/tamanho descomprimido inválidos.")


def _asset_bytes(item):
    encoding = item.get("encoding", "utf8")
    content = item.get("content")
    if not isinstance(content, str):
        raise DeskError("invalid_files", "Conteúdo do arquivo precisa ser textual UTF8/base64.")
    if encoding == "utf8":
        return content.encode("utf-8")
    if encoding != "base64" or len(content) > 4*((256*1024+2)//3):
        raise DeskError("invalid_encoding", "Encoding permitido: utf8 ou base64 estrito limitado.")
    try:
        raw = base64.b64decode(content, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise DeskError("invalid_encoding", "Base64 inválido, sem espaços ou variante URL.") from exc
    if base64.b64encode(raw).decode("ascii") != content:
        raise DeskError("invalid_encoding", "Base64 precisa de representação canônica.")
    return raw


def _file_media(path):
    extension = path.rsplit(".", 1)[-1]
    return {"png": "image/png", "excalidraw": "application/json", "json": "application/json",
            "json5": "application/json5", "md": "text/markdown", "csv": "text/csv",
            "yaml": "application/yaml", "yml": "application/yaml", "txt": "text/plain"}[extension]


def _file_view(item):
    # Explicit API representation only; never migrate stored legacy records.
    raw = _asset_bytes(item)
    return item | {"encoding": item.get("encoding", "utf8"), "media_type": item.get("media_type", _file_media(item["path"])),
                   "bytes": len(raw), "sha256": _hash(raw)}

def _actor(data):
    value = data.get("actor")
    if not isinstance(value, dict) or value.get("kind") not in ("operator", "ai_assisted"):
        raise DeskError("reviewer_required", "Informe o tipo e o identificador local do revisor.")
    return {"kind": value["kind"], "label": _text(value.get("label"), "Revisor", 100), "identity_verified": False}


def _safe_path(path):
    path = Path(os.path.abspath(os.fspath(path)))
    for component in (path, *path.parents):
        if component.is_symlink():
            raise DeskError("unsafe_path", "Symlinks não são permitidos no armazenamento.")
        if (component / ".git").exists():
            raise DeskError("git_storage", "Dados operacionais devem ficar fora de um checkout Git.")
    return path


def _inline(value, allowed_paths):
    def token(match):
        part = match.group(0)
        if part.startswith("`"):
            return "<code>" + html.escape(part[1:-1]) + "</code>"
        if part.startswith("**"):
            return "<strong>" + html.escape(part[2:-2]) + "</strong>"
        label, href = re.fullmatch(r"!?\[([^\]]+)\]\(([^)]+)\)", part).groups()
        safe_https = bool(re.fullmatch(r"https://[A-Za-z0-9.-]+(?::[0-9]+)?(?:/[^\s<>\"'\\]*)?", href))
        local = False
        if not re.search(r"[\s<>\"'\\:#?%]", href) and not href.startswith("/"):
            target = posixpath.normpath(posixpath.join("articles", href))
            local = target in allowed_paths
        if part.startswith("!"):
            if local and target.endswith(".png"):
                return '<img src="' + html.escape(href, quote=True) + '" alt="' + html.escape(label, quote=True) + '" loading="lazy">'
            return html.escape(label)  # Never remote images, trackers or data URLs.
        if safe_https or local:
            return '<a href="' + html.escape(href, quote=True) + '" rel="noreferrer noopener">' + html.escape(label) + "</a>"
        return html.escape(part)
    output, previous = [], 0
    for match in re.finditer(r"!?\[[^\]\n]+\]\([^\)\n]+\)|`[^`\n]+`|\*\*[^\n]+?\*\*", value):
        output.append(html.escape(value[previous:match.start()])); output.append(token(match)); previous = match.end()
    output.append(html.escape(value[previous:]))
    return "".join(output)


def _render(markdown, allowed_paths):
    """Escaped headings, lists, fenced code, simple tables and safe links.

    Relative links must resolve to a selected release file. HTTPS links are
    user-declared public references, never fetched or checked by this engine.
    No raw HTML, remote images, scripts, or executable JavaScript.
    """
    output, in_code, in_list = [], False, None
    lines = markdown.splitlines(); index = 0
    while index < len(lines):
        line = lines[index]; index += 1
        if line.startswith("```"):
            if in_list:
                output.append("</" + in_list + ">"); in_list = None
            output.append("</code></pre>" if in_code else "<pre><code>")
            in_code = not in_code
        elif in_code:
            output.append(html.escape(line) + "\n")
        elif re.match(r"^\s*(?:[-*]|\d+[.)])\s+", line):
            match = re.match(r"^\s*([-*]|\d+[.)])\s+(.*)$", line)
            kind = "ul" if match[1] in "-*" else "ol"
            if in_list != kind:
                if in_list: output.append("</" + in_list + ">")
                output.append("<" + kind + ">"); in_list = kind
            output.append("<li>" + _inline(match[2], allowed_paths) + "</li>")
        else:
            if in_list:
                output.append("</" + in_list + ">"); in_list = None
            if "|" in line and index < len(lines) and re.fullmatch(r"\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*", lines[index]):
                def cells(row):
                    return row.strip().strip("|").split("|")
                output.append("<table><thead><tr>" + "".join("<th>" + _inline(x.strip(), allowed_paths) + "</th>" for x in cells(line)) + "</tr></thead><tbody>")
                index += 1
                while index < len(lines) and "|" in lines[index] and lines[index].strip():
                    output.append("<tr>" + "".join("<td>" + _inline(x.strip(), allowed_paths) + "</td>" for x in cells(lines[index])) + "</tr>")
                    index += 1
                output.append("</tbody></table>"); continue
            match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if match:
                n = len(match[1]); output.append(f"<h{n}>{_inline(match[2], allowed_paths)}</h{n}>")
            elif line.strip():
                output.append("<p>" + _inline(line, allowed_paths) + "</p>")
    if in_code:
        output.append("</code></pre>")
    if in_list:
        output.append("</" + in_list + ">")
    return "\n".join(output)


class Desk:
    def __init__(self, store_path, releases_path):
        self.store_path = _safe_path(store_path)
        self.releases_path = _safe_path(releases_path)
        if self.store_path.exists() and not self.store_path.is_file():
            raise DeskError("unsafe_path", "store_path deve ser um arquivo SQLite.")
        if self.releases_path.exists() and not self.releases_path.is_dir():
            raise DeskError("unsafe_path", "releases_path deve ser um diretório.")
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.releases_path.mkdir(parents=True, exist_ok=True)
        _safe_path(self.store_path); _safe_path(self.releases_path)
        self._lock = threading.RLock()
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, name TEXT NOT NULL,
                revision INTEGER NOT NULL, active_release_id TEXT, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                data TEXT NOT NULL, revision INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL REFERENCES sources(id), revision INTEGER NOT NULL,
                content TEXT NOT NULL, sha256 TEXT NOT NULL, created_at TEXT NOT NULL,
                UNIQUE(source_id,revision));
            CREATE TABLE IF NOT EXISTS procedures(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                data TEXT NOT NULL, revision INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS articles(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                data TEXT NOT NULL, revision INTEGER NOT NULL, review TEXT);
            CREATE TABLE IF NOT EXISTS releases(id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                manifest TEXT NOT NULL, manifest_sha256 TEXT NOT NULL, created_at TEXT NOT NULL, note TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL REFERENCES projects(id), action TEXT NOT NULL,
                details TEXT NOT NULL, created_at TEXT NOT NULL);
            """)
            if "metadata" not in [r[1] for r in db.execute("PRAGMA table_info(projects)")]:
                db.execute("ALTER TABLE projects ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'")
            if "data" not in [r[1] for r in db.execute("PRAGMA table_info(snapshots)")]:
                db.execute("ALTER TABLE snapshots ADD COLUMN data TEXT")

    @contextmanager
    def _connect(self):
        _safe_path(self.store_path); _safe_path(self.releases_path)
        for suffix in ("-wal", "-shm", "-journal"):
            _safe_path(str(self.store_path) + suffix)
        db = sqlite3.connect(str(self.store_path), timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=10000")
        try:
            with db:
                yield db
        finally:
            db.close()

    def _project_row(self, db, project_id):
        _identifier(project_id, "p")
        row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if row is None:
            raise DeskError("not_found", "Projeto não encontrado.", 404)
        return row

    def _cas(self, db, project_id, expected):
        row = self._project_row(db, project_id)
        if isinstance(expected, bool) or not isinstance(expected, int):
            raise DeskError("revision_required", "expected_revision inteira do projeto é obrigatória.", 409)
        if row["revision"] != expected:
            raise DeskError("revision_conflict", "Projeto mudou; recarregue antes de salvar.", 409)
        return row

    def _event(self, db, project_id, action, details):
        db.execute("UPDATE projects SET revision=revision+1 WHERE id=?", (project_id,))
        db.execute("INSERT INTO history(project_id,action,details,created_at) VALUES(?,?,?,?)",
                   (project_id, action, _json(details), _now()))

    def _items(self, db, table, project_id):
        result = []
        for row in db.execute(f"SELECT * FROM {table} WHERE project_id=? ORDER BY rowid", (project_id,)):
            item = json.loads(row["data"])
            item.update(id=row["id"], revision=row["revision"])
            if table == "sources":
                item["content_sha256"] = _hash(item["content"])
                item["sha256"] = _hash(_json({k: item[k] for k in ("content", "files")}))
                item["attachments"] = {x["path"]: x["content"] for x in item["files"] if x.get("encoding", "utf8") == "utf8"}
                item["files"] = [_file_view(x) for x in item["files"]]
            if table == "articles":
                item["sha256"] = _hash(item["markdown"])
                review = json.loads(row["review"]) if row["review"] else {"status": "missing"}
                if review.get("stamp"):
                    review["status"] = "current" if review["stamp"] == self._stamp(db, project_id, item) else "stale"
                item["review"] = review
            result.append(item)
        return result

    def _get(self, db, table, project_id, item_id, prefix):
        _identifier(item_id, prefix)
        row = db.execute(f"SELECT * FROM {table} WHERE project_id=? AND id=?", (project_id, item_id)).fetchone()
        if row is None:
            raise DeskError("not_found", "Registro não encontrado neste projeto.", 404)
        item = json.loads(row["data"]); item.update(id=row["id"], revision=row["revision"])
        return item

    def _links(self, db, project_id, data):
        value = data.get("source_ids", [])
        if not isinstance(value, list) or len(value) > MAX_ITEMS or len(value) != len(set(x for x in value if isinstance(x, str))):
            raise DeskError("invalid_sources", "source_ids deve ser lista de IDs distintos.")
        for source_id in value:
            self._get(db, "sources", project_id, source_id, "s")
        return value

    def _source(self, data):
        if data.get("original_owned") is not True or data.get("origin", "personal_original") != "personal_original":
            raise DeskError("ownership_required", "Somente conteúdo original próprio declarado; arquivos de terceiros não são aceitos.")
        url = _text(data.get("url", ""), "url", 2048, False)
        if url and (not re.fullmatch(r"https://[^\s]+", url) or "@" in url or "?" in url or "#" in url):
            raise DeskError("invalid_url", "Referência deve ser HTTPS pública, sem usuário, fragmento ou query; nunca é buscada.")
        files = data.get("files", [])
        attachments = data.get("attachments", {})
        if not isinstance(attachments, dict) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in attachments.items()):
            raise DeskError("invalid_files", "attachments legado deve mapear caminho textual próprio para conteúdo UTF-8.")
        if attachments and files:
            if (any(x.get("encoding", "utf8") != "utf8" for x in files if isinstance(x, dict))
                    or {x.get("path"): x.get("content") for x in files if isinstance(x, dict)} != attachments):
                raise DeskError("invalid_files", "files/attachments ambíguos; envie files completos sem attachments para fontes binárias.")
        if attachments:
            files = [{"path": key, "content": value, "original_owned": True} for key, value in attachments.items()]
        if not isinstance(files, list) or len(files) > MAX_ITEMS:
            raise DeskError("invalid_files", "files: no máximo 64 arquivos próprios.")
        preserved, names, total = [], set(), 0
        for item in files:
            if not isinstance(item, dict) or item.get("original_owned") is not True:
                raise DeskError("ownership_required", "Cada arquivo precisa de declaração original_owned:true.")
            name = item.get("path")
            if (not isinstance(name, str) or not re.fullmatch(r"(?:[a-zA-Z0-9][a-zA-Z0-9_-]*/)?[a-zA-Z0-9][a-zA-Z0-9_.-]*\.(?:json|json5|txt|md|csv|yaml|yml|png|excalidraw)", name)
                    or ".." in name or name in names or name.startswith(("articles/", "sources/", "procedures/"))):
                raise DeskError("invalid_file_path", "Arquivo precisa de caminho simples pasta/nome.ext permitido, distinto e sem travessia.")
            encoding = item.get("encoding", "utf8")
            raw = _asset_bytes(item)
            if not raw or len(raw) > 256*1024:
                raise DeskError("oversize", "Arquivo deve ser não vazio e ter até256 KiB decodificados.", 413)
            media = _file_media(name)
            if item.get("media_type", media) != media:
                raise DeskError("invalid_media", "Media type diverge da extensão permitida.")
            if name.endswith(".png"):
                if encoding != "base64": raise DeskError("invalid_encoding", "PNG exige base64 estrito.")
                _png(raw)
            else:
                if encoding != "utf8": raise DeskError("invalid_encoding", "Arquivo textual exige utf8.")
                if name.endswith(".excalidraw"):
                    _text(item["content"], "file.content", 256*1024)
                    def pairs(values):
                        result = {}
                        for key, value in values:
                            if key in result: raise ValueError("Chave duplicada")
                            result[key] = value
                        return result
                    def constant(value): raise ValueError("Constante JSON inválida")
                    try:
                        scene = json.loads(item["content"], object_pairs_hook=pairs, parse_constant=constant)
                    except (ValueError, RecursionError) as exc:
                        raise DeskError("invalid_excalidraw", "JSON Excalidraw inválido.") from exc
                    if not isinstance(scene, dict) or scene.get("type") != "excalidraw" or not isinstance(scene.get("elements"), list):
                        raise DeskError("invalid_excalidraw", "Cena precisa de type:excalidraw e elements:list.")
                else:
                    _content(item["content"], "file.content", MAX_SOURCE_BYTES)
            sha = _hash(raw)
            if ("bytes" in item and (type(item["bytes"]) is not int or item["bytes"] != len(raw))
                    or "sha256" in item and item["sha256"] != sha):
                raise DeskError("invalid_file_metadata", "Tamanho/hash informado diverge dos bytes reais.")
            names.add(name); total += len(raw)
            stored = {"path": name, "content": item["content"], "sha256": sha, "original_owned": True}
            if encoding == "base64" or name.endswith(".excalidraw") or any(key in item for key in ("encoding", "media_type", "bytes")):
                stored.update(encoding=encoding, media_type=media, bytes=len(raw))
            preserved.append(stored)
        if total > 256 * 1024:
            raise DeskError("oversize", "Arquivos da fonte ultrapassam 256 KiB decodificados.", 413)
        return {"title": _text(data.get("title"), "title", 200),
                "content": _content(data.get("content"), "content", MAX_SOURCE_BYTES),
                "version": _text(data.get("version", "1"), "version", 100), "url": url,
                "original_owned": True, "origin": "personal_original",
                "evidence": _text(data.get("evidence", ""), "evidence", required=False),
                "limits": _text(data.get("limits", ""), "limits", required=False), "files": preserved}

    def _procedure(self, db, project_id, data):
        return {"title": _text(data.get("title"), "title", 200),
                "steps": _content(data.get("steps"), "steps", MAX_ARTICLE_BYTES),
                "source_ids": self._links(db, project_id, data),
                "evidence": _text(data.get("evidence", ""), "evidence", required=False),
                "limits": _text(data.get("limits", ""), "limits", required=False)}

    def _article(self, db, project_id, data):
        slug = data.get("slug")
        if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", slug):
            raise DeskError("invalid_slug", "slug: 1–80 caracteres ASCII minúsculos, números ou hífen.")
        procedure_id = data.get("procedure_id") or None
        if procedure_id:
            self._get(db, "procedures", project_id, procedure_id, "t")
        return {"title": _text(data.get("title"), "title", 200), "slug": slug,
                "markdown": _content(data.get("markdown"), "markdown", MAX_ARTICLE_BYTES),
                "source_ids": self._links(db, project_id, data), "procedure_id": procedure_id,
                "evidence": _text(data.get("evidence", ""), "evidence", required=False),
                "limits": _text(data.get("limits", ""), "limits", required=False)}

    def _stamp(self, db, project_id, article):
        # Entire records, not just source content: corrected evidence, version,
        # links or limits invalidate a previous review as well.
        article = {key: article[key] for key in ("id", "revision", "title", "slug", "markdown", "source_ids", "procedure_id", "evidence", "limits")}
        source_ids = set(article["source_ids"])
        procedure = None
        if article["procedure_id"]:
            procedure = self._get(db, "procedures", project_id, article["procedure_id"], "t")
            source_ids.update(procedure["source_ids"])
        sources = [self._get(db, "sources", project_id, x, "s") for x in sorted(source_ids)]
        return _hash(_json({"article": article, "procedure": procedure, "sources": sources}))

    def _project(self, db, project_id):
        row = self._project_row(db, project_id)
        project = dict(row)
        project.update(json.loads(project.pop("metadata")))
        project.update(destination={"kind": "personal_local"}, classification=CLASSIFICATION,
                       sources=self._items(db, "sources", project_id),
                       procedures=self._items(db, "procedures", project_id),
                       articles=self._items(db, "articles", project_id), releases=self._releases(db, project_id))
        project["history"] = [dict(x) | {"details": json.loads(x["details"])} for x in db.execute(
            "SELECT * FROM history WHERE project_id=? ORDER BY id", (project_id,))]
        return project

    def projects(self):
        with self._lock, self._connect() as db:
            result = []
            for x in db.execute("SELECT * FROM projects ORDER BY created_at"):
                item = dict(x); item.update(json.loads(item.pop("metadata")))
                item.update(destination={"kind": "personal_local"}, classification=CLASSIFICATION)
                result.append(item)
            return result

    def project(self, project_id):
        with self._lock, self._connect() as db:
            return self._project(db, project_id)

    def create_project(self, data):
        destination = data.get("destination", {"kind": "personal_local"})
        if destination != {"kind": "personal_local"}:
            raise DeskError("destination_blocked", "Destino permitido: somente personal_local; não há upload ou CMS externo.")
        name = _text(data.get("name"), "name", 200)
        metadata = {key: _text(data.get(key, ""), key, required=False) for key in ("purpose", "authority", "limits")}
        project_id = "p_" + uuid.uuid4().hex
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO projects(id,name,revision,active_release_id,created_at,metadata) VALUES(?,?,1,NULL,?,?)", (project_id, name, _now(), _json(metadata)))
            db.execute("INSERT INTO history(project_id,action,details,created_at) VALUES(?,?,?,?)",
                       (project_id, "created", _json({"classification": CLASSIFICATION}), _now()))
            return self._project(db, project_id)

    def _mutate(self, table, prefix, project_id, data, expected_revision, item_id=None):
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._cas(db, project_id, expected_revision)
            if table == "sources":
                value = self._source(data)
            elif table == "procedures":
                value = self._procedure(db, project_id, data)
            else:
                value = self._article(db, project_id, data)
                for other in self._items(db, "articles", project_id):
                    if other["slug"] == value["slug"] and other["id"] != item_id:
                        raise DeskError("duplicate_slug", "Outro artigo já usa esse slug.", 409)
            if item_id is None:
                count = db.execute(f"SELECT COUNT(*) FROM {table} WHERE project_id=?", (project_id,)).fetchone()[0]
                if count >= MAX_ITEMS:
                    raise DeskError("item_limit", "Limite de 64 registros por tipo/projeto.", 413)
                item_id = prefix + "_" + uuid.uuid4().hex; revision = 1
                db.execute(f"INSERT INTO {table}(id,project_id,data,revision) VALUES(?,?,?,?)",
                           (item_id, project_id, _json(value), revision))
            else:
                old = self._get(db, table, project_id, item_id, prefix)
                revision = old["revision"] + 1
                db.execute(f"UPDATE {table} SET data=?,revision=? WHERE id=? AND project_id=?",
                           (_json(value), revision, item_id, project_id))
            if table == "sources":
                db.execute("INSERT INTO snapshots(source_id,revision,content,sha256,created_at,data) VALUES(?,?,?,?,?,?)",
                           (item_id, revision, value["content"], _hash(_json({k: value[k] for k in ("content", "files")})), _now(), _json(value)))
            self._event(db, project_id, table + "_saved", {"id": item_id, "item_revision": revision,
                        "reviews_recalculated": True})
            return self._project(db, project_id)

    def create_source(self, project_id, data, expected_revision):
        return self._mutate("sources", "s", project_id, data, expected_revision)

    def update_source(self, project_id, source_id, data, expected_revision):
        return self._mutate("sources", "s", project_id, data, expected_revision, source_id)

    def create_procedure(self, project_id, data, expected_revision):
        return self._mutate("procedures", "t", project_id, data, expected_revision)

    def update_procedure(self, project_id, procedure_id, data, expected_revision):
        return self._mutate("procedures", "t", project_id, data, expected_revision, procedure_id)

    def create_article(self, project_id, data, expected_revision):
        return self._mutate("articles", "a", project_id, data, expected_revision)

    def update_article(self, project_id, article_id, data, expected_revision):
        return self._mutate("articles", "a", project_id, data, expected_revision, article_id)

    def snapshots(self, project_id, source_id):
        with self._lock, self._connect() as db:
            self._get(db, "sources", project_id, source_id, "s")
            return [dict(x) | {"data": json.loads(x["data"]) if x["data"] else None, "content_sha256": _hash(x["content"])} for x in db.execute("SELECT revision,content,sha256,created_at,data FROM snapshots WHERE source_id=? ORDER BY revision", (source_id,))]

    def review_article(self, project_id, article_id, data, expected_revision):
        actor = _actor(data); note = _text(data.get("note"), "note")
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE"); self._cas(db, project_id, expected_revision)
            article = self._get(db, "articles", project_id, article_id, "a")
            self._ready(db, project_id, article)
            review = {"stamp": self._stamp(db, project_id, article), "actor": actor,
                      "note": note, "reviewed_at": _now(), "acceptance": "self_declared_editorial_review"}
            db.execute("UPDATE articles SET review=? WHERE id=? AND project_id=?", (_json(review), article_id, project_id))
            self._event(db, project_id, "article_reviewed", {"article_id": article_id, "review": review})
            return self._project(db, project_id)

    def _ready(self, db, project_id, article):
        if not article["source_ids"]:
            raise DeskError("missing_sources", "Artigo precisa de ao menos uma fonte original própria vinculada.", 409)
        for name in ("evidence", "limits"):
            _text(article[name], "article." + name)
        source_ids = set(article["source_ids"])
        if article["procedure_id"]:
            procedure = self._get(db, "procedures", project_id, article["procedure_id"], "t")
            for name in ("evidence", "limits"):
                _text(procedure[name], "procedure." + name)
            source_ids.update(procedure["source_ids"])
        for source_id in source_ids:
            source = self._get(db, "sources", project_id, source_id, "s")
            for name in ("evidence", "limits"):
                _text(source[name], "source." + name)

    def _releases(self, db, project_id):
        return [dict(x) | {"path": project_id + "/" + x["id"], "preview_url": "/releases/" + project_id + "/" + x["id"] + "/index.html"}
                for x in db.execute("SELECT id,note,created_at,manifest_sha256 FROM releases WHERE project_id=? ORDER BY rowid", (project_id,))]

    def releases(self, project_id):
        with self._lock, self._connect() as db:
            self._project_row(db, project_id)
            return self._releases(db, project_id)

    def _release_files(self, project, release_id, note):
        from reader import build
        return build(project, release_id, _render, _hash, _json, _now)

    def publish(self, project_id, data, expected_revision):
        note = _text(data.get("note"), "note"); _actor(data)
        release_id = "r_" + uuid.uuid4().hex
        temporary = None; final = None; committed = False
        with self._lock:
            try:
                with self._connect() as db:
                    db.execute("BEGIN IMMEDIATE"); self._cas(db, project_id, expected_revision)
                    project = self._project(db, project_id)
                    if not project["articles"]:
                        raise DeskError("empty_release", "Nenhum artigo para publicar.", 409)
                    for article in project["articles"]:
                        self._ready(db, project_id, article)
                        if article["review"]["status"] != "current":
                            raise DeskError("stale_review", "Todos os artigos precisam de revisão interna atual.", 409)
                    files, manifest = self._release_files(project, release_id, note)
                    root = _safe_path(self.releases_path / project_id); root.mkdir(exist_ok=True)
                    final = _safe_path(root / release_id)
                    temporary = _safe_path(root / ("pending-" + uuid.uuid4().hex)); temporary.mkdir()
                    for name, payload in files.items():
                        target = _safe_path(temporary / name); target.parent.mkdir(parents=True, exist_ok=True)
                        with open(target, "xb") as handle:
                            handle.write(payload); handle.flush(); os.fsync(handle.fileno())
                    os.rename(temporary, final); temporary = None
                    manifest_hash = _hash(files["manifest.json"])
                    db.execute("INSERT INTO releases VALUES(?,?,?,?,?,?)", (release_id, project_id, _json(manifest), manifest_hash, manifest["created_at"], note))
                    db.execute("UPDATE projects SET active_release_id=? WHERE id=?", (release_id, project_id))
                    self._event(db, project_id, "published_local", {"release_id": release_id, "manifest_sha256": manifest_hash, "acceptance": "self_declared_editorial_review"})
                    result = self._project(db, project_id)
                committed = True
                return result
            finally:
                # A filesystem orphan after a process/power crash is possible,
                # but has no DB registration/activation. Never adopt it silently.
                if not committed:
                    for path in (temporary, final):
                        if path and path.exists() and not path.is_symlink():
                            shutil.rmtree(path)

    def _verified_release(self, db, project_id, release_id):
        _identifier(release_id, "r"); self._project_row(db, project_id)
        row = db.execute("SELECT * FROM releases WHERE id=? AND project_id=?", (release_id, project_id)).fetchone()
        if row is None:
            raise DeskError("not_found", "Release não encontrada neste projeto.", 404)
        root = _safe_path(self.releases_path / project_id / release_id)
        if not root.is_dir():
            raise DeskError("release_missing", "Arquivos de release ausentes.", 409)
        manifest = json.loads(row["manifest"])
        expected = {x["path"]: x for x in manifest["files"]}
        expected["manifest.json"] = {"bytes": len((_json(manifest) + "\n").encode("utf-8")), "sha256": row["manifest_sha256"]}
        actual = set()
        for folder, directories, names in os.walk(root, followlinks=False):
            for directory in directories:
                _safe_path(Path(folder) / directory)
            for name in names:
                path = _safe_path(Path(folder) / name)
                actual.add(path.relative_to(root).as_posix())
        if actual != set(expected):
            raise DeskError("release_tampered", "Arquivos adicionais ou ausentes na release.", 409)
        files = {}
        for name, record in expected.items():
            if not re.fullmatch(r"(?:index\.html|manifest\.json|articles/[a-z0-9-]+\.(?:md|html)|sources/s_[0-9a-f]{32}\.txt|procedures/t_[0-9a-f]{32}\.json|sources/s_[0-9a-f]{32}/(?:[a-zA-Z0-9][a-zA-Z0-9_-]*/)?[a-zA-Z0-9][a-zA-Z0-9_.-]*\.(?:json|json5|txt|md|csv|yaml|yml|png|excalidraw))", name) or ".." in name:
                raise DeskError("unsafe_manifest", "Caminho não permitido no manifesto.", 409)
            path = _safe_path(root / name)
            if not path.is_file() or path.stat().st_size != record["bytes"]:
                raise DeskError("release_tampered", "Tamanho de arquivo diverge do manifesto.", 409)
            value = path.read_bytes()
            if _hash(value) != record["sha256"]:
                raise DeskError("release_tampered", "Hash diverge do manifesto; release recusada.", 409)
            files[name] = value
        return manifest, files

    def rollback(self, project_id, release_id, data, expected_revision):
        note = _text(data.get("note"), "note"); _actor(data)
        with self._lock, self._connect() as db:
            db.execute("BEGIN IMMEDIATE"); row = self._cas(db, project_id, expected_revision)
            self._verified_release(db, project_id, release_id)
            if row["active_release_id"] == release_id:
                raise DeskError("already_active", "Release já está ativa.", 409)
            db.execute("UPDATE projects SET active_release_id=? WHERE id=?", (release_id, project_id))
            self._event(db, project_id, "rollback_local", {"from_release_id": row["active_release_id"], "to_release_id": release_id, "note": note, "working_drafts_unchanged": True})
            return self._project(db, project_id)

    def export_release(self, project_id, release_id):
        with self._lock, self._connect() as db:
            _, files = self._verified_release(db, project_id, release_id)
            output = io.BytesIO()
            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, value in sorted(files.items()):
                    entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    entry.create_system = 3
                    entry.external_attr = 0o100644 << 16
                    archive.writestr(entry, value)
            return output.getvalue()

    def release_file(self, project_id, release_id, path="index.html"):
        with self._lock, self._connect() as db:
            _, files = self._verified_release(db, project_id, release_id)
            if path not in files:
                raise DeskError("not_found", "Arquivo não encontrado na release.", 404)
            return files[path]
