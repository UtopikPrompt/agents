#!/usr/bin/env python3
"""
Agent Roster Validator
======================
Validates single-dispatcher execution and separate four-level ownership.
The architecture is instruction-based (declarative prompt
files), so "testing" here means verifying *definitions* and *routing consistency*,
not running executable code.

Checks performed:
  [DEF-1] Each .agent.md has valid YAML frontmatter with required fields.
  [DEF-2] frontmatter `name` matches the filename stem exactly (no spaces).
  [DEF-3] `description` and `tools` are present.
  [DEF-4] `tools` entries are well-formed.
  [RST-1] Every leaf referenced by a router's `agents:` list resolves to a real file
          whose frontmatter `name` matches (no dangling/unknown references).
  [RST-2] Every agent file is reachable by delegation from Orchestrator.
  [RST-3] Every leaf named in the README routing rules / Domain Map resolves to a real file.
    [RST-4] Only Orchestrator delegates; each catalog agent has one logical owner.
    [RST-5] Ownership contains no cycles.
    [RST-6] The ownership diagram and Domain Map match the catalog.
    [RST-7] Advisors and workers occupy their documented ownership tiers.
    [CAT-1] The compact catalog resolves all advisors, workers, and route targets.
    [TOOL-1] Role-based tool profiles require needed capabilities and reject excess access.
    [NAM-1] Canonical names follow domain prefixes, role suffixes, and explicit exceptions.
    [DOC-1] README index coverage and embedded routing match the roster and catalog.

Exit code 0 = PASS, 1 = FAIL.
"""

from collections import Counter
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
PROMPTS_DIR = Path(__file__).resolve().parent.parent
README_PATH = PROMPTS_DIR / "README.md"
CATALOG_PATH = PROMPTS_DIR / "Orchestrator.agent.md"
AGENT_GLOB = "*.agent.md"

# Required frontmatter fields.
REQUIRED_FIELDS = ("name", "description", "tools")
TIER1_ADVISORS = {
    "CodeDomainAdvisor", "InfraDevOpsAdvisor",
    "DocsGovernanceAdvisor", "UtilityAdvisor",
}
CODE_SUBADVISORS = {"CodeFrontendAdvisor", "CodeBackendAdvisor"}
DISPATCHER_TOOLS = {"read/readFile", "search", "agent", "vscode/askQuestions"}
READ_ONLY_TOOLS = {
    "Brainstorm": {"read", "search"},
    "CodeFrameworkDiagnostician": {"read", "search"},
    "ContextSummarizer": {"read"},
}
CUSTOMIZATION_WORKERS = {"AgentOptimizer", "GovArchitectureRecordsExpert", "GovDocumentationSuiteGenerator"}
IMPLEMENTATION_TOOLS = {"read", "search", "edit", "execute"}
DOMAIN_PREFIXES = {
    "CodeDomainAdvisor": "Code", "CodeFrontendAdvisor": "Code",
    "CodeBackendAdvisor": "Code", "InfraDevOpsAdvisor": "Infra",
    "DocsGovernanceAdvisor": "Gov",
}
NAMING_EXCEPTIONS = {
    "MultiLanguageBuilder": "CodeDomainAdvisor",
    "AgentOptimizer": "UtilityAdvisor", "Brainstorm": "UtilityAdvisor",
    "ContextSummarizer": "UtilityAdvisor",
}
WORKER_SUFFIXES = (
    "Agent", "Specialist", "Expert", "Generator", "Manager", "Builder",
    "Diagnostician", "Diagnostics", "Generalist", "Engineer", "Profiler",
)


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
    closed = False
    for line in lines[open_idx + 1:]:
        if line.strip() == "---":
            closed = True
            break
        content_lines.append(line)
    if not closed:
        return None, "frontmatter is missing its closing delimiter (---)"
    raw = "\n".join(content_lines)
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:  # noqa
        return None, f"frontmatter is not valid YAML: {exc}"
    if not isinstance(data, dict):
        return None, "frontmatter block is not a mapping (missing '---' closing delimiter?)"
    return data, None


def filename_stem(path: Path) -> str:
    """Return the filename 'stem' of a roster file, i.e. its canonical agent name.
    A roster file is named '<AgentName>.agent.md'; the stem is '<AgentName>'."""
    # Strip the '.md' extension first.
    if path.suffix == ".md":
        path = path.with_suffix("")
    # Strip the '.agent' middle suffix introduced by the '.agent.md' naming.
    if path.name.endswith(".agent"):
        path = path.with_suffix("")
    return path.name


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
            "text": text,
            "stem": filename_stem(path),
            "name": name.get("name") if isinstance(name, dict) else None,
            "err": err,
            "fm": name if isinstance(name, dict) else {},
        }
        files.append(entry)
        if isinstance(entry["name"], str) and entry["name"]:
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

    readme_refs = set()
    prose = re.sub(r"```[^\n]*\n.*?```", "", readme, flags=re.DOTALL)
    for tok in re.findall(r"`([^`\n]+)`", prose):
        if tok in registry or re.fullmatch(
            r"[A-Z][A-Za-z0-9]*(?:Agent|Advisor|Generalist|Specialist|Diagnostician|Diagnostics|Summarizer|Router|Generator|Builder|Expert|Manager|Orchestrator|Implementer|Executor)",
            tok,
        ):
            readme_refs.add(tok)
    readme_refs.update(re.findall(r"^\|\s*\*\*([A-Za-z]\w*)\*\*\s*\|", prose, re.MULTILINE))
    domain_map = re.search(r"^## Domain Map\s*\n(.*?)(?=^## |\Z)", prose, re.MULTILINE | re.DOTALL)
    if domain_map:
        for line in domain_map.group(1).splitlines():
            cells = [cell.strip().strip("`*") for cell in line.strip().strip("|").split("|")]
            if len(cells) != 3 or cells[0] == "Domain Prefix" or set(cells[0]) <= {"-", ":"}:
                continue
            readme_refs.add(cells[1])
            readme_refs.update(child.strip().strip("`*") for child in cells[2].split(","))

    # Router agents lists (frontmatter `agents:` of files whose name ends with 'Router').
    router_agents = []
    for f in files:
        if isinstance(f["name"], str) and f["name"].endswith("Advisor"):
            agents = f["fm"].get("agents")
            router_agents.append([a for a in agents if isinstance(a, str)] if isinstance(agents, list) else [])
    # Orchestrator agents list.
    orch = next((f["fm"] for f in files if f["fm"].get("name") == "Orchestrator"), {}).get("agents")
    orchestrator_agents = [a for a in orch if isinstance(a, str)] if isinstance(orch, list) else []

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
    seen_names = set()
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
            if not isinstance(f["name"], str):
                report.add("DEF-2", f["path"], "frontmatter name must be a string")
                continue
            if f["name"] in seen_names:
                report.add("DEF-2", f["path"], f"Duplicate agent name: '{f['name']}'")
            seen_names.add(f["name"])
            if not re.fullmatch(r"[A-Z][A-Za-z0-9]*", f["name"]):
                report.add("NAM-1", f["path"], "Name must use ASCII PascalCase without separators")
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
        elif not isinstance(tools, list):
            report.add("DEF-4", f["path"], "'tools' must be a list (empty for tool-free advisors)")
        else:
            for tool in tools:
                if not isinstance(tool, str) or " " in tool:
                    report.add("DEF-4", f["path"], f"Malformed tool entry: {tool!r} "
                                                  f"(expected 'group/operation' or 'group/*' form)")


def tool_profile(name):
    if name == "Orchestrator":
        return DISPATCHER_TOOLS, DISPATCHER_TOOLS
    if name.endswith("Advisor"):
        return set(), set()
    if name in READ_ONLY_TOOLS:
        return READ_ONLY_TOOLS[name], READ_ONLY_TOOLS[name]
    if name in CUSTOMIZATION_WORKERS:
        required = {"read", "search", "edit"}
        optional = {"todo"} if name == "GovDocumentationSuiteGenerator" else set()
        return required, required | optional
    if name in {"GovGithubAgent", "GovGitWorkflowAgent"}:
        required = {"github/*", "read", "search", "execute"}
        return required, required
    required = IMPLEMENTATION_TOOLS | ({"github/*"} if name == "InfraCIDiagnostics" else set())
    return required, required | {"todo"}


def check_tool_profiles(files, report):
    for entry in files:
        name, tools = entry["name"], entry["fm"].get("tools")
        if entry["err"] or not isinstance(name, str) or not isinstance(tools, list):
            continue
        if any(not isinstance(tool, str) for tool in tools):
            continue
        actual = set(tools)
        required, allowed = tool_profile(name)
        missing, excess = required - actual, actual - allowed
        if missing or excess or len(actual) != len(tools):
            report.add("TOOL-1", entry["path"],
                       f"Tool profile mismatch: missing {sorted(missing)}, excess {sorted(excess)}, "
                       f"duplicate entries: {len(actual) != len(tools)}")


def check_reachability(files, registry, stems, router_agents, orchestrator_agents, readme_refs, report):
    """RST checks: router leaf resolution, coverage, README routing resolution."""
    adjacency = {}
    for entry in files:
        children = entry["fm"].get("agents", [])
        if isinstance(entry["name"], str):
            adjacency[entry["name"]] = [child for child in children if isinstance(child, str)] if isinstance(children, list) else []
        if "agents" in entry["fm"] and not isinstance(children, list):
            report.add("RST-1", entry["path"], "agents must be a list of agent names")
        elif isinstance(children, list):
            for child in children:
                if not isinstance(child, str) or child not in registry:
                    report.add("RST-1", entry["path"], f"Agent reference {child!r} does not resolve")

    reachable = set()
    pending = ["Orchestrator"] if "Orchestrator" in registry else []
    while pending:
        current = pending.pop()
        if current in reachable:
            continue
        reachable.add(current)
        pending.extend(child for child in adjacency.get(current, []) if child in registry)

    # RST-1: router / Orchestrator agents-list entries must resolve to real files.
    def resolves(name):
        return registry.get(name) is not None

    # RST-2: coverage — every agent file must be reachable.
    for f in files:
        name = f["name"]
        if not name:
            report.add("RST-2", f["path"], "No frontmatter name; cannot determine reachability")
            continue
        if not isinstance(name, str) or name not in reachable:
            report.add("RST-2", f["path"], f"Agent '{name}' is not reachable from Orchestrator")

    # RST-3: README routing-rule references must resolve.
    for name in sorted(readme_refs):
        if not resolves(name):
            report.add("RST-3", README_PATH, f"README routing rule references '{name}', which does not resolve "
                                            f"(missing file or name mismatch)")


def load_catalog(text=None):
    if text is None:
        text = CATALOG_PATH.read_text(encoding="utf-8")
    groups = {}
    for domain, advisor, parent in routing_table_rows(text, "Embedded Ownership", ("Domain", "Advisor", "Parent")):
        if advisor in groups:
            raise ValueError(f"Duplicate ownership advisor: {advisor}")
        groups[advisor] = {
            "domain": domain, "advisor": advisor, "parent": parent,
            "routes": {}, "children": [],
        }
    for group in groups.values():
        parent = group["parent"]
        if parent in groups:
            groups[parent]["children"].append(group["advisor"])
    for cue, worker, advisor in routing_table_rows(text, "Embedded Routing Index", ("Selection Cue", "Worker", "Optional Advisor")):
        if advisor not in groups:
            raise ValueError(f"Unknown routing advisor: {advisor}")
        group = groups[advisor]
        if cue in group["routes"]:
            raise ValueError(f"Duplicate selection cue for {advisor}: {cue}")
        group["routes"][cue] = worker
        if worker not in group["children"]:
            group["children"].append(worker)
    return {"schema_version": 1, "dispatcher": "Orchestrator", "domains": list(groups.values())}


def routing_table_rows(text, heading, headers):
    rows = []
    for line in readme_section(text, heading).splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        if len(cells) != len(headers) or not all(cells):
            raise ValueError(f"Malformed row in {heading}: {line}")
        rows.append(cells)
    if len(rows) < 2 or rows[0] != headers:
        raise ValueError(f"Missing or invalid {heading} table")
    return rows[1:]


def readme_section(readme, heading):
    match = re.search(r"^## " + re.escape(heading) + r"\s*\n(.*?)(?=^## |\Z)", readme, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def check_topology(files, registry, report, readme=None, catalog=None):
    """Validate flat invocation separately from catalog ownership and documentation."""
    if catalog is None:
        try:
            catalog = load_catalog()
        except (OSError, ValueError) as error:
            report.add("CAT-1", CATALOG_PATH, f"Cannot load catalog: {error}")
            return
    runtime_edges = []
    for entry in files:
        name = entry["name"]
        children = entry["fm"].get("agents", [])
        if not isinstance(name, str):
            continue
        targets = [child for child in children if isinstance(child, str)] if isinstance(children, list) else []
        runtime_edges.extend((name, child) for child in targets)
        tools = entry["fm"].get("tools", [])
        tools = tools if isinstance(tools, list) else []
        if name == "Orchestrator":
            if "agent" not in tools or any(tool not in DISPATCHER_TOOLS for tool in tools):
                report.add("RST-4", entry["path"], "Dispatcher needs agent access and only classification tools")
        elif targets or any(isinstance(tool, str) and tool.split("/")[0] == "agent" for tool in tools):
            report.add("RST-4", entry["path"], "Only Orchestrator may delegate; nested agent access is forbidden")
        if name.endswith("Advisor") and (entry["fm"].get("tools") != [] or entry["fm"].get("agents") != []):
            report.add("RST-4", entry["path"], "Advisors must have explicit tools: [] and agents: []")

    expected_runtime = Counter(("Orchestrator", name) for name in registry if name != "Orchestrator")
    if Counter(runtime_edges) != expected_runtime:
        report.add("RST-4", registry.get("Orchestrator", README_PATH), "Dispatcher must directly allow every advisor and worker exactly once; no nested edges")

    if not isinstance(catalog, dict) or catalog.get("schema_version") != 1 or catalog.get("dispatcher") != "Orchestrator":
        report.add("CAT-1", CATALOG_PATH, "Expected schema_version 1 and dispatcher Orchestrator")
        return
    groups = catalog.get("domains")
    if not isinstance(groups, list):
        report.add("CAT-1", CATALOG_PATH, "domains must be a list")
        return
    adjacency = {"Orchestrator": []}
    declarations = {}
    route_targets = set()
    expected_routes = Counter()
    domain_names = set()
    for group in groups:
        if not isinstance(group, dict):
            report.add("CAT-1", CATALOG_PATH, "Each domain must be an object")
            continue
        advisor, parent = group.get("advisor"), group.get("parent")
        children, routes = group.get("children"), group.get("routes")
        domain = group.get("domain")
        if not isinstance(domain, str) or not domain or domain in domain_names:
            report.add("CAT-1", CATALOG_PATH, "Domain names must be unique non-empty strings")
        else:
            domain_names.add(domain)
        if not isinstance(advisor, str) or not advisor.endswith("Advisor") or advisor not in registry or advisor in declarations:
            report.add("CAT-1", CATALOG_PATH, f"Invalid or duplicate advisor: {advisor!r}")
            continue
        if not isinstance(parent, str) or parent not in registry:
            report.add("CAT-1", CATALOG_PATH, f"Unresolved owner for {advisor}: {parent!r}")
            continue
        declarations[advisor] = parent
        if not isinstance(children, list) or any(not isinstance(child, str) for child in children):
            report.add("CAT-1", CATALOG_PATH, f"{advisor} children must be a list of agent names")
            children = []
        adjacency[advisor] = children
        if parent == "Orchestrator":
            adjacency["Orchestrator"].append(advisor)
        for child in children:
            if child not in registry:
                report.add("CAT-1", CATALOG_PATH, f"Unresolved owned agent: {child}")
            if child.endswith("Advisor") or NAMING_EXCEPTIONS.get(child) == advisor:
                continue
            prefix = DOMAIN_PREFIXES.get(advisor)
            if not prefix or not re.fullmatch(prefix + r"[A-Z][A-Za-z0-9]*", child) or not child.endswith(WORKER_SUFFIXES):
                report.add("NAM-1", CATALOG_PATH, f"Worker {child!r} must use the {advisor} domain prefix and a documented role suffix")
        if not isinstance(routes, dict):
            report.add("CAT-1", CATALOG_PATH, f"{advisor} routes must be a label-to-worker object")
            continue
        for label, target in routes.items():
            if not isinstance(label, str) or not label or not isinstance(target, str) or target not in children or target.endswith("Advisor"):
                report.add("CAT-1", CATALOG_PATH, f"Invalid worker route in {advisor}: {label!r} -> {target!r}")
            else:
                route_targets.add(target)
                expected_routes[(label, target, advisor)] += 1

    advisors = {name for name in registry if name.endswith("Advisor")}
    workers = set(registry) - advisors - {"Orchestrator"}
    if set(declarations) != advisors:
        report.add("CAT-1", CATALOG_PATH, "Every advisor needs exactly one domain declaration")
    if route_targets != workers:
        report.add("CAT-1", CATALOG_PATH, f"Worker route coverage mismatch: missing {sorted(workers - route_targets)}, extra {sorted(route_targets - workers)}")
    edges = [(parent, child) for parent, children in adjacency.items() for child in children]

    owners = {}
    for parent, child in edges:
        owners.setdefault(child, []).append(parent)
    if set(adjacency["Orchestrator"]) != TIER1_ADVISORS:
        report.add("RST-7", CATALOG_PATH, "Ownership root must contain the four Tier-1 advisors")
    for name, path in registry.items():
        parents = owners.get(name, [])
        if name == "Orchestrator":
            if parents:
                report.add("RST-4", path, "Orchestrator must not have an ownership parent")
        elif len(parents) != 1:
            report.add("RST-4", path, f"Expected exactly one ownership parent, found {parents}")
    for name, parent in declarations.items():
        if owners.get(name) != [parent]:
            report.add("RST-7", CATALOG_PATH, f"Declared owner for {name} disagrees with ownership edges")
    for name in CODE_SUBADVISORS:
        if owners.get(name) != ["CodeDomainAdvisor"]:
            report.add("RST-7", registry.get(name, README_PATH), f"{name} must be owned by CodeDomainAdvisor")

    visiting = set()
    visited = set()

    def visit(name):
        if name in visiting:
            report.add("RST-5", registry.get(name, README_PATH), f"Ownership cycle reaches {name}")
            return
        if name in visited:
            return
        visiting.add(name)
        for child in adjacency.get(name, []):
            visit(child)
        visiting.remove(name)
        visited.add(name)

    for name in adjacency:
        visit(name)

    depths = {"Orchestrator": 0} if "Orchestrator" in registry else {}
    pending = list(depths)
    while pending:
        parent = pending.pop(0)
        for child in adjacency.get(parent, []):
            if child in registry and child not in depths:
                depths[child] = depths[parent] + 1
                pending.append(child)
    for name, depth in depths.items():
        expected = 0 if name == "Orchestrator" else 1 if name in TIER1_ADVISORS else 3 if any(parent in CODE_SUBADVISORS for parent in owners.get(name, [])) else 2
        if depth != expected:
            report.add("RST-7", registry[name], f"Expected Tier-{expected}, found Tier-{depth}")
    if set(depths) != set(registry):
        report.add("RST-7", CATALOG_PATH, f"Ownership has unreachable agents: {sorted(set(registry) - set(depths))}")

    if readme is None:
        readme = README_PATH.read_text(encoding="utf-8")
    index_names = Counter(re.findall(
        r"^\|\s*\*\*([A-Za-z]\w*)\*\*\s*\|",
        readme_section(readme, "Agent Index"), re.MULTILINE,
    ))
    if index_names != Counter(registry.keys()):
        report.add("DOC-1", README_PATH, "Agent Index must list every canonical agent exactly once, with no unknown entries")
    dispatcher = next((entry for entry in files if entry["name"] == "Orchestrator"), {})
    embedded_routes = Counter()
    for line in readme_section(dispatcher.get("text", ""), "Embedded Routing Index").splitlines():
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        if line.startswith("| ") and len(cells) == 3 and cells[0] != "Selection Cue":
            embedded_routes[cells] += 1
    if embedded_routes != expected_routes:
        report.add("DOC-1", registry.get("Orchestrator", README_PATH), "Embedded Routing Index must match catalog selection cues, workers, and advisors exactly once")
    diagram_edges = []
    for diagram in re.findall(r"```mermaid\s*\n(.*?)```", readme_section(readme, "Domain Organization"), re.DOTALL):
        diagram_edges.extend(
            ("Orchestrator" if parent == "O" else parent, child)
            for parent, child in re.findall(r"^\s*(\w+)\s*-->\s*(\w+)", diagram, re.MULTILINE)
        )
    missing = Counter(edges) - Counter(diagram_edges)
    extra = Counter(diagram_edges) - Counter(edges)
    if missing or extra:
        report.add("RST-6", README_PATH, f"Ownership diagram/catalog mismatch: missing {dict(missing)}, extra {dict(extra)}")
    documented_domains = Counter()
    for line in readme_section(readme, "Domain Map").splitlines():
        cells = [cell.strip().strip("`*") for cell in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0] != "Domain Prefix" and not set(cells[0]) <= {"-", ":"}:
            documented_domains.update((cells[1], child.strip().strip("`*")) for child in cells[2].split(","))
    expected_domains = Counter((advisor, child) for advisor, children in adjacency.items() if advisor != "Orchestrator" for child in children)
    if documented_domains != expected_domains:
        report.add("RST-6", README_PATH, "Domain Map ownership does not match the catalog")


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
    checks = ("DEF-1", "DEF-2", "DEF-3", "DEF-4", "RST-1", "RST-2", "RST-3", "RST-4", "RST-5", "RST-6", "RST-7", "CAT-1", "TOOL-1", "NAM-1", "DOC-1")
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
            "RST-1": "Invocation targets resolve",
            "RST-2": "Every agent reachable",
            "RST-3": "README routing references resolve",
            "RST-4": "Single-dispatcher boundaries and unique ownership",
            "RST-5": "No ownership cycles",
            "RST-6": "Ownership documentation matches catalog",
            "RST-7": "Documented ownership tiers and reachability",
            "CAT-1": "Catalog structure and worker route coverage",
            "TOOL-1": "Role-specific required and allowed tools",
            "NAM-1": "Domain naming convention and explicit exceptions",
            "DOC-1": "Complete README index and embedded routing parity",
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
    advisors = [entry for entry in files if isinstance(entry["name"], str) and entry["name"].endswith("Advisor")]
    lines.append(f"- Dispatchers: {int('Orchestrator' in registry)}")
    lines.append(f"- Tool-free advisors: {len(advisors)}")
    lines.append(f"- Workers: {len(files) - len(advisors) - int('Orchestrator' in registry)}")
    lines.append(f"- README routing references: {len(readme_refs)}")
    lines.append("- Static definition checks only; direct invocation and advisory decisions require runtime smoke tests.")
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
        check_tool_profiles(files, report)
        check_reachability(files, registry, stems, router_agents, orchestrator_agents, readme_refs, report)
        check_topology(files, registry, report)
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
