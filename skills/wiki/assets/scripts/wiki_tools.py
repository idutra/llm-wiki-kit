#!/usr/bin/env python3
"""Deterministic helpers for an LLM Wiki repository. Standard library only.

Installed by the wiki skill (init) at .llm-wiki/scripts/wiki_tools.py.
Never calls an LLM. Never touches raw/. Only writes wiki/index.md and
wiki/manifest.md (with --write), appends to wiki/log.md (log-append) and
builds the derived read-only skill under dist/ (publish).

Usage:
  python .llm-wiki/scripts/wiki_tools.py check [--root DIR] [--json] [--fail-on LEVEL]
  python .llm-wiki/scripts/wiki_tools.py index [--root DIR] [--write]
  python .llm-wiki/scripts/wiki_tools.py manifest [--root DIR] [--write]
  python .llm-wiki/scripts/wiki_tools.py publish [--root DIR] [--out DIR] [--install REPO]...
  python .llm-wiki/scripts/wiki_tools.py seen URL [URL ...] [--json]
  python .llm-wiki/scripts/wiki_tools.py scan FILE|- [...] [--json]   (secrets/PII gate; exit 1 on findings)
  python .llm-wiki/scripts/wiki_tools.py log-tail [--root DIR] [-n 5]
  python .llm-wiki/scripts/wiki_tools.py log-append --op ingest --title T
         [--agent A] [--files f1,f2] [--approved-by X] [--notes N]

The page vocabulary is read from .llm-wiki/config.yml, so a wiki can evolve its
schema without editing this file. Built-in defaults apply to any missing key:
  paths:            wiki / raw / assets directories, relative to the repo root
  categories:       wiki/ subdirectory -> page type, in index.md order
  category_labels:  wiki/ subdirectory -> section heading in index.md (optional)
  extra_types:      valid page types that have no directory of their own (optional)
  statuses:         valid values of the `status` key
  required_by_type: page type -> [keys that must be non-empty] (inline lists)
  enums:            key -> [allowed values]; a dotted key reaches one nested level
  lint:             severity per check, fail_on, default_volatility, freshness by band
  publish:          name, title, description, out, include_raw, max_sensitivity
  capture:          read by the wiki skill only (raw_category, author)
  research:         read by the wiki skill only (angles, max_sources, max_rounds, domains)

Exit codes: 0 ok, 1 findings at or above --fail-on (check) or bad usage, 2 wiki not found.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

KIT_VERSION = "1.0.0"  # version of llm-wiki-kit this copy came from; see `--version`
CONFIG_REL = ".llm-wiki/config.yml"
# Built-in page vocabulary; .llm-wiki/config.yml overrides it (see Schema).
# (wiki/ subdirectory, page type, heading label used in index.md)
DEFAULT_CATEGORIES = [
    ("sources", "source", "Sources"),
    ("entities", "entity", "Entities"),
    ("concepts", "concept", "Concepts"),
    ("syntheses", "synthesis", "Syntheses"),
    ("comparisons", "comparison", "Comparisons"),
    ("questions", "question", "Questions"),
    ("outputs", "output", "Outputs"),
]
DEFAULT_STATUSES = ("draft", "reviewed", "stale", "disputed")
LEVELS = ("info", "warning", "error")  # increasing severity; 'off' silences a kind entirely
# What each finding costs by default. A wiki raises or lowers any of them under `lint.severity`.
DEFAULT_SEVERITY = {
    "config": "warning", "frontmatter": "error", "raw-ref": "error", "broken-link": "error",
    "broken-wikilink": "error", "index": "error", "log": "error", "placement": "warning",
    "orphan": "warning", "unreferenced-raw": "warning", "manifest": "warning",
    "source-changed": "warning", "freshness": "info",
}
# How long a page stays fresh, by its `volatility`. 0 means it never goes stale.
DEFAULT_FRESHNESS = {"high": 30, "medium": 180, "low": 365, "static": 0}
DEFAULT_REQUIRED_BY_TYPE = {"source": ["sources"]}
SENSITIVITY = {"public", "internal", "confidential", "restricted"}
LOG_OPS = {"init", "ingest", "query", "archive", "lint", "index", "export", "publish", "research", "capture", "schema"}
REQUIRED_KEYS = ("title", "type", "status", "created", "updated")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LOG_HEADER_RE = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\] ([a-z]+) \| (.+)$")
MD_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
SPECIAL_FILES = {"index.md", "log.md", "manifest.md"}
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)
# One row of wiki/manifest.md: source path, title, wiki page, short hash.
MANIFEST_ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|.*\|\s*`([0-9a-f]{12})`\s*\|\s*$", re.M)


# ----------------------------------------------------------------------------
# Minimal YAML parser (subset: scalars, inline lists, block lists, one level of
# nested mapping). Enough for page frontmatter and for .llm-wiki/config.yml.
# ----------------------------------------------------------------------------

def _parse_scalar(raw: str):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [_strip_quotes(x) for x in inner.split(",")]
    return _strip_quotes(raw)


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def parse_yaml(lines) -> dict:
    """Parse the supported YAML subset: nested mappings, block lists and inline lists.

    Nesting follows indentation, so a mapping can be as deep as the config needs
    (`lint.freshness.high`). Lists hold scalars only. Malformed input is skipped rather
    than raised: a config typo is reported by `check`, never as a traceback.
    """
    root: dict = {}
    stack: list[tuple[int, dict]] = [(0, root)]  # (indent of this mapping's keys, mapping)
    pending: tuple[str, dict] | None = None      # key whose nested value has not started yet

    for line in lines:
        stripped = line.split(" #", 1)[0].rstrip() if not line.strip().startswith("#") else ""
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        content = stripped.strip()

        if content.startswith("- "):  # block list item; `pending` stays, more items may follow
            if pending is not None:
                key, owner = pending
                if not isinstance(owner.get(key), list):
                    owner[key] = []
                owner[key].append(_strip_quotes(content[2:]))
            continue

        if ":" not in content:
            continue

        while len(stack) > 1 and indent < stack[-1][0]:
            stack.pop()
        if pending is not None and indent > stack[-1][0]:  # deeper than the current mapping: open it
            key, owner = pending
            if not isinstance(owner.get(key), dict):
                owner[key] = {}
            stack.append((indent, owner[key]))
        elif indent > stack[-1][0]:
            continue  # indented under a key that already holds a scalar; not ours to keep
        pending = None

        current = stack[-1][1]
        key, _, value = content.partition(":")
        key, value = key.strip(), value.strip()
        if value == "":
            current[key] = None  # a nested mapping or a block list may follow
            pending = (key, current)
        else:
            current[key] = _parse_scalar(value)
    return root


def parse_frontmatter(text: str):
    """Return (dict or None, body_start_line). None when no frontmatter block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, 0
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, 0
    return parse_yaml(lines[1:end]), end + 1


def _dotted(fm: dict, key: str):
    """Look up 'a' or 'a.b' in parsed YAML (the parser keeps one nested level)."""
    head, _, tail = key.partition(".")
    value = fm.get(head)
    if tail:
        return value.get(tail) if isinstance(value, dict) else None
    return value


# ----------------------------------------------------------------------------
# Repository model
# ----------------------------------------------------------------------------

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _str_list(value) -> list[str]:
    """Normalize a config value (scalar or list) to a list of non-empty strings."""
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [str(x) for x in value if x not in (None, "")]
    return []


class Schema:
    """Page vocabulary of one wiki: built-in defaults overridden by .llm-wiki/config.yml.

    Anything malformed in the config is reported in `problems` (surfaced by `check`
    as 'config' warnings) and falls back to the default instead of raising.
    """

    def __init__(self, cfg: dict):
        self.problems: list[str] = []
        default_type = {d: t for d, t, _ in DEFAULT_CATEGORIES}
        default_label = {d: label for d, _, label in DEFAULT_CATEGORIES}

        cats = cfg.get("categories")
        if isinstance(cats, dict) and cats:
            dir_types = [(str(d), t if isinstance(t, str) and t else None) for d, t in cats.items()]
        elif isinstance(cats, list) and cats:
            # Legacy form: a plain list of directories; types come from the built-in mapping.
            dir_types = [(str(d), default_type.get(str(d))) for d in cats]
        else:
            if cats not in (None, ""):
                self.problems.append("'categories' must be a mapping 'directory: type'; using the defaults")
            dir_types = [(d, t) for d, t, _ in DEFAULT_CATEGORIES]
        for d, t in dir_types:
            if t is None:
                self.problems.append(f"category '{d}' has no page type; declare it as '{d}: <type>' under 'categories'")

        labels = cfg.get("category_labels")
        labels = labels if isinstance(labels, dict) else {}
        # (directory, index heading), in index.md order
        self.categories = [
            (d, str(labels.get(d) or default_label.get(d) or d.replace("-", " ").replace("_", " ").capitalize()))
            for d, _ in dir_types
        ]
        self.type_of_dir = {d: t for d, t in dir_types if t}
        self.types = set(self.type_of_dir.values()) | set(self._list(cfg, "extra_types"))
        self.statuses = set(self._list(cfg, "statuses") or DEFAULT_STATUSES)

        configured_required = self._map_of_lists(cfg, "required_by_type")
        for t in configured_required:
            if t not in self.types:
                self.problems.append(f"'required_by_type.{t}': '{t}' is not a declared page type")
        self.required_by_type = {**DEFAULT_REQUIRED_BY_TYPE, **configured_required}
        self.enums = self._map_of_lists(cfg, "enums")

        lint = cfg.get("lint")
        lint = lint if isinstance(lint, dict) else {}
        self.severity = dict(DEFAULT_SEVERITY)
        configured = lint.get("severity")
        if isinstance(configured, dict):
            for kind, level in configured.items():
                kind, level = str(kind), str(level).lower()
                if kind not in DEFAULT_SEVERITY:
                    self.problems.append(f"'lint.severity.{kind}': unknown check; valid: {', '.join(sorted(DEFAULT_SEVERITY))}")
                elif level not in LEVELS and level != "off":
                    self.problems.append(f"'lint.severity.{kind}': must be one of {', '.join(LEVELS)}, off")
                else:
                    self.severity[kind] = level
        elif configured is not None:
            self.problems.append("'lint.severity' must be a mapping 'check: level'; using the defaults")

        self.fail_on = str(lint.get("fail_on") or "error").lower()
        if self.fail_on not in LEVELS and self.fail_on != "never":
            self.problems.append(f"'lint.fail_on': must be one of {', '.join(LEVELS)}, never; using 'error'")
            self.fail_on = "error"

        self.default_volatility = str(lint.get("default_volatility") or "medium").lower()
        self.freshness = dict(DEFAULT_FRESHNESS)
        configured = lint.get("freshness")
        if isinstance(configured, dict):
            for band, days in configured.items():
                band = str(band).lower()
                try:
                    self.freshness[band] = max(0, int(days))
                except (TypeError, ValueError):
                    self.problems.append(f"'lint.freshness.{band}': must be a number of days")
        elif configured is not None:
            self.problems.append("'lint.freshness' must be a mapping 'volatility: days'; using the defaults")
        if self.default_volatility not in self.freshness:
            self.problems.append(f"'lint.default_volatility': unknown band '{self.default_volatility}'; using 'medium'")
            self.default_volatility = "medium"

    def _list(self, cfg: dict, key: str) -> list[str]:
        if cfg.get(key) in (None, ""):
            return []
        items = _str_list(cfg[key])
        if not items:
            self.problems.append(f"'{key}' must be a non-empty list; ignored")
        return items

    def _map_of_lists(self, cfg: dict, key: str) -> dict[str, list[str]]:
        raw = cfg.get(key)
        if raw in (None, ""):
            return {}
        if not isinstance(raw, dict):
            self.problems.append(f"'{key}' must be a mapping of inline lists, e.g. 'name: [a, b]'; ignored")
            return {}
        out: dict[str, list[str]] = {}
        for k, v in raw.items():
            items = _str_list(v)
            if items:
                out[str(k)] = items
            else:
                self.problems.append(f"'{key}.{k}' must be a non-empty inline list, e.g. '{k}: [a, b]'; ignored")
        return out


class Wiki:
    def __init__(self, root: Path):
        self.root = root
        cfg_path = root / CONFIG_REL
        self.config = parse_yaml(read_text(cfg_path).splitlines()) if cfg_path.is_file() else {}
        paths = self.config.get("paths")
        paths = paths if isinstance(paths, dict) else {}

        def configured(key: str, default: str) -> Path:
            value = paths.get(key)
            return root / (value if isinstance(value, str) and value else default)

        self.wiki_dir = configured("wiki", "wiki")
        self.raw_dir = configured("raw", "raw")
        self.assets_dir = configured("assets", "raw/assets")
        self.index_path = self.wiki_dir / "index.md"
        self.log_path = self.wiki_dir / "log.md"
        self.manifest_path = self.wiki_dir / "manifest.md"
        self.schema = Schema(self.config)

    def exists(self) -> bool:
        return self.wiki_dir.is_dir()

    def sources(self):
        """Every ingestible file under raw/ (assets and .gitkeep are not sources)."""
        if not self.raw_dir.is_dir():
            return
        for p in sorted(self.raw_dir.rglob("*")):
            if p.is_file() and p.name != ".gitkeep" and not self.is_asset(p):
                yield p

    def ingested_by(self) -> dict[str, list[Path]]:
        """Map each path named in a page's `sources:` to the pages that cite it."""
        out: dict[str, list[Path]] = {}
        for p in self.pages():
            fm, _ = parse_frontmatter(read_text(p))
            for src in ((fm or {}).get("sources") or []):
                if isinstance(src, str) and src:
                    out.setdefault((self.root / src).resolve().as_posix(), []).append(p)
        return out

    def pages(self):
        for p in sorted(self.wiki_dir.rglob("*.md")):
            if p.name in SPECIAL_FILES and p.parent == self.wiki_dir:
                continue
            yield p

    def rel(self, p: Path) -> str:
        return p.relative_to(self.root).as_posix()

    def wiki_rel(self, p: Path) -> str:
        return p.relative_to(self.wiki_dir).as_posix()

    def is_asset(self, p: Path) -> bool:
        """Images and attachments under raw/ are not sources to ingest."""
        return ("assets" in p.relative_to(self.raw_dir).parts
                or p.resolve().is_relative_to(self.assets_dir.resolve()))


def source_hash(p: Path) -> str:
    """Short content hash of a source. CRLF is normalized so the same file hashes
    the same on Windows and Linux; otherwise a checkout would look like a change."""
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:12]


def source_title(p: Path) -> str:
    """The source's own title: first H1, else frontmatter `title`, else the file stem."""
    text = read_text(p)
    fm, body_start = parse_frontmatter(text)
    m = H1_RE.search("\n".join(text.splitlines()[body_start:]))
    if m:
        return m.group(1).strip()
    title = (fm or {}).get("title")
    return str(title).strip() if isinstance(title, str) and title.strip() else p.stem


def resolve_link(from_file: Path, target: str, root: Path) -> Path | None:
    """Resolve a relative markdown link target to a filesystem path. Returns None for external links."""
    if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
        return None
    target = target.split("#", 1)[0]
    if not target:
        return None
    if target.startswith("/"):
        return (root / target.lstrip("/")).resolve()
    return (from_file.parent / target).resolve()


# ----------------------------------------------------------------------------
# check
# ----------------------------------------------------------------------------

def run_check(wiki: Wiki) -> dict:
    schema = wiki.schema
    findings: list[dict] = []
    fresh_candidates: list[tuple] = []

    def add(kind, path, msg):
        """Record a finding at the severity this wiki assigns to that kind."""
        level = schema.severity.get(kind, "error")
        if level != "off":
            findings.append({"level": level, "kind": kind, "path": path, "message": msg})

    err = warn = add  # the kind decides the severity now, not the call site

    index_rel = wiki.rel(wiki.index_path)
    log_rel = wiki.rel(wiki.log_path)
    for problem in schema.problems:
        warn("config", CONFIG_REL, problem)

    pages = list(wiki.pages())
    inbound: dict[Path, int] = {p.resolve(): 0 for p in pages}
    index_text = read_text(wiki.index_path) if wiki.index_path.exists() else ""
    if not wiki.index_path.exists():
        err("index", index_rel, "index.md not found")
    if not wiki.log_path.exists():
        err("log", log_rel, "log.md not found")

    # Frontmatter and links per page
    for p in pages:
        rel = wiki.rel(p)
        text = read_text(p)
        fm, _ = parse_frontmatter(text)
        is_marp = text.lstrip().startswith("---") and "marp:" in text[:400]
        if fm is None:
            err("frontmatter", rel, "missing YAML frontmatter")
        elif not is_marp:
            fresh_candidates.append((p, fm))
            for k in REQUIRED_KEYS:
                if k not in fm or fm[k] in (None, ""):
                    err("frontmatter", rel, f"missing required key '{k}'")
            t = fm.get("type")
            if t and (not isinstance(t, str) or t not in schema.types):
                err("frontmatter", rel, f"unknown type '{t}' (valid: {', '.join(sorted(schema.types))})")
            s = fm.get("status")
            if s and (not isinstance(s, str) or s not in schema.statuses):
                err("frontmatter", rel, f"unknown status '{s}' (valid: {', '.join(sorted(schema.statuses))})")
            sens = fm.get("sensitivity")
            if sens and sens not in SENSITIVITY:
                err("frontmatter", rel, f"unknown sensitivity '{sens}'")
            for dk in ("created", "updated"):
                v = fm.get(dk)
                if v and not DATE_RE.match(str(v)):
                    err("frontmatter", rel, f"'{dk}' must be YYYY-MM-DD, got '{v}'")
            for k in (schema.required_by_type.get(t, ()) if isinstance(t, str) else ()):
                if _dotted(fm, k) in (None, "", []):
                    err("frontmatter", rel, f"type '{t}' requires non-empty '{k}'")
            for k, allowed in schema.enums.items():
                v = _dotted(fm, k)
                for item in (v if isinstance(v, list) else [v]):
                    if item not in (None, "") and str(item) not in allowed:
                        err("frontmatter", rel, f"invalid {k} '{item}' (valid: {', '.join(allowed)})")
            for src in (fm.get("sources") or []):
                if isinstance(src, str) and src:
                    sp = (wiki.root / src)
                    if not sp.exists():
                        err("raw-ref", rel, f"sources entry not found: {src}")
                    elif not sp.resolve().is_relative_to(wiki.raw_dir.resolve()):
                        warn("raw-ref", rel, f"sources entry outside raw/: {src}")
            # Category vs type consistency
            cat = p.relative_to(wiki.wiki_dir).parts[0] if len(p.relative_to(wiki.wiki_dir).parts) > 1 else ""
            expected = schema.type_of_dir.get(cat)
            if expected and t and t != expected:
                warn("placement", rel, f"type '{t}' inside '{cat}/' (expected '{expected}')")

        # Links
        for m in MD_LINK_RE.finditer(text):
            target = m.group(2)
            resolved = resolve_link(p, target, wiki.root)
            if resolved is None:
                continue
            if not resolved.exists():
                err("broken-link", rel, f"target not found: {target}")
                continue
            if resolved in inbound and resolved != p.resolve():
                inbound[resolved] += 1
        for m in WIKILINK_RE.finditer(text):
            name = m.group(1).strip()
            matches = [q for q in pages if q.stem == name or wiki.wiki_rel(q)[:-3] == name]
            if not matches:
                err("broken-wikilink", rel, f"[[{name}]] has no target")
            for q in matches:
                if q.resolve() != p.resolve():
                    inbound[q.resolve()] += 1

    # Orphans (no inbound links from other pages; index does not count)
    for p in pages:
        if inbound.get(p.resolve(), 0) == 0 and p.name != "overview.md":
            warn("orphan", wiki.rel(p), "no inbound links from other wiki pages")

    # Index consistency
    if index_text:
        indexed: dict[str, int] = {}
        for m in MD_LINK_RE.finditer(index_text):
            target = m.group(2)
            resolved = resolve_link(wiki.index_path, target, wiki.root)
            if resolved is None:
                continue
            key = resolved.as_posix()
            indexed[key] = indexed.get(key, 0) + 1
            if not resolved.exists():
                err("index", index_rel, f"index entry points to missing file: {target}")
        for p in pages:
            key = p.resolve().as_posix()
            n = indexed.get(key, 0)
            if n == 0:
                err("index", wiki.rel(p), f"page missing from {index_rel}")
            elif n > 1:
                warn("index", wiki.rel(p), f"page listed {n} times in {index_rel}")

    # Log format
    if wiki.log_path.exists():
        for i, line in enumerate(read_text(wiki.log_path).splitlines(), 1):
            if line.startswith("## "):
                m = LOG_HEADER_RE.match(line)
                if not m:
                    err("log", f"{log_rel}:{i}", "header must be '## [YYYY-MM-DD] <op> | <title>'")
                elif m.group(2) not in LOG_OPS:
                    err("log", f"{log_rel}:{i}", f"unknown op '{m.group(2)}'")

    # raw/ files never referenced by any page (backlog reminder), and drift
    # against wiki/manifest.md: a source whose hash moved needs its page revisited.
    if wiki.raw_dir.is_dir():
        referenced = set(wiki.ingested_by())
        recorded = parse_manifest(read_text(wiki.manifest_path)) if wiki.manifest_path.exists() else None
        seen, pending = set(), 0
        for rp in wiki.sources():
            rel_raw = rp.relative_to(wiki.raw_dir).as_posix()
            seen.add(rel_raw)
            if rp.resolve().as_posix() not in referenced:
                pending += 1
                # With a manifest the backlog is already listed there; repeating it once
                # per file would bury the warnings that need action.
                if recorded is None:
                    warn("unreferenced-raw", wiki.rel(rp), "raw file not referenced by any wiki page")
            if recorded is not None:
                was = recorded.get(rel_raw)
                if was is None:
                    warn("manifest", wiki.rel(rp), f"source missing from {wiki.rel(wiki.manifest_path)}; run 'manifest --write'")
                elif was != source_hash(rp):
                    warn("source-changed", wiki.rel(rp),
                         f"content differs from {wiki.rel(wiki.manifest_path)} ({was} -> {source_hash(rp)}); re-ingest and update the manifest")
        if recorded is not None and pending:
            warn("unreferenced-raw", wiki.rel(wiki.manifest_path),
                 f"{pending} source(s) not referenced by any wiki page; the ingestion backlog is listed in the manifest")
        for gone in sorted((recorded or {}).keys() - seen):
            warn("manifest", wiki.rel(wiki.manifest_path), f"manifest lists a source that no longer exists: {gone}")

    today = dt.date.today()
    for p, fm in fresh_candidates:
        band = str(_dotted(fm, "volatility") or schema.default_volatility).lower()
        if band not in schema.freshness:
            warn("frontmatter", wiki.rel(p), f"unknown volatility '{band}' (valid: {', '.join(sorted(schema.freshness))})")
            continue
        days = schema.freshness[band]
        updated = fm.get("updated")
        if not days or not isinstance(updated, str) or not DATE_RE.match(updated):
            continue
        age = (today - dt.date.fromisoformat(updated)).days
        if age > days:
            add("freshness", wiki.rel(p),
                f"not updated for {age} days; volatility '{band}' expects a review every {days}")

    errors = [f for f in findings if f["level"] == "error"]
    warnings = [f for f in findings if f["level"] == "warning"]
    infos = [f for f in findings if f["level"] == "info"]
    return {"errors": errors, "warnings": warnings, "infos": infos, "findings": findings,
            "summary": {"pages": len(pages), "errors": len(errors),
                        "warnings": len(warnings), "infos": len(infos)}}


def cmd_check(wiki: Wiki, as_json: bool, fail_on: str | None) -> int:
    result = run_check(wiki)
    fail_on = (fail_on or wiki.schema.fail_on).lower()
    if fail_on not in LEVELS and fail_on != "never":
        print(f"--fail-on must be one of {', '.join(LEVELS)}, never", file=sys.stderr)
        return 1
    summary = result["summary"]
    if as_json:
        print(json.dumps({**result, "fail_on": fail_on}, indent=2, ensure_ascii=False))
    else:
        for f in sorted(result["findings"], key=lambda f: (-LEVELS.index(f["level"]), f["kind"], f["path"])):
            print(f"{f['level'].upper():7} [{f['kind']}] {f['path']}: {f['message']}")
        print(f"\n{summary['pages']} pages, {summary['errors']} errors, "
              f"{summary['warnings']} warnings, {summary['infos']} infos (failing on: {fail_on})")
    if fail_on == "never":
        return 0
    threshold = LEVELS.index(fail_on)
    return 1 if any(LEVELS.index(f["level"]) >= threshold for f in result["findings"]) else 0


# ----------------------------------------------------------------------------
# index
# ----------------------------------------------------------------------------

def _existing_summaries(index_text: str, wiki: Wiki) -> dict[str, str]:
    out: dict[str, str] = {}
    line_re = re.compile(r"^- \[[^\]]*\]\(([^)]+)\)\s*-\s*(.*)$")
    for line in index_text.splitlines():
        m = line_re.match(line.strip())
        if m:
            resolved = resolve_link(wiki.index_path, m.group(1), wiki.root)
            if resolved is not None:
                summary = re.sub(r"\s*\((?:fontes|sources): .*\)\s*$", "", m.group(2)).strip()
                out[resolved.as_posix()] = summary
    return out


def cmd_index(wiki: Wiki, write: bool) -> int:
    existing = _existing_summaries(read_text(wiki.index_path), wiki) if wiki.index_path.exists() else {}
    groups: dict[str, list[str]] = {d: [] for d, _ in wiki.schema.categories}
    other: list[str] = []  # pages outside every configured category
    overview_line = None
    for p in wiki.pages():
        fm, _ = parse_frontmatter(read_text(p))
        fm = fm or {}
        title = fm.get("title") or p.stem
        link = wiki.wiki_rel(p)
        summary = existing.get(p.resolve().as_posix()) or fm.get("summary") or "(no summary)"
        if fm.get("archived_from") and not str(summary).startswith("[Archived]"):
            summary = f"[Archived] {summary}"
        n_sources = len(fm.get("sources") or []) if isinstance(fm.get("sources"), list) else 0
        updated = fm.get("updated") or ""
        meta = f" (sources: {n_sources}, updated: {updated})" if updated else ""
        line = f"- [{title}]({link}) - {summary}{meta}"
        if p.parent == wiki.wiki_dir and p.name == "overview.md":
            overview_line = line
            continue
        parts = p.relative_to(wiki.wiki_dir).parts
        cat = parts[0] if len(parts) > 1 else ""
        groups.get(cat, other).append(line)

    out = ["# Índice do wiki", "",
           "Catálogo de todas as páginas, por categoria. Uma linha por página: link, resumo de uma linha, metadados.",
           "Mantido pelo agente em toda operação de ingest, archive e lint. Leia este arquivo primeiro ao responder perguntas.", ""]
    out += ["## Overview", "", overview_line or "- [Visão geral](overview.md) - (no summary)", ""]
    for d, label in wiki.schema.categories:
        out += [f"## {label}", ""]
        out += groups[d] if groups[d] else ["(vazio)"]
        out += [""]
    if other:
        out += ["## Other", ""] + other + [""]
    text = "\n".join(out).rstrip() + "\n"
    if write:
        wiki.index_path.write_text(text, encoding="utf-8")
        print(f"wrote {wiki.rel(wiki.index_path)}")
    else:
        sys.stdout.write(text)
    return 0


# ----------------------------------------------------------------------------
# log-tail / log-append
# ----------------------------------------------------------------------------

def parse_manifest(text: str) -> dict[str, str]:
    """Read back the source path -> short hash pairs recorded in wiki/manifest.md."""
    return {m.group(1): m.group(2) for m in MANIFEST_ROW_RE.finditer(text)}


def cmd_manifest(wiki: Wiki, write: bool) -> int:
    """Catalog every file under raw/: title, whether it is ingested, content hash.

    This is what lets an agent see sources it has not compiled yet, and what makes
    a re-sync visible: a changed hash means the source moved under the wiki's feet.
    """
    ingested = wiki.ingested_by()
    # A source may be cited by several pages; the one that compiles it is the page
    # in the category whose type is 'source'. Others merely reference it.
    source_dir = next((d for d, t in wiki.schema.type_of_dir.items() if t == "source"), None)

    def compiled_page(pages: list[Path]) -> Path:
        if source_dir:
            for q in pages:
                if q.relative_to(wiki.wiki_dir).parts[0] == source_dir:
                    return q
        return pages[0]

    groups: dict[str, list[str]] = {}
    n_ingested = 0
    for p in wiki.sources():
        pages = ingested.get(p.resolve().as_posix(), [])
        title = source_title(p)
        if pages:
            n_ingested += 1
            page = compiled_page(pages)
            fm, _ = parse_frontmatter(read_text(page))
            label = (fm or {}).get("title") or page.stem
            # The compiled page was written and reviewed by a human, so its title
            # beats whatever heading the raw export happens to start with.
            title = label
            where = f"[{label}]({wiki.wiki_rel(page)})"
        else:
            where = "— (não ingerida)"
        rel = p.relative_to(wiki.raw_dir)
        parts = rel.parts
        groups.setdefault(parts[0] if len(parts) > 1 else "", []).append(
            f"| `{rel.as_posix()}` | {title} | {where} | `{source_hash(p)}` |"
        )

    total = sum(len(v) for v in groups.values())
    ingested_label = "1 ingerida" if n_ingested == 1 else f"{n_ingested} ingeridas"
    out = ["# Manifesto de fontes", "",
           f"Catálogo de tudo que está em `{wiki.rel(wiki.raw_dir)}/`: título, se já virou página no wiki e hash do conteúdo.",
           "Fonte sem página ainda não foi compilada, e o seu conteúdo só existe no arquivo bruto.",
           "O caminho é o identificador. O título vem da página do wiki quando a fonte já foi ingerida;",
           "senão é extraído do arquivo bruto e pode não descrever bem o documento.",
           "Hash diferente do registrado aqui significa que a fonte mudou e a página correspondente precisa ser revista.",
           "", f"Gerado por `wiki_tools.py manifest --write`. {total} fontes, {ingested_label}, {total - n_ingested} pendentes.", ""]
    for category in sorted(groups):
        rows = groups[category]
        out += [f"## {category or 'raiz'} ({len(rows)})", "",
                "| Fonte | Título | Página no wiki | Hash |", "| --- | --- | --- | --- |", *rows, ""]
    text = "\n".join(out).rstrip() + "\n"
    if write:
        wiki.manifest_path.write_text(text, encoding="utf-8")
        print(f"wrote {wiki.rel(wiki.manifest_path)} ({total} fontes, {ingested_label})")
    else:
        sys.stdout.write(text)
    return 0


def cmd_log_tail(wiki: Wiki, n: int) -> int:
    if not wiki.log_path.exists():
        print(f"{wiki.rel(wiki.log_path)} not found", file=sys.stderr)
        return 2
    lines = read_text(wiki.log_path).splitlines()
    starts = [i for i, l in enumerate(lines) if l.startswith("## [")]
    for s in starts[-n:]:
        e = next((x for x in starts if x > s), len(lines))
        print("\n".join(lines[s:e]).rstrip())
        print()
    return 0


def cmd_log_append(wiki: Wiki, op: str, title: str, agent: str, files: str, approved_by: str, notes: str) -> int:
    if op not in LOG_OPS:
        print(f"unknown op '{op}'. valid: {', '.join(sorted(LOG_OPS))}", file=sys.stderr)
        return 1
    today = dt.date.today().isoformat()
    entry = [f"## [{today}] {op} | {title}", f"- agent: {agent}"]
    if files:
        entry.append(f"- files: {', '.join(f.strip() for f in files.split(',') if f.strip())}")
    if approved_by:
        entry.append(f"- approved_by: {approved_by}")
    if notes:
        entry.append(f"- notes: {notes}")
    existing = read_text(wiki.log_path) if wiki.log_path.exists() else "# Log do wiki\n"
    sep = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    wiki.log_path.write_text(existing + sep + "\n".join(entry) + "\n", encoding="utf-8")
    print(entry[0])
    return 0


# ----------------------------------------------------------------------------

def _utf8_when_piped() -> None:
    """Agents and hooks read our output through a pipe, where Windows defaults to the
    ANSI code page and mangles accents. A real console is left to Python's own handling."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and not stream.isatty():
            stream.reconfigure(encoding="utf-8", errors="replace")


# ----------------------------------------------------------------------------
# scan
# ----------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(r"^(<|\$\{|\{\{|%|\*{3,}|x{3,}|\.{3})", re.I)
SCAN_PATTERNS = [
    ("secret", "private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("secret", "aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("secret", "github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})\b")),
    ("secret", "slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("secret", "api-key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("secret", "jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("secret", "bearer-token", re.compile(r"(?i)\bbearer\s+([A-Za-z0-9._~+/-]{20,})")),
    ("secret", "url-credentials", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s:/@]+:([^\s@/]{3,})@")),
    ("secret", "assignment", re.compile(
        r"(?i)\b(?:password|passwd|pwd|senha|secret|token|api[_-]?key|client[_-]?secret|access[_-]?key)\b"
        r"\s*[:=]\s*[\"']?([^\s\"'`,;]{6,})")),
    ("pii", "email", re.compile(r"\b[\w.+-]+@(?!example\.)[\w-]+(?:\.[\w-]+)+\b")),
]


def scan_text(text: str) -> list[dict]:
    """Known secret and PII patterns, line by line. Never returns the matched value in full."""
    findings = []
    for n, line in enumerate(text.splitlines(), 1):
        taken: list[tuple[int, int]] = []
        for level, kind, rx in SCAN_PATTERNS:
            for m in rx.finditer(line):
                value = m.group(m.lastindex or 0)
                if _PLACEHOLDER_RE.match(value) or any(a < m.end() and m.start() < b for a, b in taken):
                    continue
                taken.append(m.span())
                findings.append({"level": level, "kind": kind, "line": n, "preview": value[:4] + "..."})
    return findings


def cmd_scan(paths: list[str], as_json: bool) -> int:
    """Gate before a note is written to raw/, which is immutable and versioned."""
    report = []
    for raw_path in paths:
        text = sys.stdin.read() if raw_path == "-" else read_text(Path(raw_path))
        for f in scan_text(text):
            report.append({"path": raw_path, **f})
    if as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for r in report:
            print(f"{r['level'].upper():7} [{r['kind']}] {r['path']}:{r['line']}  {r['preview']}")
        print(f"\n{len(report)} finding(s). Pattern scan only: a clean result does not replace human review.")
    return 1 if report else 0


# ----------------------------------------------------------------------------
# seen
# ----------------------------------------------------------------------------

TRACKING_PARAM_RE = re.compile(r"^(utm_[a-z]+|fbclid|gclid|mc_cid|mc_eid|ref|ref_src)$", re.I)


def normalize_url(url: str) -> str:
    """Canonical form used only to compare URLs: no scheme, no www., no fragment,
    no tracking parameters, no trailing slash, lower-case host."""
    from urllib.parse import parse_qsl, urlencode, urlsplit
    parts = urlsplit(url.strip() if "://" in url else "https://" + url.strip())
    host = parts.netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                       if not TRACKING_PARAM_RE.match(k)])
    return host + parts.path.rstrip("/") + ("?" + query if query else "")


def known_urls(wiki: Wiki) -> dict[str, str]:
    """normalized URL -> repo-relative file that records it (raw/ header or page source_meta)."""
    out: dict[str, str] = {}
    for p in wiki.sources():
        if p.suffix.lower() not in (".md", ".markdown", ".txt"):
            continue
        fm, _ = parse_frontmatter(read_text(p))
        url = (fm or {}).get("source_url")
        if isinstance(url, str) and "." in url and url != "pasted":
            out.setdefault(normalize_url(url), wiki.rel(p))
    for p in wiki.pages():
        fm, _ = parse_frontmatter(read_text(p))
        url = _dotted(fm or {}, "source_meta.origin_url")
        if isinstance(url, str) and "." in url and url != "n/a":
            out.setdefault(normalize_url(url), wiki.rel(p))
    return out


def cmd_seen(wiki: Wiki, urls: list[str], as_json: bool) -> int:
    """Tell which URLs are already captured, so research does not fetch a source twice."""
    known = known_urls(wiki)
    result = [{"url": u, "seen": normalize_url(u) in known, "where": known.get(normalize_url(u))} for u in urls]
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for r in result:
            print(f"seen  {r['url']}  ->  {r['where']}" if r["seen"] else f"new   {r['url']}")
    return 0


# ----------------------------------------------------------------------------
# publish
# ----------------------------------------------------------------------------

PUBLISH_SKILL_REL = ".llm-wiki/publish/SKILL.md"
PUBLISH_TEMPLATE_REL = ".llm-wiki/templates/consumer-skill.md"
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SENSITIVITY_ORDER = ["public", "internal", "confidential", "restricted"]
INSTALL_DIRS = (".claude/skills", ".agents/skills")  # Claude Code; Codex, OpenCode, Copilot, Cursor, Gemini CLI


def _git(root: Path, *args: str) -> str:
    try:
        return subprocess.run(("git",) + args, cwd=root, capture_output=True, text=True,
                              encoding="utf-8").stdout.strip()
    except OSError:
        return ""


def _consumer_skill_text(wiki: Wiki, cfg: dict):
    """The consumer SKILL.md: a hand-written one wins; otherwise the template filled from config.
    Returns (text, origin) or (None, reason)."""
    custom = wiki.root / PUBLISH_SKILL_REL
    if custom.is_file():
        return read_text(custom), PUBLISH_SKILL_REL
    template = wiki.root / PUBLISH_TEMPLATE_REL
    if not template.is_file():
        return None, f"missing both {PUBLISH_SKILL_REL} and {PUBLISH_TEMPLATE_REL}"
    description = cfg.get("description")
    if not isinstance(description, str) or not description.strip():
        return None, ("publish.description is empty in .llm-wiki/config.yml; it is what makes an agent "
                      "load the skill, so it has to name the subjects this wiki covers")
    text = read_text(template)
    for key in ("name", "title", "description", "repository", "wiki_dir", "raw_dir"):
        text = text.replace("{{" + key + "}}", str(cfg.get(key) or "").strip())
    return text, PUBLISH_TEMPLATE_REL


def cmd_publish(wiki: Wiki, out, install) -> int:
    """Assemble the wiki as a read-only Agent Skill that other repositories install."""
    cfg = wiki.config.get("publish")
    cfg = dict(cfg) if isinstance(cfg, dict) else {}
    if not cfg.get("name"):
        base = re.sub(r"[^a-z0-9]+", "-", wiki.root.name.lower()).strip("-") or "llm"
        cfg["name"] = base if base.endswith("wiki") else f"{base}-wiki"
    cfg["title"] = cfg.get("title") or cfg["name"]
    cfg["repository"] = cfg.get("repository") or wiki.root.name
    name = str(cfg["name"])
    if not SKILL_NAME_RE.match(name):
        print(f"publish.name must be kebab-case ASCII, got: {name}", file=sys.stderr)
        return 1

    check = run_check(wiki)
    if check["errors"]:  # publish always blocks on error level, whatever lint.fail_on says
        print(f"check reports {len(check['errors'])} error(s); fix them before publishing:", file=sys.stderr)
        for e in check["errors"]:
            print(f"  [{e['kind']}] {e['path']}: {e['message']}", file=sys.stderr)
        return 1

    ceiling = str(cfg.get("max_sensitivity") or "internal")
    if ceiling not in SENSITIVITY_ORDER:
        print(f"publish.max_sensitivity must be one of {SENSITIVITY_ORDER}, got: {ceiling}", file=sys.stderr)
        return 1
    default_sens = str(wiki.config.get("default_sensitivity") or "internal")
    too_sensitive = []
    for p in wiki.pages():
        fm, _ = parse_frontmatter(read_text(p))
        sens = str((fm or {}).get("sensitivity") or default_sens)
        if sens in SENSITIVITY_ORDER and SENSITIVITY_ORDER.index(sens) > SENSITIVITY_ORDER.index(ceiling):
            too_sensitive.append(f"{wiki.rel(p)} ({sens})")
    if too_sensitive:
        print(f"pages above publish.max_sensitivity={ceiling}. A published skill leaves this repository: "
              "reclassify the page, raise the ceiling on purpose, or do not publish.", file=sys.stderr)
        for line in too_sensitive:
            print(f"  {line}", file=sys.stderr)
        return 1

    # The published layout keeps this wiki's own directory names, so every relative link
    # inside the pages ("../../docs/adr-001.md") resolves the same inside the skill.
    try:
        wiki_rel, raw_rel = wiki.rel(wiki.wiki_dir), wiki.rel(wiki.raw_dir)
    except ValueError:
        print("publish needs paths.wiki and paths.raw to live inside the repository", file=sys.stderr)
        return 1
    cfg["wiki_dir"], cfg["raw_dir"] = wiki_rel, raw_rel

    skill_text, origin = _consumer_skill_text(wiki, cfg)
    if skill_text is None:
        print(origin, file=sys.stderr)
        return 1
    fm, _ = parse_frontmatter(skill_text)
    if not fm or fm.get("name") != name:
        print(f"{origin}: frontmatter `name` must be `{name}` (publish.name)", file=sys.stderr)
        return 1
    for wrong, right in (("references/wiki/", f"references/{wiki_rel}/"),
                         ("references/raw/", f"references/{raw_rel}/")):
        if wrong != right and wrong in skill_text:
            print(f"{origin}: says '{wrong}' but this wiki publishes to '{right}'", file=sys.stderr)
            return 1

    skill_dir = (wiki.root / (out or str(cfg.get("out") or "dist")) / name).resolve()
    if skill_dir == wiki.root.resolve() or wiki.wiki_dir.resolve().is_relative_to(skill_dir):
        print(f"refusing to build into {skill_dir}", file=sys.stderr)
        return 1
    if skill_dir.exists():
        shutil.rmtree(skill_dir)
    refs = skill_dir / "references"
    shutil.copytree(wiki.wiki_dir, refs / wiki_rel, ignore=shutil.ignore_patterns(".gitkeep", "log.md"))
    include_raw = str(cfg.get("include_raw", "true")).strip().lower() not in ("false", "no", "0")
    if include_raw and wiki.raw_dir.is_dir():
        shutil.copytree(wiki.raw_dir, refs / raw_rel, ignore=shutil.ignore_patterns(".gitkeep"))
    for d in sorted((x for x in refs.rglob("*") if x.is_dir()), reverse=True):
        if not any(d.iterdir()):
            d.rmdir()  # empty categories do not ship
    (skill_dir / "SKILL.md").write_text(skill_text, encoding="utf-8", newline="\n")

    commit = _git(wiki.root, "rev-parse", "--short", "HEAD") or "no-git"
    if _git(wiki.root, "status", "--porcelain", "--", wiki.rel(wiki.wiki_dir), wiki.rel(wiki.raw_dir)):
        commit += "-dirty"
    total = list(wiki.sources())
    cited = wiki.ingested_by()
    ingested = sum(1 for s in total if s.resolve().as_posix() in cited)
    by_cat: dict[str, int] = {}
    for p in wiki.pages():
        parts = p.relative_to(wiki.wiki_dir).parts
        if len(parts) > 1:
            by_cat[parts[0]] = by_cat.get(parts[0], 0) + 1
    raw_note = (f"all sources ship under `{raw_rel}/`, compiled or not; see `{wiki_rel}/manifest.md`"
                if include_raw else "sources are not shipped; the pages are the only evidence available")
    (refs / "VERSION.md").write_text(
        "# Packaged wiki version\n\n"
        f"- Version: `{commit}` (commit of `{cfg['repository']}`)\n"
        f"- Built: {dt.date.today().isoformat()}\n"
        f"- Pages: {check['summary']['pages']}" + "".join(f" · {k}: {v}" for k, v in sorted(by_cat.items())) + "\n"
        f"- Sources compiled: {ingested} of {len(total)} ({raw_note})\n",
        encoding="utf-8", newline="\n")

    broken = []
    raw_out = (refs / raw_rel).resolve()
    for page in sorted((refs / wiki_rel).rglob("*.md")):
        for _, target in MD_LINK_RE.findall(read_text(page)):
            resolved = resolve_link(page, target, skill_dir)
            if resolved is None or (not include_raw and resolved.is_relative_to(raw_out)):
                continue
            if not resolved.exists() or not resolved.is_relative_to(skill_dir):
                broken.append(f"{page.relative_to(skill_dir).as_posix()} -> {target}")
    if broken:
        print("links that do not resolve inside the published skill:", file=sys.stderr)
        for b in broken:
            print(f"  {b}", file=sys.stderr)
        return 1

    files = [x for x in skill_dir.rglob("*") if x.is_file()]
    words = sum(len(read_text(x).split()) for x in files if x.suffix == ".md")
    print(f"{skill_dir.as_posix()}: {len(files)} files, {words} words, version {commit}")
    for target in install:
        for rel in INSTALL_DIRS:
            dest = Path(target).resolve() / rel / name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(skill_dir, dest)
            print(f"installed: {dest.as_posix()}")
    return 0


def main(argv=None) -> int:
    _utf8_when_piped()
    ap = argparse.ArgumentParser(description="LLM Wiki deterministic helpers")
    ap.add_argument("--version", action="version", version=KIT_VERSION)
    ap.add_argument("--root", default=".", help="repository root (default: cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("check"); s.add_argument("--json", action="store_true")
    s.add_argument("--fail-on", default=None, choices=[*LEVELS, "never"],
                   help="exit 1 from this severity up (default: lint.fail_on in config, else error)")
    s = sub.add_parser("index"); s.add_argument("--write", action="store_true")
    s = sub.add_parser("manifest"); s.add_argument("--write", action="store_true")
    s = sub.add_parser("publish"); s.add_argument("--out", default=None)
    s.add_argument("--install", action="append", default=[], metavar="REPO")
    s = sub.add_parser("scan"); s.add_argument("paths", nargs="+"); s.add_argument("--json", action="store_true")
    s = sub.add_parser("seen"); s.add_argument("urls", nargs="+"); s.add_argument("--json", action="store_true")
    s = sub.add_parser("log-tail"); s.add_argument("-n", type=int, default=5)
    s = sub.add_parser("log-append")
    s.add_argument("--op", required=True); s.add_argument("--title", required=True)
    s.add_argument("--agent", default=os.environ.get("LLM_WIKI_AGENT", "unknown"))
    s.add_argument("--files", default=""); s.add_argument("--approved-by", default="")
    s.add_argument("--notes", default="")
    a = ap.parse_args(argv)

    if a.cmd == "scan":  # works on any text, inside a wiki or not
        return cmd_scan(a.paths, a.json)

    wiki = Wiki(Path(a.root).resolve())
    if not wiki.exists():
        print(f"no {wiki.rel(wiki.wiki_dir)}/ directory under {wiki.root}. Run the wiki skill (init) first.", file=sys.stderr)
        return 2
    if a.cmd == "check":
        return cmd_check(wiki, a.json, a.fail_on)
    if a.cmd == "index":
        return cmd_index(wiki, a.write)
    if a.cmd == "manifest":
        return cmd_manifest(wiki, a.write)
    if a.cmd == "publish":
        return cmd_publish(wiki, a.out, a.install)
    if a.cmd == "seen":
        return cmd_seen(wiki, a.urls, a.json)
    if a.cmd == "log-tail":
        return cmd_log_tail(wiki, a.n)
    if a.cmd == "log-append":
        return cmd_log_append(wiki, a.op, a.title, a.agent, a.files, a.approved_by, a.notes)
    return 1


if __name__ == "__main__":
    sys.exit(main())
