"""Tests for the deterministic helper shipped by the wiki skill. Standard library only.

Run from the repository root:
    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import contextlib
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

    def test_install_copies_to_both_discovery_directories(self):
        self.build_publishable()
        with tempfile.TemporaryDirectory() as consumer:
            code, out, err = self.publish("--install", consumer)
            self.assertEqual(code, 0, err)
            for rel in (".claude/skills", ".agents/skills"):
                self.assertTrue((Path(consumer) / rel / "acme-wiki/SKILL.md").is_file())


class PipedOutput(unittest.TestCase):
    def test_output_is_utf8_when_captured(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "wiki").mkdir()
            proc = subprocess.run([sys.executable, str(SCRIPT), "--root", tmp, "index"],
                                  capture_output=True, check=True)
        self.assertIn("# Índice do wiki", proc.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
