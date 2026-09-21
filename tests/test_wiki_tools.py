"""Tests for the deterministic helper shipped by the wiki skill. Standard library only.

Run from the repository root:
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import contextlib
import datetime as dt
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ASSETS = REPO / "skills" / "wiki" / "assets"
SCRIPT = ASSETS / "scripts" / "wiki_tools.py"

_spec = importlib.util.spec_from_file_location("wiki_tools", SCRIPT)
wiki_tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wiki_tools)


def page(title: str, type_: str, status: str = "draft", extra: str = "") -> str:
    return (f"---\ntitle: {title}\ntype: {type_}\nstatus: {status}\n"
            f"created: 2026-01-01\nupdated: 2026-01-01\n{extra}---\n\n# {title}\n")


class WikiCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def build(self, files: dict[str, str], config: str | None = None, wiki_dir: str = "wiki") -> None:
        """Write `files` (repo-relative path -> content) plus a minimal index, log and optional config."""
        files = {f"{wiki_dir}/log.md": "# Log do wiki\n", **files}
        files.setdefault(f"{wiki_dir}/index.md", "# Índice do wiki\n")
        if config is not None:
            files[".llm-wiki/config.yml"] = config
        for rel, content in files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")

    def run_tool(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = wiki_tools.main(["--root", str(self.root), *args])
        return code, out.getvalue()

    def check(self) -> dict:
        _, out = self.run_tool("check", "--json")
        return json.loads(out)

    def messages(self, kind: str, level: str = "errors") -> list[str]:
        return [f"{e['path']}: {e['message']}" for e in self.check()[level] if e["kind"] == kind]


class DefaultVocabulary(WikiCase):
    def test_without_config_the_builtin_types_apply(self):
        self.build({
            "wiki/entities/acme.md": page("Acme", "entity"),
            "wiki/entities/adr-1.md": page("ADR 1", "decision"),
        })
        errors = self.messages("frontmatter")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("unknown type 'decision'", errors[0])
        self.assertIn("valid: comparison, concept, entity", errors[0])

    def test_shipped_config_declares_exactly_the_builtin_defaults(self):
        cfg = wiki_tools.parse_yaml((ASSETS / "config.yml").read_text(encoding="utf-8").splitlines())
        shipped, builtin = wiki_tools.Schema(cfg), wiki_tools.Schema({})
        self.assertEqual(shipped.problems, [])
        self.assertEqual(shipped.categories, builtin.categories)
        self.assertEqual(shipped.type_of_dir, builtin.type_of_dir)
        self.assertEqual(shipped.types, builtin.types)
        self.assertEqual(shipped.statuses, builtin.statuses)
        self.assertEqual(shipped.required_by_type, builtin.required_by_type)

    def test_legacy_list_of_categories_still_works(self):
        self.build({"wiki/concepts/x.md": page("X", "concept")},
                   config="categories:\n  - sources\n  - concepts\n")
        self.assertEqual(self.messages("frontmatter"), [])
        self.assertEqual(self.messages("config", "warnings"), [])

    def test_legacy_list_cannot_name_a_custom_directory(self):
        self.build({}, config="categories:\n  - sources\n  - decisions\n")
        warnings = self.messages("config", "warnings")
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("category 'decisions' has no page type", warnings[0])


class CustomVocabulary(WikiCase):
    CONFIG = (
        "categories:\n"
        "  sources: source\n"
        "  decisions: decision   # tipo novo\n"
        "category_labels:\n"
        "  decisions: Decisões (ADRs)\n"
        "statuses: [draft, reviewed, vigente]\n"
        "required_by_type:\n"
        "  decision: [sources, adr_id]\n"
        "enums:\n"
        "  decision_status: [proposed, accepted, superseded]\n"
        "  source_meta.kind: [adr, guideline]\n"
    )
    ADR = "sources: [raw/adrs/adr-001.md]\nadr_id: ADR-001\n"

    def test_custom_type_is_accepted_and_undeclared_builtin_is_not(self):
        self.build({
            "raw/adrs/adr-001.md": "# ADR-001\n",
            "wiki/decisions/adr-001.md": page("ADR-001", "decision", extra=self.ADR),
            "wiki/decisions/acme.md": page("Acme", "entity"),
        }, config=self.CONFIG)
        errors = self.messages("frontmatter")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("wiki/decisions/acme.md: unknown type 'entity'", errors[0])
        self.assertEqual(self.messages("config", "warnings"), [])

    def test_placement_follows_the_configured_mapping(self):
        self.build({
            "raw/adrs/adr-001.md": "# ADR-001\n",
            "wiki/sources/adr-001.md": page("ADR-001", "decision", extra=self.ADR),
        }, config=self.CONFIG)
        warnings = self.messages("placement", "warnings")
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("type 'decision' inside 'sources/' (expected 'source')", warnings[0])

    def test_custom_statuses_replace_the_defaults(self):
        self.build({
            "raw/adrs/adr-001.md": "# ADR-001\n",
            "wiki/decisions/a.md": page("A", "decision", status="vigente", extra=self.ADR),
            "wiki/decisions/b.md": page("B", "decision", status="stale", extra=self.ADR),
        }, config=self.CONFIG)
        errors = self.messages("frontmatter")
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("wiki/decisions/b.md: unknown status 'stale'", errors[0])

    def test_required_by_type_adds_to_the_builtin_source_rule(self):
        self.build({
            "raw/adrs/adr-001.md": "# ADR-001\n",
            "wiki/decisions/a.md": page("A", "decision", extra="sources: [raw/adrs/adr-001.md]\n"),
            "wiki/sources/s.md": page("S", "source"),
        }, config=self.CONFIG)
        errors = self.messages("frontmatter")
        self.assertEqual(sorted(errors), [
            "wiki/decisions/a.md: type 'decision' requires non-empty 'adr_id'",
            "wiki/sources/s.md: type 'source' requires non-empty 'sources'",
        ])

    def test_enums_validate_plain_and_dotted_keys(self):
        extra = self.ADR + "decision_status: aceito\nsource_meta:\n  kind: memo\n"
        self.build({
            "raw/adrs/adr-001.md": "# ADR-001\n",
            "wiki/decisions/a.md": page("A", "decision", extra=extra),
            "wiki/decisions/b.md": page("B", "decision", extra=self.ADR + "decision_status: accepted\n"),
        }, config=self.CONFIG)
        errors = self.messages("frontmatter")
        self.assertEqual(sorted(errors), [
            "wiki/decisions/a.md: invalid decision_status 'aceito' (valid: proposed, accepted, superseded)",
            "wiki/decisions/a.md: invalid source_meta.kind 'memo' (valid: adr, guideline)",
        ])

    def test_index_uses_configured_order_and_labels(self):
        self.build({
            "raw/adrs/adr-001.md": "# ADR-001\n",
            "wiki/decisions/adr-001.md": page("ADR-001", "decision", extra=self.ADR),
            "wiki/misc/solta.md": page("Solta", "source"),
        }, config=self.CONFIG)
        _, out = self.run_tool("index")
        headings = [line for line in out.splitlines() if line.startswith("## ")]
        self.assertEqual(headings, ["## Overview", "## Sources", "## Decisões (ADRs)", "## Other"])
        self.assertIn("- [ADR-001](decisions/adr-001.md)", out)

    def test_malformed_config_is_reported_not_raised(self):
        self.build({}, config="categories: sources\nstatuses:\n  a: b\nrequired_by_type:\n  ghost: [x]\nenums:\n  k:\n")
        warnings = self.messages("config", "warnings")
        self.assertEqual(len(warnings), 4, warnings)


class ConfiguredPaths(WikiCase):
    def test_wiki_and_raw_directories_come_from_config(self):
        self.build({
            "fontes/adrs/adr-001.md": "# ADR-001\n",
            "fontes/anexos/diagrama.png": "",
            "kb/sources/adr-001.md": page("ADR-001", "source", extra="sources: [fontes/adrs/adr-001.md]\n"),
        }, config="paths:\n  wiki: kb\n  raw: fontes\n  assets: fontes/anexos\n", wiki_dir="kb")
        result = self.check()
        self.assertEqual([e for e in result["errors"] if e["kind"] == "raw-ref"], [])
        self.assertEqual([w for w in result["warnings"] if w["kind"] in ("raw-ref", "unreferenced-raw")], [])
        self.assertEqual(result["summary"]["pages"], 1)
        self.assertIn("kb/sources/adr-001.md: page missing from kb/index.md", self.messages("index"))


class Manifest(WikiCase):
    SRC = "# ADR-001: Usar PostgreSQL\n\nCorpo.\n"

    def build_with_sources(self, **kwargs):
        self.build({
            "raw/adrs/adr-001.md": self.SRC,
            "raw/adrs/adr-002.md": "---\ntitle: Cache local\n---\n\nSem H1.\n",
            "raw/guides/style.md": "Sem título nenhum.\n",
            "raw/assets/diagrama.png": "",
            "wiki/sources/adr-001.md": page("ADR-001", "source", extra="sources: [raw/adrs/adr-001.md]\n"),
            # Cita a mesma fonte e vem antes na ordem alfabética: não pode virar "a página" dela.
            "wiki/concepts/evento.md": page("Evento", "concept", extra="sources: [raw/adrs/adr-001.md]\n"),
        }, **kwargs)

    def test_manifest_lists_every_source_with_title_page_and_hash(self):
        self.build_with_sources()
        _, out = self.run_tool("manifest")
        self.assertIn("3 fontes, 1 ingerida, 2 pendentes", out)
        self.assertIn("## adrs (2)", out)
        self.assertIn("## guides (1)", out)
        # Fonte ingerida: título e link vêm da página em sources/, não do conceito que também a cita.
        self.assertIn("| `adrs/adr-001.md` | ADR-001 | [ADR-001](sources/adr-001.md) |", out)
        self.assertNotIn("evento.md", out)
        self.assertIn("| `adrs/adr-002.md` | Cache local | — (não ingerida) |", out)  # título do frontmatter
        self.assertIn("| `guides/style.md` | style | — (não ingerida) |", out)           # sem título: o stem
        self.assertNotIn("diagrama.png", out)  # assets não são fontes

    def test_hash_ignores_line_endings(self):
        self.build_with_sources()
        crlf = self.root / "raw/adrs/adr-001.md"
        lf_hash = wiki_tools.source_hash(crlf)
        crlf.write_bytes(self.SRC.replace("\n", "\r\n").encode("utf-8"))
        self.assertEqual(wiki_tools.source_hash(crlf), lf_hash)

    def test_check_flags_a_source_whose_content_moved(self):
        self.build_with_sources()
        self.run_tool("manifest", "--write")
        self.assertEqual(self.messages("source-changed", "warnings"), [])
        (self.root / "raw/adrs/adr-001.md").write_text(self.SRC + "\nRegra nova.\n", encoding="utf-8")
        warnings = self.messages("source-changed", "warnings")
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("raw/adrs/adr-001.md: content differs", warnings[0])

    def test_check_flags_sources_added_or_removed_since_the_manifest(self):
        self.build_with_sources()
        self.run_tool("manifest", "--write")
        (self.root / "raw/adrs/adr-003.md").write_text("# ADR-003\n", encoding="utf-8")
        (self.root / "raw/guides/style.md").unlink()
        warnings = sorted(self.messages("manifest", "warnings"))
        self.assertEqual(len(warnings), 2, warnings)
        self.assertIn("raw/adrs/adr-003.md: source missing from wiki/manifest.md", warnings[0])
        self.assertIn("no longer exists: guides/style.md", warnings[1])

    def test_backlog_is_one_warning_once_a_manifest_exists(self):
        self.build_with_sources()
        per_file = self.messages("unreferenced-raw", "warnings")
        self.assertEqual(len(per_file), 2, per_file)  # sem manifesto: um aviso por fonte
        self.run_tool("manifest", "--write")
        summary = self.messages("unreferenced-raw", "warnings")
        self.assertEqual(len(summary), 1, summary)
        self.assertIn("wiki/manifest.md: 2 source(s) not referenced", summary[0])

    def test_manifest_is_not_treated_as_a_page(self):
        self.build_with_sources()
        self.run_tool("manifest", "--write")
        result = self.check()
        self.assertEqual(result["summary"]["pages"], 2)  # sources/adr-001.md e concepts/evento.md
        self.assertEqual([e for e in result["errors"] if e["kind"] == "frontmatter"], [])

    def test_manifest_respects_configured_paths(self):
        self.build({
            "fontes/adrs/adr-001.md": self.SRC,
            "kb/sources/adr-001.md": page("ADR-001", "source", extra="sources: [fontes/adrs/adr-001.md]\n"),
        }, config="paths:\n  wiki: kb\n  raw: fontes\n", wiki_dir="kb")
        code, out = self.run_tool("manifest", "--write")
        self.assertEqual(code, 0)
        self.assertIn("`fontes/`", (self.root / "kb/manifest.md").read_text(encoding="utf-8"))


class Publish(WikiCase):
    CONFIG = ("publish:\n  name: acme-wiki\n  title: Wiki da Acme\n"
              "  description: Use para qualquer pergunta sobre cache e banco na Acme.\n")

    def build_publishable(self, config=None, extra_page: str = ""):
        template = (ASSETS / "templates" / "consumer-skill.md").read_text(encoding="utf-8")
        source_page = (page("ADR-001", "source", extra="sources: [raw/adrs/adr-001.md]\n" + extra_page)
                       + "\nVer [a fonte](../../raw/adrs/adr-001.md).\n")
        self.build({
            "raw/adrs/adr-001.md": "# ADR-001\n",
            "raw/adrs/adr-002.md": "# ADR-002\n",
            "wiki/index.md": "# Índice do wiki\n\n- [ADR-001](sources/adr-001.md) - resumo\n",
            "wiki/sources/adr-001.md": source_page,
            "wiki/entities/.gitkeep": "",
            ".llm-wiki/templates/consumer-skill.md": template,
        }, config=self.CONFIG if config is None else config)

    def publish(self, *args):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code, out = self.run_tool("publish", *args)
        return code, out, err.getvalue()

    def test_builds_a_self_contained_skill(self):
        self.build_publishable()
        code, out, err = self.publish()
        self.assertEqual(code, 0, err)
        skill = self.root / "dist/acme-wiki"
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: acme-wiki", text)
        self.assertIn("# Wiki da Acme", text)
        self.assertNotIn("{{", text)
        self.assertTrue((skill / "references/wiki/sources/adr-001.md").is_file())
        self.assertTrue((skill / "references/raw/adrs/adr-002.md").is_file())  # fonte não ingerida também vai
        self.assertFalse((skill / "references/wiki/log.md").exists())           # trilha do mantenedor fica
        self.assertFalse((skill / "references/wiki/entities").exists())         # categoria vazia não vai
        self.assertIn("Sources compiled: 1 of 2", (skill / "references/VERSION.md").read_text(encoding="utf-8"))

    def test_refuses_without_a_description(self):
        self.build_publishable(config="publish:\n  name: acme-wiki\n")
        code, _, err = self.publish()
        self.assertEqual(code, 1)
        self.assertIn("publish.description is empty", err)

    def test_refuses_when_check_has_errors(self):
        self.build_publishable()
        (self.root / "wiki/sources/quebrada.md").write_text(page("Q", "source"), encoding="utf-8")
        code, _, err = self.publish()
        self.assertEqual(code, 1)
        self.assertIn("fix them before publishing", err)
        self.assertFalse((self.root / "dist").exists())

    def test_refuses_pages_above_the_sensitivity_ceiling(self):
        self.build_publishable(extra_page="sensitivity: confidential\n")
        code, _, err = self.publish()
        self.assertEqual(code, 1)
        self.assertIn("wiki/sources/adr-001.md (confidential)", err)

    def test_without_raw_the_links_to_sources_are_tolerated(self):
        self.build_publishable(config=self.CONFIG + "  include_raw: false\n")
        code, _, err = self.publish()
        self.assertEqual(code, 0, err)
        self.assertFalse((self.root / "dist/acme-wiki/references/raw").exists())

    def test_a_hand_written_skill_wins_over_the_template(self):
        self.build_publishable(config="publish:\n  name: acme-wiki\n")
        custom = self.root / ".llm-wiki/publish/SKILL.md"
        custom.parent.mkdir(parents=True)
        custom.write_text("---\nname: acme-wiki\ndescription: feita à mão\n---\n\n# Minha\n", encoding="utf-8")
        code, _, err = self.publish()
        self.assertEqual(code, 0, err)
        self.assertIn("# Minha", (self.root / "dist/acme-wiki/SKILL.md").read_text(encoding="utf-8"))

    def test_it_keeps_the_configured_directory_names(self):
        """A docs repo that adopts a wiki keeps its `docs/` folder; the links must still resolve."""
        template = (ASSETS / "templates" / "consumer-skill.md").read_text(encoding="utf-8")
        source_page = (page("ADR 1", "source", extra="sources: [docs/adr/adr-001.md]\n")
                       + "\nVer [a fonte](../../docs/adr/adr-001.md).\n")
        self.build({
            "docs/adr/adr-001.md": "# ADR 1\n",
            "wiki/index.md": "# Índice do wiki\n\n- [ADR 1](sources/adr-001.md) - resumo\n",
            "wiki/sources/adr-001.md": source_page,
            ".llm-wiki/templates/consumer-skill.md": template,
        }, config="paths:\n  raw: docs\n" + self.CONFIG)
        code, _, err = self.publish()
        self.assertEqual(code, 0, err)
        skill = self.root / "dist/acme-wiki"
        self.assertTrue((skill / "references/docs/adr/adr-001.md").is_file())
        self.assertFalse((skill / "references/raw").exists())
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/docs/", text)
        self.assertNotIn("references/raw/", text)

    def test_a_hand_written_skill_naming_the_wrong_directory_is_refused(self):
        self.build({
            "docs/adr/adr-001.md": "# ADR 1\n",
            "wiki/index.md": "# Índice do wiki\n",
            ".llm-wiki/publish/SKILL.md": ("---\nname: acme-wiki\ndescription: x\n---\n\n"
                                           "Leia `references/raw/` por completo.\n"),
        }, config="paths:\n  raw: docs\n" + self.CONFIG)
        code, _, err = self.publish()
        self.assertEqual(code, 1)
        self.assertIn("says 'references/raw/' but this wiki publishes to 'references/docs/'", err)

    def test_install_copies_to_both_discovery_directories(self):
        self.build_publishable()
        with tempfile.TemporaryDirectory() as consumer:
            code, out, err = self.publish("--install", consumer)
            self.assertEqual(code, 0, err)
            for rel in (".claude/skills", ".agents/skills"):
                self.assertTrue((Path(consumer) / rel / "acme-wiki/SKILL.md").is_file())


class Seen(WikiCase):
    def test_normalization_ignores_scheme_www_tracking_fragment_and_slash(self):
        n = wiki_tools.normalize_url
        self.assertEqual(n("https://www.Example.com/a/b/?utm_source=x&id=7#top"), n("http://example.com/a/b?id=7"))
        self.assertNotEqual(n("https://example.com/a?id=7"), n("https://example.com/a?id=8"))

    def test_reports_urls_already_captured_in_raw_or_cited_by_pages(self):
        self.build({
            "raw/research/2026-01-01-a.md": "---\nsource_url: https://example.com/post/\ntitle: A\n---\n\nTexto.\n",
            "raw/research/2026-01-02-b.md": "---\nsource_url: pasted\n---\n\nColado.\n",
            "wiki/sources/c.md": page("C", "source", extra="sources: [raw/research/2026-01-02-b.md]\n"
                                                           "source_meta:\n  origin_url: https://papers.example.org/c\n"),
        })
        code, out = self.run_tool("seen", "http://www.example.com/post?utm_campaign=z",
                                  "https://papers.example.org/c/", "https://example.com/other", "--json")
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual([r["seen"] for r in result], [True, True, False])
        self.assertEqual(result[0]["where"], "raw/research/2026-01-01-a.md")
        self.assertEqual(result[1]["where"], "wiki/sources/c.md")

    def test_research_is_a_valid_log_operation(self):
        self.build({})
        code, _ = self.run_tool("log-append", "--op", "research", "--title", "Pergunta")
        self.assertEqual(code, 0)
        self.assertEqual(self.messages("log"), [])


class Scan(WikiCase):
    def scan(self, text: str):
        f = self.root / "nota.md"
        f.write_text(text, encoding="utf-8")
        code, out = self.run_tool("scan", str(f), "--json")
        return code, json.loads(out)

    def test_clean_note_passes_without_a_wiki(self):
        code, found = self.scan("# Nota\n\n- Decisão: usar WAL. Evidência: verified.\nContato: time@example.com\n")
        self.assertEqual((code, found), (0, []))

    def test_finds_known_secret_shapes_and_never_echoes_them(self):
        secret = "ghp_" + "a1B2" * 10
        code, found = self.scan(
            f"token do CI: {secret}\n"
            "DATABASE_URL=postgres://app:s3nh4Forte@db.internal:5432/app\n"
            "senha: hunter2hunter2\n"
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "AKIAABCDEFGHIJKLMNOP\n")
        self.assertEqual(code, 1)
        self.assertEqual({f["kind"] for f in found},
                         {"github-token", "url-credentials", "assignment", "private-key", "aws-access-key"})
        self.assertEqual([f["line"] for f in found], [1, 2, 3, 4, 5])
        self.assertNotIn(secret, json.dumps(found))

    def test_placeholders_and_redactions_are_not_findings(self):
        code, found = self.scan("password: <redacted: senha>\napi_key=${API_KEY}\ntoken: {{token}}\nsenha=********\n")
        self.assertEqual((code, found), (0, []))

    def test_email_is_reported_as_pii(self):
        code, found = self.scan("Falar com maria.silva@empresa.com.br sobre o incidente.\n")
        self.assertEqual(code, 1)
        self.assertEqual([(f["level"], f["kind"]) for f in found], [("pii", "email")])

    def test_capture_is_a_valid_log_operation(self):
        self.build({})
        code, _ = self.run_tool("log-append", "--op", "capture", "--title", "Nota")
        self.assertEqual(code, 0)
        self.assertEqual(self.messages("log"), [])


class NestedYaml(unittest.TestCase):
    """The config needs three levels (lint.freshness.high); the frontmatter needs two."""

    def parse(self, text):
        return wiki_tools.parse_yaml(text.splitlines())

    def test_mappings_nest_as_deep_as_the_config_needs(self):
        got = self.parse(
            "lint:\n"
            "  fail_on: warning\n"
            "  freshness:\n"
            "    high: 30\n"
            "    static: 0\n"
            "  default_volatility: low\n"
            "paths:\n"
            "  wiki: kb\n")
        self.assertEqual(got["lint"]["freshness"], {"high": "30", "static": "0"})
        self.assertEqual(got["lint"]["fail_on"], "warning")
        self.assertEqual(got["lint"]["default_volatility"], "low")  # back out to the parent level
        self.assertEqual(got["paths"], {"wiki": "kb"})

    def test_block_and_inline_lists_survive_nesting(self):
        got = self.parse(
            "statuses:\n"
            "  - draft\n"
            "  - reviewed\n"
            "research:\n"
            "  angles: [technical, contrarian]\n"
            "  block_domains:\n"
            "    - exemplo.com\n"
            "  max_rounds: 2\n")
        self.assertEqual(got["statuses"], ["draft", "reviewed"])
        self.assertEqual(got["research"]["angles"], ["technical", "contrarian"])
        self.assertEqual(got["research"]["block_domains"], ["exemplo.com"])
        self.assertEqual(got["research"]["max_rounds"], "2")

    def test_the_shipped_config_parses_into_the_blocks_the_script_reads(self):
        cfg = self.parse((ASSETS / "config.yml").read_text(encoding="utf-8"))
        for key in ("paths", "categories", "lint", "publish", "research", "capture", "search", "export"):
            self.assertIsInstance(cfg.get(key), dict, key)
        self.assertIsInstance(cfg["lint"]["freshness"], dict)
        self.assertIsInstance(cfg["statuses"], list)


class Severity(WikiCase):
    STALE = "created: 2020-01-01\nupdated: 2020-01-01\n"

    def build_with_orphan(self, config=None):
        page = ("---\ntitle: Solta\ntype: concept\nstatus: draft\n"
                "created: 2026-01-01\nupdated: 2026-01-01\n---\n\n# Solta\n")
        self.build({
            "wiki/concepts/solta.md": page,
            "wiki/index.md": "# Índice do wiki\n\n- [Solta](concepts/solta.md) - resumo\n",
        }, config=config)

    def orphans(self, level: str):
        return [f for f in self.check()[level] if f["kind"] == "orphan"]

    def test_a_wiki_can_lower_a_check_to_info(self):
        self.build_with_orphan()
        self.assertEqual(len(self.orphans("warnings")), 1)
        self.build_with_orphan(config="lint:\n  severity:\n    orphan: info\n")
        self.assertEqual(self.orphans("warnings"), [])
        self.assertEqual(len(self.orphans("infos")), 1)

    def test_off_silences_a_check_entirely(self):
        self.build_with_orphan(config="lint:\n  severity:\n    orphan: off\n")
        self.assertEqual(self.orphans("findings"), [])

    def test_a_wiki_can_raise_a_check_to_error(self):
        self.build_with_orphan(config="lint:\n  severity:\n    orphan: error\n")
        code, _ = self.run_tool("check")
        self.assertEqual(code, 1)

    def test_an_unknown_check_or_level_is_reported_and_ignored(self):
        self.build_with_orphan(config="lint:\n  severity:\n    orfa: info\n    orphan: critical\n")
        problems = " | ".join(self.messages("config", "warnings"))
        self.assertIn("'lint.severity.orfa': unknown check", problems)
        self.assertIn("'lint.severity.orphan': must be one of", problems)
        self.assertEqual([f["kind"] for f in self.check()["warnings"] if f["kind"] == "orphan"], ["orphan"])


class FailOn(WikiCase):
    def build_with_warning(self, config=None):
        self.build({
            "wiki/concepts/solta.md": page("Solta", "concept"),
            "wiki/index.md": "# Índice do wiki\n\n- [Solta](concepts/solta.md) - resumo\n",
        }, config=config)

    def test_default_fails_on_error_only(self):
        self.build_with_warning()
        self.assertTrue([f for f in self.check()["warnings"] if f["kind"] == "orphan"])
        self.assertEqual(self.run_tool("check")[0], 0)  # a warning alone does not fail

    def test_the_flag_overrides_the_config(self):
        self.build_with_warning(config="lint:\n  fail_on: warning\n")
        self.assertEqual(self.run_tool("check")[0], 1)
        self.assertEqual(self.run_tool("check", "--fail-on", "error")[0], 0)
        self.assertEqual(self.run_tool("check", "--fail-on", "never")[0], 0)

    def test_never_tolerates_even_errors(self):
        self.build({"wiki/sources/sem-fonte.md": page("Sem fonte", "source")})
        self.assertEqual(self.run_tool("check")[0], 1)
        self.assertEqual(self.run_tool("check", "--fail-on", "never")[0], 0)

    def test_an_invalid_fail_on_in_config_is_reported_and_falls_back(self):
        self.build_with_warning(config="lint:\n  fail_on: sempre\n")
        self.assertIn("'lint.fail_on': must be one of", " ".join(self.messages("config", "warnings")))
        self.assertEqual(self.run_tool("check")[0], 0)


class Freshness(WikiCase):
    def aged(self, days: int, volatility: str = "") -> str:
        old = (dt.date.today() - dt.timedelta(days=days)).isoformat()
        extra = f"volatility: {volatility}\n" if volatility else ""
        return (f"---\ntitle: Página\ntype: concept\nstatus: draft\n"
                f"created: {old}\nupdated: {old}\n{extra}---\n\n# Página\n")

    def build_aged(self, days: int, volatility: str = "", config=None):
        self.build({
            "wiki/concepts/p.md": self.aged(days, volatility),
            "wiki/index.md": "# Índice do wiki\n\n- [Página](concepts/p.md) - resumo\n",
        }, config=config)
        return [f for f in self.check()["findings"] if f["kind"] == "freshness"]

    def test_a_page_within_its_band_is_not_flagged(self):
        self.assertEqual(self.build_aged(100), [])          # default medium = 180 days

    def test_a_page_past_its_band_is_flagged_as_info(self):
        found = self.build_aged(400)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["level"], "info")
        self.assertIn("volatility 'medium' expects a review every 180", found[0]["message"])

    def test_volatility_in_the_frontmatter_wins(self):
        self.assertEqual(len(self.build_aged(100, "high")), 1)   # 30 days
        self.assertEqual(self.build_aged(400, "static"), [])      # 0 = never stale

    def test_bands_and_the_default_come_from_the_config(self):
        cfg = "lint:\n  default_volatility: high\n  freshness:\n    high: 7\n"
        self.assertEqual(len(self.build_aged(30, config=cfg)), 1)
        self.assertEqual(self.build_aged(3, config=cfg), [])

    def test_an_unknown_volatility_is_a_frontmatter_problem_not_a_silent_pass(self):
        self.build({
            "wiki/concepts/p.md": self.aged(400, "quando-der"),
            "wiki/index.md": "# Índice do wiki\n\n- [Página](concepts/p.md) - resumo\n",
        })
        # frontmatter problems are errors, like an unknown type or status
        self.assertIn("unknown volatility 'quando-der'", " ".join(self.messages("frontmatter")))


class ExampleWiki(unittest.TestCase):
    """examples/team-wiki is documentation: if it stops being a valid wiki, the docs lie."""

    EXAMPLE = REPO / "examples" / "team-wiki"

    def test_check_passes_with_no_errors_and_no_warnings(self):
        wiki = wiki_tools.Wiki(self.EXAMPLE)
        result = wiki_tools.run_check(wiki)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])

    def test_index_and_manifest_are_up_to_date_and_fully_summarized(self):
        index = (self.EXAMPLE / "wiki/index.md").read_text(encoding="utf-8")
        self.assertNotIn("(no summary)", index)
        wiki = wiki_tools.Wiki(self.EXAMPLE)
        sources = list(wiki.sources())
        self.assertTrue(sources)
        manifest = (self.EXAMPLE / "wiki/manifest.md").read_text(encoding="utf-8")
        recorded = wiki_tools.parse_manifest(manifest)
        for p in sources:
            rel = p.relative_to(wiki.raw_dir).as_posix()
            self.assertEqual(recorded.get(rel), wiki_tools.source_hash(p), rel)

    def test_it_ships_its_own_copy_of_the_helper_at_the_current_version(self):
        local = self.EXAMPLE / ".llm-wiki/scripts/wiki_tools.py"
        self.assertIn(f'KIT_VERSION = "{wiki_tools.KIT_VERSION}"', local.read_text(encoding="utf-8"))


class ShippedSkills(unittest.TestCase):
    """Limits of the Agent Skills spec that no tool reports until the skill silently fails to load."""

    def test_descriptions_are_ascii_and_within_1024_chars(self):
        files = list((REPO / "skills").glob("*/SKILL.md")) + list((REPO / "agents").glob("*.md"))
        self.assertGreaterEqual(len(files), 2)
        for f in files:
            fm, _ = wiki_tools.parse_frontmatter(f.read_text(encoding="utf-8"))
            desc = fm["description"]
            self.assertLessEqual(len(desc), 1024, f.name)
            self.assertTrue(desc.isascii(), f.name)
            self.assertEqual(fm["name"], f.parent.name if f.name == "SKILL.md" else f.stem)

    def test_every_manifest_and_the_helper_agree_on_the_version(self):
        import re
        versions = {"wiki_tools.py": wiki_tools.KIT_VERSION}
        for rel in (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"):
            manifest = json.loads((REPO / rel).read_text(encoding="utf-8"))
            versions[rel] = manifest["version"]
            for plugin in manifest.get("plugins", []):  # marketplace repeats it per plugin
                versions[f"{rel}:{plugin['name']}"] = plugin["version"]
        versions["apm.yml"] = re.search(r"^version: (\S+)", (REPO / "apm.yml").read_text(encoding="utf-8"), re.M).group(1)
        for f in (REPO / "skills").glob("*/SKILL.md"):
            fm, _ = wiki_tools.parse_frontmatter(f.read_text(encoding="utf-8"))
            versions[f.parent.name] = fm["metadata"]["version"]
        self.assertEqual(len(set(versions.values())), 1, versions)

    def test_every_operation_in_the_router_has_its_reference(self):
        import re
        router = (REPO / "skills/wiki/SKILL.md").read_text(encoding="utf-8")
        refs = set(re.findall(r"`(references/[a-z]+\.md)`", router))
        self.assertGreaterEqual(len(refs), 10)
        for ref in refs:
            self.assertTrue((REPO / "skills/wiki" / ref).is_file(), ref)


class PipedOutput(unittest.TestCase):
    def test_output_is_utf8_when_captured(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "wiki").mkdir()
            proc = subprocess.run([sys.executable, str(SCRIPT), "--root", tmp, "index"],
                                  capture_output=True, check=True)
        self.assertIn("# Índice do wiki", proc.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
