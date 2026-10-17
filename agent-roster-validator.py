#!/usr/bin/env python3
"""
Agent Roster Validator
======================
Validates the multi-tier agent roster (the .agent.md prompt files) for the 3-tier
Orchestrator architecture. The architecture is instruction-based (declarative prompt
files), so "testing" here means verifying *definitions* and *routing consistency*,
not running executable code.

Checks performed:
  [DEF-1] Each .agent.md has valid YAML frontmatter with required fields.
  [DEF-2] frontmatter `name` matches the filename stem exactly (no spaces).
  [DEF-3] `description` and `tools` are present.
  [DEF-4] `tools` entries are well-formed.
  [RST-1] Every leaf referenced by a router's `agents:` list resolves to a real file
          whose frontmatter `name` matches (no dangling/unknown references).
  [RST-2] Every agent file is reachable: listed in a router's `agents:` list, the
          Orchestrator's `agents:` list, or the README routing rules (backtick refs).
          Catches orphaned files with no routing entry.
  [RST-3] Every leaf named in the README routing rules / Domain Map resolves to a real file.

Exit code 0 = PASS, 1 = FAIL.
"""

import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "[ERROR] PyYAML is required but not installed. Install with:\n"
        "   python -m pip install pyyaml\n"
    )
    sys.exit(2)


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
# Resolve the prompts directory relative to this script so the validator is portable.
PROMPTS_DIR = Path(__file__).resolve().parent
README_PATH = PROMPTS_DIR / "README.md"
AGENT_GLOB = "*.agent.md"

# Required frontmatter fields.
REQUIRED_FIELDS = ("name", "description", "tools")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def parse_frontmatter(text):
    """
    Return the parsed YAML frontmatter dict, or None with an error string if the
    file has no valid frontmatter block.
    """
    if not text.startswith("---"):
        return None, "file does not start with a YAML frontmatter delimiter (---)"
    lines = text.splitlines()
    # Find the opening delimiter line index.
    open_idx = next(i for i, line in enumerate(lines) if line.strip() == "---")
    # Collect lines until the next '---' delimiter.
    content_lines = []
    for line in lines[open_idx + 1:]:
        if line.strip() == "---":
            break
        content_lines.append(line)
    raw = "\n".join(content_lines)
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:  # noqa
        return None, f"frontmatter is not valid YAML: {exc}"
    if not isinstance(data, dict):
        return None, "frontmatter block is not a mapping (missing '---' closing delimiter?)"
    return data, None


def filename_stem(path: Path) -> str:
    """Return the filename stem (path without the .agent.md extension)."""
    return path.with_suffix("").name


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_agents():
    """
    Discover and parse every .agent.md file.
    Returns:
      files:   list of (Path, name, raw_text)
      registry: dict name -> Path  (canonical frontmatter name -> file)
      stems:   dict stem -> Path  (filename stem -> file)
      frontmatters: dict stem -> frontmatter dict
    """
    files = []
    registry = {}   # canonical name -> Path
    stems = {}      # stem -> Path
    frontmatters = {}  # stem -> dict
    for path in sorted(PROMPTS_DIR.glob(AGENT_GLOB)):
        text = path.read_text(encoding="utf-8")
        name, err = parse_frontmatter(text)
        entry = {
            "path": path,
            "stem": filename_stem(path),
            "name": name.get("name") if isinstance(name, dict) else None,
            "err": err,
            "fm": name if isinstance(name, dict) else {},
        }
        files.append(entry)
        if entry["name"]:
            registry[entry["name"]] = path
            stems[entry["stem"]] = path
        if entry["stem"]:
            stems.setdefault(entry["stem"], path)
    return files, registry, stems, frontmatters


def load_readme_refs(files, registry):
    """
    Parse README.md and return:
      router_agents: list of router frontmatter `agents` lists (from routers)
      orchestrator_agents: Orchestrator frontmatter agents list
      readme_refs: set of canonical names referenced via backticks in the README
    """
    readme = README_PATH.read_text(encoding="utf-8")

    # Backtick-quoted references in the README (routing rules / Domain Map).
    readme_refs = set()
    for tok in re.findall(r"`([^`]+)`", readme):
        if tok in registry:
            readme_refs.add(tok)

    # Router agents lists (frontmatter `agents:` of files whose name ends with 'Router').
    router_agents = []
    for f in files:
        if f["fm"].get("name", "").endswith("Router"):
            agents = f["fm"].get("agents")
            router_agents.append([a for a in (agents or []) if isinstance(a, str)])
    # Orchestrator agents list.
    orch = next((f["fm"] for f in files if f["fm"].get("name") == "Orchestrator"), {}).get("agents")
    orchestrator_agents = [a for a in (orch or []) if isinstance(a, str)]

    return router_agents, orchestrator_agents, readme_refs


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #
class Report:
    def __init__(self):
        self.findings = []  # list of dicts: {check, file, message}
        self.check_counts = {}

    def add(self, check, path, message):
        self.findings.append({"check": check, "path": str(path), "message": message})
        self.check_counts[check] = self.check_counts.get(check, 0) + 1


def check_definition(files, report):
    """DEF checks: frontmatter validity, name/stem match, required fields, tools."""
    for f in files:
        stem = f["stem"]
        if f["err"]:
            report.add("DEF-1", f["path"], f"Invalid frontmatter: {f['err']}")
            continue
        fm = f["fm"]
        # DEF-1: required fields present.
        for field in REQUIRED_FIELDS:
            if field not in fm:
                report.add("DEF-1", f["path"], f"Missing required frontmatter field: '{field}'")
        # DEF-2: name matches stem exactly (no spaces).
        if f["name"] is not None:
            if f["name"] != stem:
                report.add("DEF-2", f["path"],
                           f"frontmatter name '{f['name']}' does not match filename stem '{stem}' "
                           f"(must be identical, no spaces)")
            if " " in (f["name"] or ""):
                report.add("DEF-2", f["path"], f"frontmatter name '{f['name']}' contains spaces; "
                                              f"use the stem form instead")
        # DEF-3: description present.
        if not fm.get("description"):
            report.add("DEF-3", f["path"], "Missing 'description' field")
        # DEF-4: tools present and well-formed.
        tools = fm.get("tools")
        if tools is None:
            report.add("DEF-4", f["path"], "Missing 'tools' field")
        elif not isinstance(tools, list) or len(tools) == 0:
            report.add("DEF-4", f["path"], "'tools' must be a non-empty list")
        else:
            for tool in tools:
                if not isinstance(tool, str) or "/" not in tool and "*" not in tool:
                    report.add("DEF-4", f["path"], f"Malformed tool entry: {tool!r} "
                                                  f"(expected 'group/operation' or 'group/*' form)")


def check_reachability(files, registry, stems, router_agents, orchestrator_agents, readme_refs, report):
    """RST checks: router leaf resolution, coverage, README routing resolution."""
    # Build the set of all canonical names that reference an agent.
    referenced = set(readme_refs)
    referenced.update(orchestrator_agents)
    for agents in router_agents:
        referenced.update(agents)

    # RST-1: router / Orchestrator agents-list entries must resolve to real files.
    def resolves(name):
        return registry.get(name) is not None

    for f in files:
        if not f["fm"].get("name", "").endswith("Router"):
            continue
        for leaf in f["fm"].get("agents", []):
            if not isinstance(leaf, str):
                report.add("RST-1", f["path"], f"Non-string entry in agents list: {leaf!r}")
                continue
            if not resolves(leaf):
                report.add("RST-1", f["path"], f"Agent '{leaf}' referenced by this router does not exist "
                                              f"(missing file or name mismatch)")

    # Orchestrator agents resolution.
    orch = next((f for f in files if f["fm"].get("name") == "Orchestrator"), None)
    if orch:
        for leaf in orch["fm"].get("agents", []):
            if not isinstance(leaf, str) or not resolves(leaf):
                report.add("RST-1", orch["path"], f"Agent '{leaf}' in Orchestrator agents list does not resolve")

    # RST-2: coverage — every agent file must be reachable.
    for f in files:
        name = f["name"]
        if not name:
            report.add("RST-2", f["path"], "No frontmatter name; cannot determine reachability")
            continue
        if name not in referenced:
            report.add("RST-2", f["path"], f"Agent '{name}' is unreachable — not listed by any router, "
                                          f"the Orchestrator, or in the README routing rules")

    # RST-3: README routing-rule references must resolve.
    for name in sorted(readme_refs):
        if not resolves(name):
            report.add("RST-3", README_PATH, f"README routing rule references '{name}', which does not resolve "
                                            f"(missing file or name mismatch)")


# --------------------------------------------------------------------------- #
# Report generation
# --------------------------------------------------------------------------- #
def build_report(report, files, registry, readme_refs):
    lines = []
    lines.append("# Agent Roster Validation Report")
    lines.append("")
    lines.append(f"Workspace: `{PROMPTS_DIR}`")
    lines.append(f"Agent files: `{len(files)}`")
    lines.append(f"Canonical agents: `{len(registry)}`")
    lines.append("")

    # Summary.
    checks = ("DEF-1", "DEF-2", "DEF-3", "DEF-4", "RST-1", "RST-2", "RST-3")
    passed = all(v == 0 for v in report.check_counts.values())
    total_issues = sum(report.check_counts.values())
    if passed:
        lines.append("## Result: **PASS** — no issues found.")
    else:
        lines.append(f"## Result: **FAIL** — {total_issues} issue(s).")
    lines.append("")

    # Per-check breakdown.
    lines.append("## Check Summary")
    lines.append("")
    lines.append("| Check | Purpose | Issues |")
    lines.append("|---|---|---|")
    for check in checks:
        purpose = {
            "DEF-1": "Frontmatter validity",
            "DEF-2": "name matches filename stem",
            "DEF-3": "description present",
            "DEF-4": "tools well-formed",
            "RST-1": "Router/Orchestrator leaf resolution",
            "RST-2": "Every agent reachable",
            "RST-3": "README routing references resolve",
        }[check]
        lines.append(f"| {check} | {purpose} | {report.check_counts.get(check, 0)} |")
    lines.append("")

    # Detailed findings.
    lines.append("## Detailed Findings")
    lines.append("")
    if not report.findings:
        lines.append("_None._")
    else:
        lines.append("| Check | File | Issue |")
        lines.append("|---|---|---|")
        for finding in report.findings:
            lines.append(f"| {finding['check']} | `{finding['path']}` | {finding['message']} |")
    lines.append("")

    # Roster health.
    lines.append("## Roster Health")
    lines.append("")
    lines.append(f"- Routers: {len([f for f in files if f['fm'].get('name', '').endswith('Router')])}")
    lines.append(f"- Leaf specialists: {len([f for f in files if not f['fm'].get('name', '').endswith('Router')])}")
    lines.append(f"- README routing references: {len(readme_refs)}")
    lines.append("")

    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    files, registry, stems, frontmatters = load_agents()
    router_agents, orchestrator_agents, readme_refs = load_readme_refs(files, registry)
    report = Report()

    try:
        check_definition(files, report)
        check_reachability(files, registry, stems, router_agents, orchestrator_agents, readme_refs, report)
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"[ERROR] validator crashed: {exc}\n")
        sys.exit(2)

    report_md = build_report(report, files, registry, readme_refs)
    out_path = PROMPTS_DIR / "agent-roster-report.md"
    out_path.write_text(report_md, encoding="utf-8")
    print(report_md)

    total_issues = sum(report.check_counts.values())
    sys.exit(1 if total_issues else 0)


if __name__ == "__main__":
    main()
