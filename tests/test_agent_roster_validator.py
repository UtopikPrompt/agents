import ast
import copy
import re
import runpy
import unittest
from pathlib import Path
from unittest.mock import patch


VALIDATOR = runpy.run_path(
    str(Path(__file__).resolve().parent.parent / "tools" / "agent-roster-validator.py")
)


class RosterValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline, cls.registry, cls.stems, _ = VALIDATOR["load_agents"]()
        cls.readme_text = VALIDATOR["README_PATH"].read_text(encoding="utf-8")
        cls.catalog_data = VALIDATOR["load_catalog"]()

    def setUp(self):
        self.files = copy.deepcopy(self.baseline)
        self.readme = self.readme_text
        self.catalog = copy.deepcopy(self.catalog_data)

    def agent(self, name):
        return next(entry for entry in self.files if entry["name"] == name)

    def domain(self, advisor):
        return next(group for group in self.catalog["domains"] if group["advisor"] == advisor)

    def validate(self):
        report = VALIDATOR["Report"]()
        with patch.object(Path, "read_text", return_value=self.readme):
            routers, root, refs = VALIDATOR["load_readme_refs"](self.files, self.registry)
        VALIDATOR["check_definition"](self.files, report)
        VALIDATOR["check_tool_profiles"](self.files, report)
        VALIDATOR["check_reachability"](
            self.files, self.registry, self.stems, routers, root, refs, report
        )
        VALIDATOR["check_topology"](self.files, self.registry, report, self.readme, self.catalog)
        return report

    def assert_check(self, check):
        report = self.validate()
        self.assertIn(check, report.check_counts, report.findings)

    def test_split_workers_are_read_only_and_keep_distinct_ownership(self):
        for name in ("CodeProductModernizationExpert", "CodeArchitectureExpert"):
            with self.subTest(agent=name):
                worker = self.agent(name)
                self.assertEqual(worker["fm"]["tools"], ["read", "search"])
                self.assertEqual(worker["fm"]["agents"], [])
                self.assertNotIn("model", worker["fm"])
                self.assertEqual(
                    VALIDATOR["tool_profile"](name),
                    ({"read", "search"}, {"read", "search"}),
                )
        product = self.agent("CodeProductModernizationExpert")["text"]
        architecture = self.agent("CodeArchitectureExpert")["text"]
        self.assertIn(
            "feature/opportunity assessment and proposed target-product requirements report",
            " ".join(product.split()),
        )
        self.assertIn(
            "technical architecture documentation and contracts",
            " ".join(architecture.split()),
        )
        self.assertIn("BusinessKnowledgeExpert owns professional business extraction", product)
        self.assertIn("CodeRebuildEngineer integrates migration/readiness/roadmap", architecture)
        rebuild = self.agent("CodeRebuildEngineer")["text"]
        self.assertNotIn("## Feature and Opportunity Assessment", rebuild)
        self.assertNotIn("## Enterprise Architecture Recommendations", rebuild)
        dispatcher = self.agent("Orchestrator")["text"]
        for name in ("CodeProductModernizationExpert", "CodeArchitectureExpert"):
            self.assertEqual(self.agent("Orchestrator")["fm"]["agents"].count(name), 1)
            self.assertIn(name, self.domain("CodeDomainAdvisor")["children"])
        self.assertIn("only orchestrator invokes workers", dispatcher.lower())
        self.assertIn("For rebuild assessments, order discovery, modernization", dispatcher)
        self.assertIn("Target product specification", dispatcher)

    def test_split_preserves_portability_gates_and_limits_dispatcher_size(self):
        product = " ".join(self.agent("CodeProductModernizationExpert")["text"].split())
        architecture = " ".join(self.agent("CodeArchitectureExpert")["text"].split())
        rebuild = " ".join(self.agent("CodeRebuildEngineer")["text"].split())
        for owner, definition in (("product", product), ("architecture", architecture)):
            for clause in ("PASS/FAIL/UNKNOWN", "professional-report-v1", "Orchestrator", "PARTIAL"):
                with self.subTest(owner=owner, clause=clause):
                    self.assertIn(clause, definition)
        self.assertIn("## Transformation Roadmap", rebuild)
        self.assertIn("Each work package has an ID", rebuild)
        self.assertIn("Request missing design through Orchestrator", rebuild)
        dispatcher = self.agent("Orchestrator")["text"]
        for name in (
            "BusinessKnowledgeExpert", "CodeProductModernizationExpert",
            "CodeArchitectureExpert", "CodeRebuildEngineer",
        ):
            self.assertIn(name, dispatcher.split("## Rebuild Report Coordination\n", 1)[1])
        self.assertLess(len(dispatcher), 25000)
        self.assertLess(len(self.agent("CodeRebuildEngineer")["text"]), 20000)

    def test_audit_framework_modes_do_not_require_scaffolding_for_maintenance(self):
        for name in (
            "CodeNextJsSpecialist", "CodeReactViteSpecialist", "CodeExpressSpecialist",
            "CodeSpringBootSpecialist", "CodeFastApiSpecialist",
        ):
            with self.subTest(agent=name):
                definition = " ".join(self.agent(name)["text"].split()).lower()
                self.assertIn("review/diagnosis is read-only", definition)
                self.assertIn("initialization is explicitly requested", definition)
                self.assertIn("maintenance", definition)

    def test_audit_python_examples_parse_and_use_consistent_apis(self):
        for name in ("CodeFastApiSpecialist", "CodeDatabaseORMGenerator"):
            examples = re.findall(r"```python\n(.*?)```", self.agent(name)["text"], re.DOTALL)
            self.assertTrue(examples)
            for index, example in enumerate(examples):
                with self.subTest(agent=name, example=index):
                    ast.parse(example)
        fastapi = self.agent("CodeFastApiSpecialist")["text"]
        self.assertIn("app.add_middleware(", fastapi)
        self.assertIn("allow_origins=", fastapi)
        self.assertNotIn("app.add_cors_middleware", fastapi)
        self.assertNotIn("decode_token(token)", fastapi)
        database = self.agent("CodeDatabaseORMGenerator")["text"]
        self.assertIn("engine = create_async_engine(", database)
        self.assertIn("SessionLocal = async_sessionmaker(", database)
        self.assertNotIn("class_=Base", database)
        self.assertIn("from datetime import datetime", database)

    def test_audit_typescript_examples_define_procedures_and_native_button_props(self):
        trpc = self.agent("CodeGraphQLTRPCAgent")["text"]
        self.assertIn("const trpc = initTRPC.create()", trpc)
        self.assertIn("trpc.procedure.input(", trpc)
        self.assertNotIn("routerProcedure", trpc)
        button = self.agent("CodeDesignSystemSpecialist")["text"]
        self.assertIn("extends ButtonHTMLAttributes<HTMLButtonElement>", button)
        self.assertIn('"#FFFFFF" : "#1F2937"', button)

    def test_audit_monorepo_and_github_preserve_operation_boundaries(self):
        monorepo = self.agent("InfraMonorepoManager")["text"]
        self.assertIn("Publication: \"not performed by this worker\"", monorepo)
        self.assertNotIn("scriptPostVersion", monorepo)
        self.assertNotIn("lerna publish", monorepo)
        github = " ".join(self.agent("GovGithubAgent")["text"].split())
        for clause in (
            "**Triage:**", "**Proposal:**", "**Authorized mutation:**",
            "Issue creation does not authorize project/board creation",
            "never create one merely because it seems a better home",
            "verify host, owner, repository and owner type",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, github)
        self.assertNotIn("The agent MUST execute all actions", github)

    def test_audit_git_workflows_are_embedded_and_tag_publication_is_separate(self):
        git = " ".join(self.agent("GovGitWorkflowAgent")["text"].split())
        self.assertIn("Local skills are optional enrichment", git)
        self.assertIn("create pending review, add scoped line comments, then submit once", git)
        self.assertIn("Tag creation does not authorize tag publication", git)
        self.assertNotIn("load the matching available skill", git)
        self.assertNotIn("load the available create-pull-request skill", git)

    def test_audit_routing_uses_mode_and_primary_artifact(self):
        dispatcher = self.agent("Orchestrator")["text"]
        section = dispatcher.split("## Boundary Tie-Breakers\n", 1)[1].split("\n## ", 1)[0]
        for clause in (
            "Diagnosis-only framework traceback vs authorized repair",
            "InfraIaCGenerator for IaC/state",
            "InfraKubernetesEngineer for manifests/operators/pod troubleshooting",
            "InfraMonorepoManager for package graph/version coordination",
            "GovArchitectureRecordsExpert for substantive ADR/RFC proposals",
            "version coordination alone does not authorize either",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, section)
        diagnostician = self.agent("CodeFrameworkDiagnostician")["text"]
        self.assertNotIn("engine/pyproject.toml", diagnostician)
        self.assertNotIn("apps/dashboard/package.json", diagnostician)
        self.assertNotIn("Lead Project Supervisor", diagnostician)
        build = self.agent("MultiLanguageBuilder")["text"]
        self.assertIn("no fixed language order is assumed", build)
        self.assertIn("Scoped repository-local toolchain", build)

    def test_audit_export_manifest_and_business_lineage_match_responsibilities(self):
        writer = self.agent("GovDocumentationSuiteGenerator")["text"]
        for field in ("ArtifactManifest:", "BusinessCatalogues:", "KnowledgeSnapshots:", "RebuildRecords:", "ApprovalStatus:"):
            with self.subTest(field=field):
                self.assertIn(field, writer)
        rebuild = self.agent("CodeRebuildEngineer")["text"]
        self.assertIn("Preserve supplied business IDs", rebuild)
        self.assertNotIn("Reconstruct the data model and the domain rules", rebuild)
        self.assertIn("GovArchitectureRecordsExpert when requested", self.agent("Orchestrator")["text"])

    def test_audit_reporting_is_sanitized_provider_neutral_and_incident_specific(self):
        container = self.agent("InfraDevContainerSpecialist")["text"]
        self.assertIn("variable names and redacted or explicitly nonsecret values only", container)
        self.assertNotIn("Environment: [environment variables]", container)
        self.assertIn("actual configured provider", self.agent("InfraObservabilitySpecialist")["text"])
        self.assertIn("actual configured provider", self.agent("InfraCloudDeploymentAgent")["text"])
        self.assertIn("verified installed profiler", self.agent("InfraPerformanceProfiler")["text"])
        incident = self.agent("InfraCIDiagnostics")["text"]
        self.assertIn("**Root Cause**", incident)
        self.assertNotIn("**Filed In**", incident)

    def test_audit_utilities_and_mcp_require_real_evidence_not_hidden_capabilities(self):
        brainstorm = " ".join(self.agent("Brainstorm")["text"].split())
        self.assertIn("at most three meaningful options", brainstorm)
        self.assertIn("not invented implementation dates", brainstorm)
        self.assertNotIn("Extra variations drain local VRAM", brainstorm)
        self.assertIn("evidence that could change it", brainstorm)
        optimizer = " ".join(self.agent("AgentOptimizer")["text"].split())
        self.assertIn("Do not assume the dispatcher has session-store tools", optimizer)
        mcp = self.agent("InfraMCPServerGenerator")["text"]
        self.assertIn("verify APIs against local SDK/source evidence", mcp)
        self.assertIn("global/user client settings", mcp)
        self.assertNotIn('"mcpVersion": "1.0.0"', mcp)

    def test_business_knowledge_domain_definitions_have_restricted_roles(self):
        advisor = self.agent("BusinessKnowledgeAdvisor")
        worker = self.agent("BusinessKnowledgeExpert")
        self.assertEqual(advisor["fm"]["tools"], [])
        self.assertEqual(advisor["fm"]["agents"], [])
        self.assertEqual(worker["fm"]["tools"], ["read", "search"])
        self.assertEqual(worker["fm"]["agents"], [])
        self.assertNotIn("model", advisor["fm"])
        self.assertNotIn("model", worker["fm"])
        self.assertEqual(
            VALIDATOR["tool_profile"](worker["name"]),
            ({"read", "search"}, {"read", "search"}),
        )

    def test_business_knowledge_professional_quality_gate_is_explicit(self):
        definition = " ".join(self.agent("BusinessKnowledgeExpert")["text"].split())
        for clause in (
            "## Professional Quality Gate and Audit Mode",
            "counts by catalogue",
            "declared scope and coverage denominator",
            "COMPLETE means every in-scope capability/layer is analyzed or explicitly marked",
            "A documented evidence gap can coexist with a complete coverage inventory",
            "Keep evidence confidence, runtime/test execution, stakeholder approval and coverage completeness as separate dimensions",
            "A tautology such as correct output or successful save is not an oracle",
            "No polished formatting or inventory count can substitute for semantic completeness",
            "explicit competent human validation before operational reliance",
            "No local skills, workflow files or client-profile discovery",
            "single package-level plan/resume item in README",
            "Do not append a separate \"Next action\" to each generated report",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, definition)

    def test_business_knowledge_worker_rejects_writes_execution_and_delegation(self):
        for tool in ("edit", "execute", "agent", "github/*"):
            with self.subTest(tool=tool):
                worker = copy.deepcopy(self.agent("BusinessKnowledgeExpert"))
                worker["fm"]["tools"].append(tool)
                report = VALIDATOR["Report"]()
                VALIDATOR["check_tool_profiles"]([worker], report)
                self.assertTrue(report.findings)
                self.assertEqual(report.findings[0]["check"], "TOOL-1")

    def test_business_knowledge_domain_has_unique_root_ownership_and_route(self):
        domain = self.domain("BusinessKnowledgeAdvisor")
        self.assertEqual(domain["parent"], "Orchestrator")
        self.assertEqual(domain["children"], ["BusinessKnowledgeExpert"])
        route = (
            "business needs/requirements and business logic, process analysis, "
            "enterprise knowledge mapping, evidence-linked traceability/impact queries, "
            "snapshot refresh or knowledge quality audit"
        )
        self.assertEqual(domain["routes"][route], "BusinessKnowledgeExpert")
        allowlist = self.agent("Orchestrator")["fm"]["agents"]
        self.assertEqual(allowlist.count("BusinessKnowledgeAdvisor"), 1)
        self.assertEqual(allowlist.count("BusinessKnowledgeExpert"), 1)
        self.assertIn("BusinessKnowledgeAdvisor", VALIDATOR["TIER1_ADVISORS"])
        self.assertEqual(VALIDATOR["DOMAIN_PREFIXES"]["BusinessKnowledgeAdvisor"], "Business")

    def test_context_and_guardrail_workers_are_read_only_and_routed(self):
        expected = {
            "pre-design schema/API/config/environment audit": "CodeContextSchemaAuditor",
            "evidence-based review of a proposed or changed artifact": "CodeQualityGuardrailReviewer",
        }
        domain = self.domain("CodeDomainAdvisor")
        allowlist = self.agent("Orchestrator")["fm"]["agents"]
        for cue, name in expected.items():
            with self.subTest(agent=name):
                worker = self.agent(name)
                self.assertEqual(worker["fm"]["tools"], ["read", "search"])
                self.assertEqual(worker["fm"]["agents"], [])
                self.assertEqual(VALIDATOR["tool_profile"](name), ({"read", "search"}, {"read", "search"}))
                self.assertEqual(allowlist.count(name), 1)
                self.assertEqual(domain["routes"][cue], name)
                self.assertIn(name, self.agent("CodeDomainAdvisor")["text"])
        scenarios = VALIDATOR["yaml"].safe_load(
            (VALIDATOR["PROMPTS_DIR"] / "tests" / "roster-scenarios.yaml").read_text(encoding="utf-8")
        )
        for scenario_id, worker in (
            ("context-schema-conflict-audit", "CodeContextSchemaAuditor"),
            ("guardrail-unsupported-api-review", "CodeQualityGuardrailReviewer"),
        ):
            scenario = next(item for item in scenarios if item["id"] == scenario_id)
            self.assertEqual(scenario["split"], "held-out")
            self.assertEqual(scenario["expected_worker"], worker)

    def test_business_knowledge_procedures_are_not_owned_by_rebuild_worker(self):
        rebuild = self.agent("CodeRebuildEngineer")["text"]
        self.assertIn("## Business Knowledge Ownership and Handoff", rebuild)
        self.assertIn("BusinessKnowledgeExpert", rebuild)
        self.assertNotIn("## Portable Enterprise Knowledge Graph Contract", rebuild)
        self.assertNotIn("## Enterprise Knowledge Reconstruction", rebuild)
        writer = " ".join(self.agent("GovDocumentationSuiteGenerator")["text"].split())
        self.assertIn("Preserve its quality-review artifact", writer)
        scenario_path = VALIDATOR["PROMPTS_DIR"] / "tests" / "roster-scenarios.yaml"
        scenarios = VALIDATOR["yaml"].safe_load(scenario_path.read_text(encoding="utf-8"))
        scenario = next(item for item in scenarios if item["id"] == "business-knowledge-professional-audit")
        self.assertEqual(scenario["expected_worker"], "BusinessKnowledgeExpert")
        self.assertIn("competent human validation", scenario["required_behavior"])

    def test_rebuild_consumes_business_findings_without_claiming_extraction(self):
        definition = " ".join(self.agent("CodeRebuildEngineer")["text"].split())
        self.assertNotIn("extract the business need or requirement", definition)
        self.assertNotIn("## Business Need Extraction", definition)
        for clause in (
            "BusinessKnowledgeExpert owns professional business needs",
            "## Input Review and Traceability",
            "Do not independently recreate business catalogues, product strategy or architecture",
            "CodeProductModernizationExpert owns feature assessment",
            "CodeArchitectureExpert owns technical options",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, definition)

    def test_architecture_proposals_allow_pending_authority_but_gate_acceptance(self):
        definition = " ".join(self.agent("GovArchitectureRecordsExpert")["text"].split())
        for clause in (
            "record unknown authority as TBD and decisions as proposed/pending",
            "Missing approval does not block authorized proposal drafting",
            "Do not reinterpret an existing accepted record as a new draft",
            "Require explicit approval before accepting a decision",
            "changing accepted decision content/status",
            "An accepted implementation handoff remains blocked",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, definition)
        self.assertNotIn("If acceptance status or authority is unclear, return NEEDS_INPUT", definition)
        scenario_path = VALIDATOR["PROMPTS_DIR"] / "tests" / "roster-scenarios.yaml"
        scenarios = VALIDATOR["yaml"].safe_load(scenario_path.read_text(encoding="utf-8"))
        scenario = next(item for item in scenarios if item["id"] == "architecture-proposal-pending-authority")
        self.assertEqual(scenario["expected_worker"], "GovArchitectureRecordsExpert")
        self.assertIn("accepted", scenario["required_behavior"])

    def test_business_knowledge_prefix_migration_is_complete(self):
        root = VALIDATOR["PROMPTS_DIR"]
        for name in ("BusinessKnowledgeAdvisor", "BusinessKnowledgeExpert"):
            with self.subTest(agent=name):
                self.assertEqual(self.agent(name)["stem"], name)
                self.assertEqual(self.agent(name)["fm"]["name"], name)
                self.assertTrue((root / f"{name}.agent.md").is_file())
                self.assertFalse((root / f"Gov{name}.agent.md").exists())
        self.assertIn(
            "| BusinessKnowledgeAdvisor | Business | BusinessKnowledgeExpert |",
            self.readme,
        )
        self.assertIn("Gov, or Business prefix", (root / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertEqual(VALIDATOR["DOMAIN_PREFIXES"]["DocsGovernanceAdvisor"], "Gov")
        with patch.dict(VALIDATOR["DOMAIN_PREFIXES"], {"BusinessKnowledgeAdvisor": "Gov"}):
            self.assert_check("NAM-1")

    def test_current_roster_passes(self):
        self.assertEqual(self.validate().findings, [])

    def test_only_orchestrator_is_user_invocable(self):
        user_invocable = {
            entry["name"]
            for entry in self.files
            if entry["fm"]["user-invocable"] is True
        }
        self.assertEqual(user_invocable, {"Orchestrator", "GovWebResearchAgent"})

    def test_comfyui_worker_is_not_user_invocable_and_routed(self):
        worker = self.agent("CodeComfyUICustomNodeSpecialist")
        self.assertIs(worker["fm"]["user-invocable"], False)
        self.assertEqual(worker["fm"]["tools"], ["read", "search", "edit", "execute"])
        self.assertEqual(worker["fm"]["agents"], [])
        domain = self.domain("CodeDomainAdvisor")
        self.assertIn(worker["name"], domain["children"])
        self.assertEqual(
            domain["routes"]["ComfyUI custom node implementation, review, debugging or tests"],
            worker["name"],
        )
        self.assertEqual(self.agent("Orchestrator")["fm"]["agents"].count(worker["name"]), 1)

    def test_comfyui_worker_embeds_version_and_execution_safeguards(self):
        definition = self.agent("CodeComfyUICustomNodeSpecialist")["text"]
        for clause in (
            "classic V1 API or the newer V3 schema/extension API",
            "NODE_CLASS_MAPPINGS",
            "BHWC",
            "MASK tensors BHW",
            "do not assume every tensor is an image",
            "Do not hardcode CUDA",
            "WEB_DIRECTORY",
            "CPU-capable, offline, and free of model downloads",
            "Never report skipped GPU/UI integration as passing",
            "do not search client profiles or require local skills",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause.lower(), definition.lower())

    def test_mermaid_workers_embed_consistent_vertical_safety_contract(self):
        owners = {
            "GovArchitectureRecordsExpert", "GovDocumentationSuiteGenerator",
            "GovGithubAgent", "InfraCIDiagnostics", "InfraMCPServerGenerator",
            "InfraMonorepoManager", "InfraPerformanceProfiler",
            "InfraReleaseManager", "InfraTestInfrastructureGenerator",
        }
        sections = []
        for entry in self.baseline:
            with self.subTest(agent=entry["name"]):
                self.assertNotIn("Prefer Mermaid diagrams over bulleted lists", entry["text"])
                if entry["name"] not in owners:
                    continue
                self.assertEqual(entry["text"].count("## Mermaid Diagrams\n"), 1)
                section = entry["text"].split("## Mermaid Diagrams\n", 1)[1].split("\n## ", 1)[0]
                sections.append(section.strip())
                for clause in (
                    "Use diagrams only when they clarify relationships",
                    "Use fenced `mermaid` blocks",
                    "Default to vertical `flowchart TD`",
                    "use horizontal flow only when explicitly requested",
                    "supported by the target renderer",
                    "simple ASCII node IDs",
                    "never use lowercase `end` as an ID",
                    "Quote all node labels",
                    "Define nodes separately from edges, one statement per line",
                    "avoid HTML, Markdown formatting, literal quotes inside labels",
                    "Avoid custom styling, icons, and initialization directives",
                    "review IDs, label quotes, balanced delimiters, and edge references",
                    "within your tool permissions",
                    "Markdown lint is not Mermaid validation",
                    'report "syntax reviewed, rendering unverified"',
                    "return the exact validation needed if blocked",
                    "Never claim a rendering check ran when it did not",
                ):
                    self.assertIn(clause, section)
        self.assertEqual(len(sections), len(owners))
        self.assertEqual(len(set(sections)), 1)

    def test_mermaid_dispatch_and_documentation_require_vertical_flow(self):
        payload = self.agent("Orchestrator")["text"].split("## Worker Payload\n", 1)[1].split("\n## ", 1)[0]
        self.assertIn("vertical `flowchart TD` by default", payload)
        self.assertIn('require "syntax reviewed, rendering unverified"', payload)
        self.assertIn("do not expand tool permissions", payload)
        self.assertIn("## Mermaid Output", self.readme)
        self.assertIn("Default to vertical `flowchart TD`", self.readme)
        self.assertIn("Markdown lint is not\nMermaid validation", self.readme)

    def test_dispatcher_routes_around_its_own_tool_limits(self):
        dispatcher = self.agent("Orchestrator")["text"]
        for clause in (
            "invoke the indexed worker instead of reporting the dispatcher's tool limit",
            "Do not ask the user to name an agent when the index identifies",
            "Report a blocker only if invocation fails or the worker's session",
            "This restriction applies to the Orchestrator's own actions, not dispatch",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, dispatcher)

    def test_dispatcher_requires_approval_before_discarding_existing_edits(self):
        dispatcher = self.agent("Orchestrator")["text"]
        payload = dispatcher.split("## Worker Payload\n", 1)[1].split("\n## ", 1)[0]
        for clause in (
            "Preserve existing file edits",
            "restoring, reverting, resetting, overwriting",
            "ask the user for explicit approval naming the affected files",
            "General task authorization is not approval",
            "preserve the edits and return NEEDS_INPUT",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, payload)

    def test_dispatcher_requires_root_cause_and_implementation_offer(self):
        dispatcher = self.agent("Orchestrator")["text"]
        payload = dispatcher.split("## Worker Payload\n", 1)[1].split("\n## ", 1)[0]
        for clause in (
            "evidence-based\n  root cause",
            "confirmed facts from hypotheses",
            "stating what remains\n  unknown",
            "simple one-line recommended fix",
            "concise, ready-to-approve proposal",
            "specific\n  change, expected effect, validation",
            "authorization or evidence still\n  needed",
            "Do not present a proposed solution or implementation offer as\n  completed work",
            "do not imply that approval has been granted",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, payload)

    def test_edit_and_command_workers_require_restoration_approval(self):
        for entry in self.baseline:
            if not {"edit", "execute"}.intersection(entry["fm"].get("tools", [])):
                continue
            with self.subTest(agent=entry["name"]):
                self.assertEqual(entry["text"].count("## Existing Edit Protection\n"), 1)
                section = entry["text"].split("## Existing Edit Protection\n", 1)[1].split("\n## ", 1)[0]
                for clause in (
                    "including changes discovered during the task",
                    "restoring, reverting, resetting, overwriting",
                    "ask the user for explicit approval naming the affected files and proposed restoration",
                    "General task authorization is not approval to discard edits",
                    "Without approval, preserve the edits and return NEEDS_INPUT",
                    "ask the user directly when running as the main agent",
                    "This rule grants no additional permissions",
                ):
                    self.assertIn(clause, section)

    def test_existing_edit_protection_is_documented(self):
        self.assertIn("## Existing Edit Protection", self.readme)
        self.assertIn("General task authorization is not approval to discard edits", self.readme)

    def test_current_names_and_documentation_follow_policy(self):
        findings = [finding for finding in self.validate().findings if finding["check"] in {"NAM-1", "DOC-1"}]
        self.assertEqual(findings, [])

    def test_shareable_report_paths_are_relative(self):
        report = VALIDATOR["Report"]()
        root = VALIDATOR["PROMPTS_DIR"]
        report.add("DEF-1", root / "Example.agent.md", f"Invalid definition under {root}")
        report.add("DEF-1", root.parent / "external" / "Outside.agent.md", "Invalid external definition")
        rendered = VALIDATOR["build_report"](report, self.files, self.registry, [])
        self.assertIn("Workspace: repository root (paths are relative)", rendered)
        self.assertIn("`Example.agent.md`", rendered)
        self.assertIn("`Outside.agent.md`", rendered)
        self.assertNotIn(str(root), rendered)
        self.assertNotIn(root.as_posix(), rendered)
        self.assertNotIn(str(root.parent / "external"), rendered)

    def test_shareable_artifacts_exclude_identity_and_location_details(self):
        root = VALIDATOR["PROMPTS_DIR"]
        artifacts = list(root.glob("*.md"))
        artifacts.extend((root / ".agents" / "skills").rglob("SKILL.md"))
        artifacts.append(root / "tests" / "roster-scenarios.yaml")
        forbidden_patterns = (
            r"(?i)\b[A-Z]:[\\/](?:Users|Documents and Settings)[\\/][^\\/\s]+",
            r"/(?:Users|home)/[^/\s]+/",
            r"(?i)\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b",
            r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
            r"https?://(?:www\.)?github\.com/[^/\s)]+/[^/\s)]+",
            r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b",
        )
        for artifact in artifacts:
            text = artifact.read_text(encoding="utf-8")
            with self.subTest(artifact=artifact.relative_to(root).as_posix()):
                for pattern in forbidden_patterns:
                    self.assertNotRegex(text, pattern)

    def test_architecture_records_preserve_human_authorization(self):
        definition = self.agent("GovArchitectureRecordsExpert")["text"]
        self.assertIn("Only the user or an explicitly documented human authority", definition)
        self.assertIn("Keep unapproved proposals in their proposal state", definition)
        self.assertIn("target repository's existing paths", definition)
        self.assertIn("return NEEDS_INPUT", definition)
        self.assertNotIn("Auto-approve", definition)
        self.assertNotRegex(definition, r"docs/[a-z_]+_plan\.md")
        self.assertNotIn("apps/dashboard/", definition)
        self.assertEqual(definition.count("## Efficiency"), 1)

    def test_release_stages_preserve_scoped_authorization(self):
        definition = self.agent("InfraReleaseManager")["text"]
        self.assertIn("explicit stage-specific authorization", definition)
        self.assertIn("Orchestrator for GovGitWorkflowAgent", definition)
        self.assertIn("never perform Git mutations yourself", definition)
        self.assertIn("Deployment requires separate authorization", definition)
        self.assertIn("Preparing a release creates no commit, tag, push, publication, or deployment", definition)
        self.assertNotIn("**Git Commit**: Commit changes", definition)

    def test_identity_workflow_requires_layer_isolation_without_extra_tools(self):
        for name in ("InfraCIDiagnostics", "InfraSecurityAuthAgent"):
            with self.subTest(agent=name):
                definition = self.agent(name)["text"]
                self.assertIn("## Identity Failure Isolation", definition)
                self.assertIn("application authorization", definition)
                self.assertIn("Secret delivery", definition)
        security = self.agent("InfraSecurityAuthAgent")
        self.assertNotIn("github/*", security["fm"]["tools"])
        self.assertIn("No automatic permission expansion", security["text"])

    def test_release_workflow_requires_exact_artifact_and_storage_boundaries(self):
        for name in ("InfraReleaseManager", "InfraKubernetesEngineer", "InfraCloudDeploymentAgent", "InfraIaCGenerator"):
            with self.subTest(agent=name):
                self.assertIn("## Release Contract Preflight", self.agent(name)["text"])
        kubernetes = self.agent("InfraKubernetesEngineer")["text"]
        for clause in ("exact reviewed artifact", "Namespace/PV/PVC", "without separate authorization", "bounded waits", "ready/failed/blocked/not-run"):
            self.assertIn(clause, kubernetes)

    def test_profiler_workflow_requires_runtime_and_api_evidence(self):
        definition = self.agent("InfraPerformanceProfiler")["text"]
        self.assertIn("Verify OS", definition)
        self.assertIn("installed profiler version, supported API", definition)
        self.assertIn("Do not assume Windows support", definition)
        self.assertNotIn("memray.MemoryProfiler", definition)
        self.assertNotIn("tachyon.Profile()", definition)

    def test_remote_workflows_are_embedded_in_owning_agents(self):
        owners = {
            "InfraLLMInferenceSpecialist": ("Controlled Engine Evaluation",),
            "InfraCIDiagnostics": ("Identity Failure Isolation",),
            "InfraSecurityAuthAgent": ("Identity Failure Isolation",),
            "InfraReleaseManager": ("Release Contract Preflight",),
            "InfraKubernetesEngineer": ("Release Contract Preflight",),
            "InfraCloudDeploymentAgent": ("Release Contract Preflight",),
            "InfraIaCGenerator": ("AWS Platform Safety", "Release Contract Preflight"),
            "InfraDevContainerSpecialist": ("Secure Development Bootstrap", "Container Display Operations"),
            "CodeGeneralist": ("Go Contract Validation", "Container Display Operations"),
            "MultiLanguageBuilder": ("Go Contract Validation", "Secure Development Bootstrap"),
            "GovArchitectureRecordsExpert": ("Specification To Code Handoff",),
            "GovDocumentationSuiteGenerator": ("Specification To Code Handoff",),
        }
        for name, headings in owners.items():
            for heading in headings:
                with self.subTest(agent=name, workflow=heading):
                    section = self.agent(name)["text"].split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]
                    steps = VALIDATOR["re"].findall(r"(?m)^\d+\. ", section)
                    self.assertGreaterEqual(len(steps), 6)

    def test_remote_agents_do_not_require_external_workflow_discovery(self):
        self.assertIn("Required workflows must be embedded in their owning agent definitions", self.readme)
        for entry in self.baseline:
            with self.subTest(agent=entry["name"]):
                self.assertNotRegex(entry["text"], r"(?i)(?:skill discovery|runtime discovery|\.agents/skills/)")
                self.assertNotRegex(entry["text"], r"\b(?:load|use|Use|Load) `[a-z]+(?:-[a-z]+)+`")

    def test_routing_scenarios_preserve_framework_and_worker_boundaries(self):
        dispatcher = self.agent("Orchestrator")["text"]
        frontend = self.agent("CodeFrontendAdvisor")["text"]
        self.assertIn("TypeScript alone is not evidence of React/Vite", dispatcher)
        self.assertIn("Angular, .NET, Go", dispatcher)
        self.assertIn("VS Code extension implementation", dispatcher)
        self.assertIn("Existing Angular/Vue application implementation", frontend)
        self.assertIn("-> NO_MATCH, not React scaffolding", frontend)
        self.assertNotIn("React or TypeScript SPA", dispatcher)

    def test_routing_scenarios_have_known_workers_and_held_out_cases(self):
        scenario_path = VALIDATOR["PROMPTS_DIR"] / "tests" / "roster-scenarios.yaml"
        scenarios = VALIDATOR["yaml"].safe_load(scenario_path.read_text(encoding="utf-8"))
        self.assertEqual(len(scenarios), 45)
        self.assertEqual(len({scenario["id"] for scenario in scenarios}), len(scenarios))
        self.assertEqual({scenario["split"] for scenario in scenarios}, {"calibration", "held-out"})
        self.assertEqual(sum(scenario["split"] == "held-out" for scenario in scenarios), 27)
        rebuild_scenario = next(scenario for scenario in scenarios if scenario["id"] == "rebuild-spec")
        self.assertEqual(rebuild_scenario["expected_worker"], "CodeRebuildEngineer")
        for scenario in scenarios:
            with self.subTest(scenario=scenario["id"]):
                self.assertGreater(len(scenario["prompt"]), 15)
                self.assertGreater(len(scenario["required_behavior"]), 15)
                target = scenario["expected_worker"]
                if target == "DIRECT":
                    continue
                self.assertIn(target, self.registry)
                self.assertFalse(target.endswith("Advisor"))
                self.assertNotEqual(target, "Orchestrator")

    def test_implementation_workers_require_regression_guided_code_retention(self):
        workers = [entry for entry in self.files if "## Required Code Validation" in entry["text"]]
        self.assertEqual(len(workers), 25)
        required_clauses = (
            "legacy code and backward-compatibility shims",
            "Before intentionally retaining legacy code or backward/retro-compatible behavior",
            "ask the user for explicit confirmation",
            "Until the user confirms, stop the affected change and return NEEDS_INPUT",
            "Repository docs, tests, inferred compatibility, and general task authorization are not approval",
            "Only an explicit direction in the current request waives this question",
            "unless an explicit supported requirement needs them",
            "Keep cleanup within the authorized scope",
            "focused regression tests for the current supported behavior",
            "justify retaining or removing code",
            "Add missing coverage before deciding",
            "missing coverage is not evidence that code is unused",
            "Do not weaken tests to justify removal",
            "or preserve obsolete behavior merely because an old test asserts it",
            "stop the affected change and return NEEDS_INPUT",
            "a focused question for Orchestrator to ask the user",
            "Do not guess or delete unrelated legacy code",
        )
        for worker in workers:
            with self.subTest(agent=worker["name"]):
                self.assertEqual(worker["text"].count("## Code Retention Policy"), 1)
                policy = worker["text"].split("## Code Retention Policy\n", 1)[1].split("\n## ", 1)[0]
                for clause in required_clauses:
                    self.assertIn(clause, policy)

    def test_orchestrator_requires_retention_evidence_and_user_clarification(self):
        payload = self.agent("Orchestrator")["text"].split("## Worker Payload\n", 1)[1].split("\n## ", 1)[0]
        payload = " ".join(payload.split())
        for clause in (
            "Avoid legacy code and backward-compatibility shims",
            "Before intentionally leaving legacy or backward/retro-compatible behavior in place",
            "ask the user for explicit confirmation",
            "Repository docs, tests, inferred compatibility, and general task authorization are not approval",
            "Only an explicit direction in the current request waives this question",
            "unless an explicit supported requirement needs them",
            "focused regression tests for the current supported behavior",
            "missing coverage is not evidence that code is unused",
            "Do not weaken tests to justify removal or delete unrelated legacy code",
            "NEEDS_INPUT with a focused question and ask the user before the affected change",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, payload)

    def test_orchestrator_numbers_choices_and_reply_references(self):
        delivery = self.agent("Orchestrator")["text"].split("## Boundaries and Delivery\n", 1)[1].split("\n## ", 1)[0]
        delivery = " ".join(delivery.split())
        for clause in (
            "Use concise prose, headings, or unordered bullets",
            "Use numbered lists for choices and for multiple proposals, findings, suggestions, or follow-up actions",
            "the user may select or refer to in a reply",
            "a distinct number within the answer",
            "do not restart numbering across related option groups",
            "Do not number ordinary explanatory paragraphs or a single recommendation",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, delivery)
        self.assertNotIn("every user-facing answer as a numbered enumeration", delivery)

    def test_orchestrator_requires_final_next_action(self):
        delivery = self.agent("Orchestrator")["text"].split("## Boundaries and Delivery\n", 1)[1].split("\n## ", 1)[0]
        delivery = " ".join(delivery.split())
        for clause in (
            'Always end every final user-facing answer with a closing recommendation labeled "Next action:"',
            "completed work, direct factual answers, diagnosis, review, NEEDS_INPUT, and BLOCKED outcomes",
            "recommend closing the task and state that no further action is needed",
            "Never invent extra work just to fill this item",
            "optional plain-text recommendation",
            "execute it without authorization",
            'verify that it ends with "Next action:" and its recommendation',
            "add the closing recommendation if missing",
            "unless the user explicitly requested no follow-up suggestions",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, delivery)
        self.assertNotIn("After meaningful completed work", delivery)
        self.assertNotIn("omit them when there is no natural continuation", delivery)

    def test_routing_loads_only_orchestrator_definition(self):
        definition = self.agent("Orchestrator")["text"]
        with patch.object(Path, "read_text", return_value=definition) as read_text:
            self.assertEqual(VALIDATOR["load_catalog"](), self.catalog)
        read_text.assert_called_once_with(encoding="utf-8")
        self.assertEqual(VALIDATOR["CATALOG_PATH"].name, "Orchestrator.agent.md")

    def test_embedded_routing_requires_both_tables(self):
        definition = self.agent("Orchestrator")["text"]
        for heading in ("Embedded Ownership", "Embedded Routing Index"):
            with self.subTest(heading=heading):
                with self.assertRaises(ValueError):
                    VALIDATOR["load_catalog"](definition.replace("## " + heading, "## Missing Section"))

    def test_embedded_routing_rejects_malformed_rows(self):
        definition = self.agent("Orchestrator")["text"].replace(
            "| CODE_ | CodeDomainAdvisor | Orchestrator |", "| CODE_ | CodeDomainAdvisor |",
        )
        with self.assertRaisesRegex(ValueError, "Malformed row"):
            VALIDATOR["load_catalog"](definition)

    def test_embedded_routing_rejects_duplicate_cues(self):
        definition = self.agent("Orchestrator")["text"]
        row = "| generic coding with no specialist match | CodeGeneralist | CodeDomainAdvisor |"
        with self.assertRaisesRegex(ValueError, "Duplicate selection cue"):
            VALIDATOR["load_catalog"](definition.replace(row, row + "\n" + row))

    def test_embedded_routing_rejects_unknown_advisors(self):
        definition = self.agent("Orchestrator")["text"].replace(
            "| CodeGeneralist | CodeDomainAdvisor |", "| CodeGeneralist | MissingAdvisor |",
        )
        with self.assertRaisesRegex(ValueError, "Unknown routing advisor"):
            VALIDATOR["load_catalog"](definition)

    def test_agent_names_reject_separators_lowercase_and_non_ascii(self):
        for name in ("codeExampleAgent", "Code_ExampleAgent", "Code-ExampleAgent", "CodeEx\u00e4mpleAgent"):
            with self.subTest(name=name):
                self.files = copy.deepcopy(self.baseline)
                self.agent("CodeGeneralist")["name"] = name
                self.assert_check("NAM-1")

    def test_worker_name_must_match_owning_domain(self):
        self.domain("CodeDomainAdvisor")["children"].append("GovGitWorkflowAgent")
        self.assert_check("NAM-1")

    def test_worker_name_requires_role_suffix(self):
        registry = dict(self.registry)
        registry["CodeWidget"] = Path("CodeWidget.agent.md")
        self.domain("CodeDomainAdvisor")["children"].append("CodeWidget")
        report = VALIDATOR["Report"]()
        VALIDATOR["check_topology"](self.files, registry, report, self.readme, self.catalog)
        self.assertIn("NAM-1", report.check_counts)

    def test_new_utility_name_requires_explicit_exception(self):
        self.domain("UtilityAdvisor")["children"].append("GovGitWorkflowAgent")
        self.assert_check("NAM-1")

    def test_every_agent_needs_readme_index_entry(self):
        self.readme = "\n".join(line for line in self.readme.splitlines() if not line.startswith("| **GovGitWorkflowAgent** |"))
        self.assert_check("DOC-1")

    def test_readme_index_rejects_duplicate_entries(self):
        row = next(line for line in self.readme.splitlines() if line.startswith("| **GovGitWorkflowAgent** |"))
        self.readme = self.readme.replace(row, row + "\n" + row)
        self.assert_check("DOC-1")

    def test_embedded_routes_must_match_catalog(self):
        self.agent("Orchestrator")["text"] = self.agent("Orchestrator")["text"].replace(
            "| Git branches, staging, commits, pushes or PR lifecycle |", "| obsolete selection cue |",
        )
        self.assert_check("DOC-1")

    def test_unknown_backtick_agent_is_rejected(self):
        self.readme += "\nRoute to `MissingAgent`.\n"
        self.assert_check("RST-3")

    def test_unknown_renamed_role_reference_is_rejected(self):
        for name in ("MissingSpecialist", "MissingDiagnostician", "MissingDiagnostics", "MissingSummarizer"):
            with self.subTest(name=name):
                self.readme = self.readme_text + f"\nRoute to `{name}`.\n"
                self.assert_check("RST-3")

    def test_unknown_domain_map_child_is_rejected(self):
        self.readme = self.readme.replace(
            "| AgentOptimizer, Brainstorm, ContextSummarizer |",
            "| AgentOptimizer, Brainstorm, ContextSummarizer, MissingSpecialist |",
        )
        self.assert_check("RST-3")

    def test_unknown_index_agent_is_rejected(self):
        self.readme += "\n| **MissingSpecialist** | no | no | Missing |\n"
        self.assert_check("RST-3")

    def test_fenced_code_example_is_not_an_agent_reference(self):
        self.readme += "\n```text\n`MissingAgent`\n```\n"
        self.assertEqual(self.validate().findings, [])

    def test_duplicate_parent_is_rejected(self):
        self.domain("UtilityAdvisor")["children"].append("CodeNextJsSpecialist")
        self.assert_check("RST-4")

    def test_duplicate_edge_is_rejected(self):
        self.domain("CodeFrontendAdvisor")["children"].append("CodeNextJsSpecialist")
        self.assert_check("RST-4")

    def test_direct_dispatch_has_no_ownership_penalty(self):
        root = self.agent("Orchestrator")["fm"]["agents"]
        self.assertIn("CodeNextJsSpecialist", root)
        self.assertIn("CodeFrontendAdvisor", root)
        self.assertEqual(self.validate().findings, [])

    def test_duplicate_runtime_target_is_rejected(self):
        self.agent("Orchestrator")["fm"]["agents"].append("Brainstorm")
        self.assert_check("RST-4")

    def test_root_cannot_have_a_parent(self):
        self.domain("UtilityAdvisor")["children"].append("Orchestrator")
        self.assert_check("RST-4")

    def test_readme_reference_does_not_make_detached_agent_reachable(self):
        self.agent("Orchestrator")["fm"]["agents"].remove("Brainstorm")
        self.assert_check("RST-2")

    def test_disconnected_ownership_group_is_unreachable(self):
        self.domain("CodeDomainAdvisor")["parent"] = "InfraDevOpsAdvisor"
        self.assert_check("RST-7")

    def test_self_cycle_is_rejected(self):
        self.domain("UtilityAdvisor")["children"].append("UtilityAdvisor")
        self.assert_check("RST-5")

    def test_disconnected_cycle_is_rejected(self):
        self.domain("CodeDomainAdvisor")["parent"] = "CodeFrontendAdvisor"
        self.domain("CodeFrontendAdvisor")["children"].append("CodeDomainAdvisor")
        self.assert_check("RST-5")

    def test_missing_diagram_edge_is_rejected(self):
        self.readme = self.readme.replace('    UtilityAdvisor --> Brainstorm["Brainstorm"]', "")
        self.assert_check("RST-6")

    def test_extra_diagram_edge_is_rejected(self):
        self.readme = self.readme.replace("flowchart LR", "flowchart LR\n    O --> MissingAgent")
        self.assert_check("RST-6")

    def test_duplicate_diagram_edge_is_rejected(self):
        self.readme = self.readme.replace("flowchart LR", "flowchart LR\n    UtilityAdvisor --> Brainstorm")
        self.assert_check("RST-6")

    def test_subadvisor_parent_is_enforced(self):
        self.domain("CodeDomainAdvisor")["children"].remove("CodeFrontendAdvisor")
        self.domain("UtilityAdvisor")["children"].append("CodeFrontendAdvisor")
        self.domain("CodeFrontendAdvisor")["parent"] = "UtilityAdvisor"
        self.assert_check("RST-7")

    def test_tier_one_advisor_cannot_be_nested(self):
        self.domain("UtilityAdvisor")["parent"] = "CodeDomainAdvisor"
        self.domain("CodeDomainAdvisor")["children"].append("UtilityAdvisor")
        self.assert_check("RST-7")

    def test_dispatcher_requires_agent_tool(self):
        self.agent("Orchestrator")["fm"]["tools"] = ["read/readFile"]
        self.assert_check("RST-4")

    def test_leaf_cannot_delegate(self):
        self.agent("Brainstorm")["fm"]["agents"] = ["AgentOptimizer"]
        self.assert_check("RST-4")

    def test_malformed_agents_list_is_rejected(self):
        self.agent("Orchestrator")["fm"]["agents"] = "Brainstorm"
        self.assert_check("RST-1")

    def test_unknown_delegation_is_rejected(self):
        self.agent("Orchestrator")["fm"]["agents"].append("MissingAgent")
        self.assert_check("RST-1")

    def test_non_string_delegation_is_rejected(self):
        self.agent("Orchestrator")["fm"]["agents"].append(7)
        self.assert_check("RST-1")

    def test_duplicate_canonical_name_is_rejected(self):
        self.files.append(copy.deepcopy(self.agent("Brainstorm")))
        self.assert_check("DEF-2")

    def test_frontmatter_requires_closing_delimiter(self):
        data, error = VALIDATOR["parse_frontmatter"]("---\nname: MissingAgent\n")
        self.assertIsNone(data)
        self.assertIn("closing delimiter", error)

    def test_advisor_must_be_tool_free(self):
        self.agent("CodeFrontendAdvisor")["fm"]["tools"] = ["read"]
        self.assert_check("RST-4")

    def test_advisor_cannot_delegate(self):
        self.agent("CodeFrontendAdvisor")["fm"]["agents"] = ["CodeNextJsSpecialist"]
        self.assert_check("RST-4")

    def test_worker_cannot_acquire_delegation_tool(self):
        self.agent("Brainstorm")["fm"]["tools"].append("agent")
        self.assert_check("RST-4")

    def test_dispatcher_cannot_acquire_execution_tool(self):
        self.agent("Orchestrator")["fm"]["tools"].append("execute")
        self.assert_check("RST-4")

    def test_tool_free_advisor_is_a_valid_definition(self):
        report = VALIDATOR["Report"]()
        VALIDATOR["check_definition"]([self.agent("CodeFrontendAdvisor")], report)
        self.assertEqual(report.findings, [])

    def test_unknown_catalog_child_is_rejected(self):
        self.domain("UtilityAdvisor")["children"].append("MissingAgent")
        self.assert_check("CAT-1")

    def test_route_cannot_target_an_advisor(self):
        self.domain("CodeDomainAdvisor")["routes"]["bad route"] = "CodeFrontendAdvisor"
        self.assert_check("CAT-1")

    def test_route_cannot_borrow_another_domains_worker(self):
        self.domain("CodeFrontendAdvisor")["routes"]["bad route"] = "GovGithubAgent"
        self.assert_check("CAT-1")

    def test_every_worker_needs_a_selection_cue(self):
        self.domain("CodeDomainAdvisor")["routes"].pop("generic coding with no specialist match")
        self.assert_check("CAT-1")

    def test_catalog_schema_is_checked(self):
        self.catalog["schema_version"] = 99
        self.assert_check("CAT-1")

    def test_catalog_dispatcher_is_checked(self):
        self.catalog["dispatcher"] = "Brainstorm"
        self.assert_check("CAT-1")

    def test_catalog_domains_require_a_list(self):
        self.catalog["domains"] = "invalid"
        self.assert_check("CAT-1")

    def test_catalog_domain_names_are_unique(self):
        self.domain("UtilityAdvisor")["domain"] = "CODE_"
        self.assert_check("CAT-1")

    def test_catalog_advisors_are_unique(self):
        self.catalog["domains"].append(copy.deepcopy(self.domain("UtilityAdvisor")))
        self.assert_check("CAT-1")

    def test_catalog_children_require_agent_names(self):
        self.domain("UtilityAdvisor")["children"].append(7)
        self.assert_check("CAT-1")

    def test_catalog_routes_require_an_object(self):
        self.domain("UtilityAdvisor")["routes"] = []
        self.assert_check("CAT-1")

    def test_execution_diagram_is_not_ownership(self):
        self.readme = self.readme.replace("flowchart TD", "flowchart TD\n    D --> ExtraExecutionStep")
        self.assertEqual(self.validate().findings, [])

    def test_missing_domain_organization_section_is_rejected(self):
        self.readme = self.readme.replace("## Domain Organization", "## Unrelated Section")
        self.assert_check("RST-6")

    def test_domain_organization_has_no_execution_tier_labels(self):
        section = VALIDATOR["readme_section"](self.readme, "Domain Organization")
        self.assertIn("belongs to", section)
        self.assertNotRegex(section, r"Tier-\d")

    def test_domain_map_parity_is_checked(self):
        self.readme = self.readme.replace(
            "| AgentOptimizer, Brainstorm, ContextSummarizer |",
            "| AgentOptimizer, Brainstorm |",
        )
        self.assert_check("RST-6")

    def test_implementation_workers_require_native_search(self):
        for entry in self.baseline:
            required, _ = VALIDATOR["tool_profile"](entry["name"])
            if not VALIDATOR["IMPLEMENTATION_TOOLS"] <= required:
                continue
            with self.subTest(agent=entry["name"]):
                self.files = copy.deepcopy(self.baseline)
                self.agent(entry["name"])["fm"]["tools"].remove("search")
                self.assert_check("TOOL-1")

    def test_ci_worker_requires_edit_access(self):
        self.agent("InfraCIDiagnostics")["fm"]["tools"].remove("edit")
        self.assert_check("TOOL-1")

    def test_inference_worker_has_standard_profile_and_unique_route(self):
        worker = self.agent("InfraLLMInferenceSpecialist")
        required, allowed = VALIDATOR["tool_profile"](worker["name"])
        self.assertEqual(required, {"read", "search", "edit", "execute"})
        self.assertEqual(allowed, required | {"todo"})
        self.assertEqual(set(worker["fm"]["tools"]), allowed)
        self.assertEqual(worker["fm"]["agents"], [])
        self.assertEqual(self.agent("Orchestrator")["fm"]["agents"].count(worker["name"]), 1)
        self.assertIn(worker["name"], self.domain("InfraDevOpsAdvisor")["children"])
        self.assertEqual(self.validate().findings, [])

    def test_inference_worker_requires_capacity_evidence_and_boundaries(self):
        definition = self.agent("InfraLLMInferenceSpecialist")["text"]
        for clause in (
            "Distinguish weight quantization from KV-cache representation",
            "bytes versus GB/GiB",
            "per-request versus shared allocation",
            "Missing metadata is unknown",
            "prediction error, uncertainty",
            "No large downloads",
            "never delegate",
            "## Controlled Engine Evaluation",
            "time-to-first-token separately from total latency",
            "Do not drop failed trials",
            "complete procedure; do not load external skills",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, definition)

    def test_implementation_worker_requires_execution(self):
        self.agent("CodeNextJsSpecialist")["fm"]["tools"].remove("execute")
        self.assert_check("TOOL-1")

    def test_read_only_and_documentation_workers_reject_execution(self):
        names = set(VALIDATOR["READ_ONLY_TOOLS"]) | VALIDATOR["CUSTOMIZATION_WORKERS"]
        for name in names:
            with self.subTest(agent=name):
                self.files = copy.deepcopy(self.baseline)
                self.agent(name)["fm"]["tools"].append("execute")
                self.assert_check("TOOL-1")

    def test_read_only_workers_reject_editing(self):
        for name in VALIDATOR["READ_ONLY_TOOLS"]:
            with self.subTest(agent=name):
                self.files = copy.deepcopy(self.baseline)
                self.agent(name)["fm"]["tools"].append("edit")
                self.assert_check("TOOL-1")

    def test_rebuild_engineer_has_read_only_profile(self):
        worker = copy.deepcopy(self.agent("CodeRebuildEngineer"))
        expected = {"read", "search"}
        required, allowed = VALIDATOR["tool_profile"](worker["name"])
        self.assertEqual((required, allowed), (expected, expected))
        self.assertEqual(set(worker["fm"]["tools"]), expected)

        worker["fm"]["tools"].extend(["edit", "execute"])
        report = VALIDATOR["Report"]()
        VALIDATOR["check_tool_profiles"]([worker], report)
        self.assertEqual(len(report.findings), 1)
        self.assertEqual(report.findings[0]["check"], "TOOL-1")

    def test_rebuild_spec_requires_evidence_and_decision_ready_deliverables(self):
        definition = " ".join(self.agent("CodeRebuildEngineer")["text"].split())
        for clause in (
            "## Input Review and Traceability",
            "BN-001, BR-001, FR-001 and NFR-001",
            "repository-relative source paths and symbols",
            "Keep observed, asserted, inferred and proposed records distinct",
            "## Migration and Planning Readiness",
            "migration validation and reconciliation",
            "cutover and rollback requirements",
            "planning-readiness verdict of ready, conditional, or blocked",
            "Never call an incomplete or unapproved specification implementation-ready",
            "## Report Handoff and Delivery",
            "## Report Handoff and Delivery",
            "For rebuild assessments, deliver a report package rooted at `docs/rebuild/README.md`",
            "open decisions",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, definition)

    def test_rebuild_spec_separates_capability_retention_from_implementation(self):
        contracts = {
            "CodeProductModernizationExpert": (
                "Recommend keep, improve, replace, remove, add or needs decision",
                "Preserving capability does not mean reusing code",
                "preserve, improve to redesign and remove to retire",
                "supported consumers and obligations",
                "Acceptance scenarios use representative inputs and expected output/state",
            ),
            "CodeArchitectureExpert": (
                "Compare viable options", "Modern does not automatically mean distributed",
                "identity/authorization, trust boundaries", "privacy/retention",
                "observability", "operating cost", "proposed decision records",
            ),
            "CodeRebuildEngineer": (
                "Dispositions, code reuse and architecture choices remain proposals",
                "Requested persistence goes to GovDocumentationSuiteGenerator",
                "verify actual saved paths",
                "focused validation through Orchestrator",
            ),
        }
        for owner, clauses in contracts.items():
            definition = " ".join(self.agent(owner)["text"].split())
            for clause in clauses:
                with self.subTest(owner=owner, clause=clause):
                    self.assertIn(clause, definition)

    def test_rebuild_spec_routing_and_documentation_are_synchronized(self):
        route = (
            '"Build the project bible for [repository]" or integrated rebuild assessment, roadmap/migration, portable package or readiness/decisions'
        )
        self.assertEqual(
            self.domain("CodeDomainAdvisor")["routes"][route], "CodeRebuildEngineer"
        )
        self.assertIn("`CodeRebuildEngineer`; not code implementation", self.agent("CodeDomainAdvisor")["text"])
        self.assertIn("## Repository Rebuild Specifications", self.readme)
        self.assertIn("Repository to rebuild specification | CodeRebuildEngineer", self.readme)
        self.assertIn("As-Is Project Bible integration", self.readme)
        self.assertIn("Diataxis classification", self.readme)
        self.assertIn("only resume point", self.readme)
        self.assertIn("one proposed next outcome", " ".join(self.readme.split()))
        self.assertIn('"Build the project bible for [repository]"', self.agent("CodeRebuildEngineer")["text"])
        self.assertIn("> Build the project bible for [repository]", self.readme)
        self.assertIn("current checkout/branch", " ".join(self.agent("CodeRebuildEngineer")["text"].split()))
        self.assertIn("current checkout and branch are the default source", " ".join(self.readme.split()))
        scenarios = VALIDATOR["yaml"].safe_load(
            (VALIDATOR["PROMPTS_DIR"] / "tests" / "roster-scenarios.yaml").read_text(encoding="utf-8")
        )
        bible = next(item for item in scenarios if item["id"] == "as-is-project-bible")
        self.assertEqual(bible["expected_worker"], "CodeRebuildEngineer")
        self.assertIn("docs/project-bible/interoperability.md first", bible["required_behavior"])
        self.assertIn("read back each complete owner artifact before commissioning the next", bible["required_behavior"])
        self.assertIn("not modernization by default", " ".join(self.agent("CodeDomainAdvisor")["text"].split()))

    def test_project_bible_profile_covers_as_is_views_without_starting_redesign(self):
        dispatcher = " ".join(self.agent("Orchestrator")["text"].split())
        profile = " ".join(self.agent("CodeRebuildEngineer")["text"].split())
        for owner in (
            "BusinessKnowledgeExpert", "CodeContextSchemaAuditor", "CodeArchitectureExpert",
            "GovDocumentationSuiteGenerator", "CodeQualityGuardrailReviewer",
        ):
            with self.subTest(owner=owner):
                self.assertIn(owner, dispatcher)
                self.assertIn(owner, profile)
        for clause in (
            "Build the project bible for [repository]",
            "business needs/requirements",
            "internal-component and external-system dependencies/contracts",
            "external-system dependencies/contracts",
            "C4 System Context, Container and Component views",
            "Diataxis categories by user need",
            "versioned YAML/JSON schema",
            "typed directional dependency edges",
            "interoperability register first",
            "docs/project-bible/README.md",
            "decisions and lifecycle artifacts by project stage",
            "decisions and lifecycle artifacts by project stage",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause.lower(), profile.lower())
        for clause in (
            "coverage denominator from declared repository scope",
            "current checkout/branch",
            "no prior scope/revision choice",
            "README includes the dashboard, coverage plan, exclusions/unknowns",
            "Every item has evidence or an explicit status/gap",
            "Coverage can be COMPLETE within scope while facts are unknown",
            "use PARTIAL for omitted items or missing required semantics, not unrun tests or pending approval",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause.lower(), profile.lower())
        architecture = " ".join(self.agent("CodeArchitectureExpert")["text"].split())
        self.assertIn("do not require a target-scope report", architecture)
        self.assertIn("CodeArchitectureExpert (as-is C4)", profile)
        self.assertIn("Complete in-scope evidence without approval", profile)
        self.assertIn("GovGitWorkflowAgent reads Git identity", dispatcher)
        self.assertIn("save `interoperability.md` first", dispatcher)
        self.assertIn("Persist/read back each artifact before next", dispatcher)
        self.assertIn("Project Bible: BusinessKnowledgeExpert", dispatcher)
        self.assertIn("README owns plan", dispatcher)
        self.assertIn("Inventory/disposition denominator", dispatcher)
        self.assertIn("one unnumbered coverage-plan table", profile)
        self.assertIn("separate exclusions and unknowns register", profile)
        self.assertNotIn("Next action:", architecture)
        for owner in ("CodeRebuildEngineer", "GovDocumentationSuiteGenerator", "CodeQualityGuardrailReviewer"):
            definition = " ".join(self.agent(owner)["text"].split())
            self.assertIn("README", definition)
        documentation = " ".join(self.agent("GovDocumentationSuiteGenerator")["text"].split())
        self.assertIn("dedicated interoperability-boundaries row", documentation)
        self.assertIn("Save `docs/project-bible/interoperability.md` first", documentation)
        self.assertIn("Persist each complete owner report and read it back before commissioning the next", documentation)
        self.assertIn("arc42 context/scope, building-block and runtime prompts", documentation)
        self.assertIn("Pact contracts are consumer/provider expectations, not test results", documentation)
        self.assertIn("Start README with `## Project Dashboard`", documentation)
        self.assertIn("interoperability counts by boundary/evidence state", documentation)
        self.assertIn("test inspection versus execution", documentation)
        self.assertIn("unknown is not zero", documentation)
        self.assertIn("Do not invent percentages or an overall health score", documentation)
        layout_sections = (
            "Project Dashboard; linked Contents; Scope & Context; Capabilities & Business Rules;",
            "Architecture & Interoperability; Data & Contracts; Documentation Map; Coverage & Evidence;",
            "Gaps, Unknowns & Exclusions; Decisions & Lifecycle; Verification; Artifacts & Resume",
        )
        for section in layout_sections:
            with self.subTest(layout=section):
                self.assertIn(section, documentation)
        self.assertIn("navigation front page", documentation)
        self.assertIn("link to canonical registers instead of repeating them", documentation)
        for path in (
            "docs/project-bible/README.md",
            "docs/project-bible/interoperability.md",
            "reports/business.md",
            "reports/schemas-and-dependencies.md",
            "reports/architecture.md",
            "reports/documentation-map.md",
        ):
            with self.subTest(path=path):
                self.assertIn(path, documentation)
        self.assertIn("Put standalone diagrams in `diagrams/` only when they clarify", documentation)
        self.assertIn("Create no empty directories or placeholder files", documentation)
        self.assertIn("For a dirty checkout, identify evidence as HEAD plus local changes", documentation)
        self.assertIn("Individual Bible reports contain findings/gaps but no repeated \"Next action\" footer", documentation)
        self.assertIn("README alone owns an unnumbered coverage table", documentation)
        reviewer = " ".join(self.agent("CodeQualityGuardrailReviewer")["text"].split())
        self.assertIn("package follows the declared `docs/project-bible/` layout", reviewer)
        self.assertIn("every material internal and external interoperability boundary", reviewer)
        auditor = " ".join(self.agent("CodeContextSchemaAuditor")["text"].split())
        self.assertIn("Interoperability is a required as-is deliverable", auditor)
        self.assertIn("entry points, channel/API registrations", auditor)
        self.assertIn("a sample of interfaces is not a repository-wide denominator", auditor)
        self.assertIn("interface a stable ID, provider/consumer, direction", auditor)
        self.assertIn("source, configured, test-only and runtime-verified links", auditor)
        self.assertIn("runtime-verified links", auditor)
        self.assertIn("material interoperability crossings visible", architecture)
        self.assertIn("review the declared scope/denominator against the README coverage plan", reviewer)
        self.assertIn("Verify the README coverage table accounts for business needs", reviewer)
        self.assertIn("must identify omitted in-scope items or missing required semantics", reviewer)
        self.assertIn("Verify the README dashboard is near the top", reviewer)
        self.assertIn("Reconcile counts to the coverage, interoperability and documentation registers", reviewer)
        self.assertIn("**Documentation Framework Crosswalk**", self.readme)
        self.assertIn("[C4](https://c4model.com/diagrams)", self.readme)
        self.assertIn("[arc42 Context & Scope](https://docs.arc42.org/section-3/)", self.readme)
        self.assertIn("[Diataxis](https://diataxis.fr/)", self.readme)
        scenario = next(
            item for item in VALIDATOR["yaml"].safe_load(
                (VALIDATOR["PROMPTS_DIR"] / "tests" / "roster-scenarios.yaml").read_text(encoding="utf-8")
            ) if item["id"] == "as-is-project-bible"
        )

    def test_rebuild_package_requires_portable_behavior_and_completeness_review(self):
        definition = " ".join(self.agent("CodeRebuildEngineer")["text"].split())
        for clause in (
            "## Portable Rebuild Specification",
            "usable in a fresh repository without access to the",
            "Citations establish provenance",
            "analyzed,\n  deferred, excluded, or unknown",
            "state transitions, business rules, validation, failure/recovery behavior",
            "representative inputs and expected results",
            "Carry concise evidence summaries",
            "Include an implementation handoff",
            "Include a downstream kickoff prompt",
            "Audit the package as if only its delivered files existed",
            "List unresolved dependencies and exact missing decisions",
        ):
            with self.subTest(clause=clause):
                self.assertIn(" ".join(clause.split()), definition)

    def test_rebuild_package_consumption_limits_blockers_to_affected_slices(self):
        definition = self.agent("CodeRebuildEngineer")["text"]
        for clause in (
            "Identify the requested report/workstream",
            "do not restart source discovery automatically",
            "evidence coverage, specification completeness and approval status",
            "Block only the affected decision or slice",
            "not planning against explicit target contracts",
            "Request original source only for a named unresolved parity question",
            "entire legacy repository as a blanket prerequisite",
            "Do not invent missing behavior",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, definition)
        scenario_path = VALIDATOR["PROMPTS_DIR"] / "tests" / "roster-scenarios.yaml"
        scenarios = VALIDATOR["yaml"].safe_load(scenario_path.read_text(encoding="utf-8"))
        scenario = next(item for item in scenarios if item["id"] == "rebuild-portable-consumption")
        self.assertEqual(scenario["expected_worker"], "CodeRebuildEngineer")
        self.assertEqual(scenario["split"], "held-out")
        self.assertIn("legacy source is intentionally unavailable", scenario["prompt"])
        self.assertIn("keep the proposed slice unapproved", scenario["required_behavior"])

    def test_rebuild_package_export_preserves_full_content_across_handoffs(self):
        writer = self.agent("GovDocumentationSuiteGenerator")["text"]
        for clause in (
            "## Portable Rebuild Package Export",
            "preserve the complete specification",
            "Historical source files need not exist in the fresh repository",
            "Review sufficiency using only the exported package",
            "PARTIAL with focused questions",
            "concise status summary separate from the complete package content",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, writer)
        dispatcher = self.agent("Orchestrator")["text"]
        self.assertIn("Preserve complete artifact content through documentation handoff", dispatcher)
        self.assertIn("do not blanket-block independent work", dispatcher)
        self.assertIn("Use the exported package in a fresh repository", self.readme)

    def test_rebuild_report_workflow_keeps_phases_only_in_roadmap(self):
        definition = self.agent("CodeRebuildEngineer")["text"]
        for clause in (
            "## Professional Assessment Reports",
            "## Report Index and Resume Contract",
            "## Numbered Rebuild Roadmap",
            "docs/rebuild/README.md",
            "Numbered phases belong only inside the proposed implementation/rebuild roadmap",
            "PASS/FAIL/UNKNOWN",
            "Emit only workflow_version professional-report-v1",
            "Missing evidence is PARTIAL/UNKNOWN, never invented",
            "Changed inputs invalidate affected downstream reports/reviews",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause.lower(), definition.lower())
        self.assertNotIn("## Phase-Gated Capability Workflow", definition)
        self.assertNotIn("## Phase Checkpoint Contract", definition)
        self.assertNotIn("| Phase | Entry |", definition)

    def test_rebuild_report_dispatch_requires_independent_review_and_authorization(self):
        dispatcher = self.agent("Orchestrator")["text"]
        section = " ".join(dispatcher.split("## Rebuild Report Coordination\n", 1)[1].split("\n## ", 1)[0].split()).lower()
        for clause in (
            "do not request interim approvals",
            "separate read-only codegeneralist invocation",
            "supplied package content/criteria",
            "review is not approval or executed test evidence",
            "explicitly approved",
            "changed inputs invalidate affected findings",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause.lower(), section)
        self.assertIn("### Rebuild Report Workflow", self.readme)
        self.assertIn("README.md` is the index and resume point", self.readme)

    def test_rebuild_report_records_preserve_versions_and_review_status(self):
        writer = self.agent("GovDocumentationSuiteGenerator")["text"]
        section = " ".join(writer.split("## Rebuild Report and Roadmap Persistence\n", 1)[1].split("\n## ", 1)[0].split())
        for clause in (
            "report_id, capability_id where relevant, roadmap_phase only for rebuild",
            "PASS/FAIL/UNKNOWN",
            "COMPLETE, PARTIAL and NEEDS_INPUT",
            "separate-reader reviews with their exact current artifact",
            "mark affected downstream gates/reviews stale",
            "no authority or approval is inferred",
            "File existence and link checks are not proof",
            "Do not retain legacy phase labels in current headings, filenames, aliases",
            "Emit workflow_version professional-report-v1 only",
            "Do not map prior workflow versions",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, section)
        self.assertNotIn("consolidated-review-v2", section)
        scenario_path = VALIDATOR["PROMPTS_DIR"] / "tests" / "roster-scenarios.yaml"
        scenarios = VALIDATOR["yaml"].safe_load(scenario_path.read_text(encoding="utf-8"))
        expected = {
            "rebuild-report-sufficiency": "CodeRebuildEngineer",
            "rebuild-independent-review": "CodeGeneralist",
        }
        for scenario_id, worker in expected.items():
            with self.subTest(scenario=scenario_id):
                scenario = next(item for item in scenarios if item["id"] == scenario_id)
                self.assertEqual(scenario["expected_worker"], worker)
                self.assertEqual(scenario["split"], "held-out")

    def test_rebuild_reports_defer_decisions_not_evidence_gaps(self):
        definition = " ".join(self.agent("CodeRebuildEngineer")["text"].split())
        for clause in (
            "Record options for consolidated review instead of requesting feature approvals during discovery",
            "Technical completeness, evidence coverage and approval are separate",
            "a critical missing behavior or contract keeps only affected report scope PARTIAL",
            "Delivery of this report is not approval",
            "Preserve separate as-is and to-be specifications and their change map",
            "Emit only workflow_version professional-report-v1",
            "Do not resume phase-numbered checkpoints or map old phase workflows",
            "Treat any supplied old artifact only as unverified source evidence",
            "Do not emit legacy filenames, aliases, prior workflow versions or compatibility mappings",
            "Use canonical descriptive report names",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, definition)
        self.assertNotIn("Unresolved approval keeps this gate open", definition)
        self.assertNotIn("Phase 7 decision closure", definition)

    def test_rebuild_consolidated_review_is_preserved_by_coordinator_and_writer(self):
        dispatcher = " ".join(self.agent("Orchestrator")["text"].split())
        writer = " ".join(self.agent("GovDocumentationSuiteGenerator")["text"].split())
        for clause in (
            "project bible: businessknowledgeexpert",
            "carry options to the decision report",
            "do not request interim approvals",
            "The rebuild roadmap contains the only numbered phases",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause.lower(), dispatcher.lower())
        for clause in (
            "Analysis reports can be technically COMPLETE while approval_status remains pending",
            "Keep distinct as-is, feature/opportunity assessment, proposed architecture, to-be",
            "Explicit approval remains required to accept decisions or authorize implementation",
            "Validate anchors against actual headings",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, writer)
        self.assertIn("workflow_version professional-report-v1", writer)
        scenario_path = VALIDATOR["PROMPTS_DIR"] / "tests" / "roster-scenarios.yaml"
        scenarios = VALIDATOR["yaml"].safe_load(scenario_path.read_text(encoding="utf-8"))
        scenario = next(item for item in scenarios if item["id"] == "rebuild-consolidated-review")
        self.assertEqual(scenario["expected_worker"], "CodeRebuildEngineer")
        self.assertEqual(scenario["split"], "held-out")

    def test_enterprise_knowledge_requires_six_layers_and_explicit_business_catalogues(self):
        definition = " ".join(self.agent("BusinessKnowledgeExpert")["text"].split())
        for clause in (
            "laws/regulations, internal policies, business processes, systems/infrastructure, enterprise data and source code",
            "Missing layers limit conclusions, not all useful work",
            "separately indexed business-requirement and business-rule catalogues",
            "trigger, preconditions, inputs/fields, decision logic",
            "Documentation-only material can establish a declared rule, not verified runtime implementation",
            "A supplied regulation is not proof it applies",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, definition)

    def test_enterprise_knowledge_graph_has_provenance_and_stable_relationships(self):
        definition = " ".join(self.agent("BusinessKnowledgeExpert")["text"].split())
        for clause in (
            "## Optional Structured Knowledge Export",
            "Do not add a full graph/snapshot to the default Project Bible or business report",
            "Produce a separate versioned YAML/JSON graph only when the user requests one",
            "Link records to canonical catalogue IDs rather than copying full prose",
            "schema_version, snapshot_version, scope, source_registry, nodes, edges",
            "edges carry id, from_id, relation, to_id and evidence_refs",
            "claim_status (observed/asserted/inferred/proposed/unknown/",
            "do not infer identity or links from matching names or co-occurrence",
            "Validate unique IDs, edge endpoints, relation definitions and source locators",
            "Approval is not confidence",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, definition)

    def test_enterprise_knowledge_queries_preserve_broken_paths_and_refresh_limits(self):
        definition = " ".join(self.agent("BusinessKnowledgeExpert")["text"].split())
        for clause in (
            "Show verified segments and the exact broken hop",
            "Never invent a bridge to make a complete chain",
            "directly evidenced impacts, transitive evidence-backed dependencies, inferred candidates",
            "missing links do not prove absence of impact",
            "Absence from a partial inventory is not confirmed deletion",
            "Do not claim continuous monitoring or automatic indexing",
            "Secrets and personal data are excluded or redacted",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, definition)

    def test_enterprise_knowledge_dispatch_and_export_preserve_evidence_boundaries(self):
        dispatcher = " ".join(self.agent("Orchestrator")["text"].split())
        writer = " ".join(self.agent("GovDocumentationSuiteGenerator")["text"].split())
        for clause in (
            "A product overview or bare source links are not those deliverables",
            "Require the exact broken hop when a chain is incomplete",
            "Do not accept unsupported claims of legal compliance",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, dispatcher)
        for clause in (
            "A YAML/JSON graph is optional",
            "only when explicitly requested or required by a concrete query/refresh use case",
            "Do not copy entire catalogue prose into graph nodes",
            "Review ID uniqueness, edge endpoints and source locators",
            "this role cannot run parsers, query engines or tests",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, writer)
        self.assertIn("## Enterprise Knowledge Reconstruction", self.readme)
        self.assertIn("Enterprise knowledge reconstruction/query | BusinessKnowledgeExpert", self.readme)
        self.assertIn("traceability", self.agent("BusinessKnowledgeAdvisor")["text"])
        scenario_path = VALIDATOR["PROMPTS_DIR"] / "tests" / "roster-scenarios.yaml"
        scenarios = VALIDATOR["yaml"].safe_load(scenario_path.read_text(encoding="utf-8"))
        for scenario_id in (
            "enterprise-knowledge-broken-chain", "enterprise-knowledge-impact-refresh",
        ):
            with self.subTest(scenario=scenario_id):
                scenario = next(item for item in scenarios if item["id"] == scenario_id)
                self.assertEqual(scenario["expected_worker"], "BusinessKnowledgeExpert")
                self.assertEqual(scenario["split"], "held-out")

    def test_unrelated_workers_reject_github_access(self):
        self.agent("CodeGeneralist")["fm"]["tools"].append("github/*")
        self.assert_check("TOOL-1")

    def test_dispatcher_rejects_github_access(self):
        self.agent("Orchestrator")["fm"]["tools"].append("github/*")
        self.assert_check("TOOL-1")

    def test_github_worker_cannot_edit_source_files(self):
        for name in ("GovGithubAgent", "GovGitWorkflowAgent"):
            with self.subTest(agent=name):
                self.files = copy.deepcopy(self.baseline)
                self.agent(name)["fm"]["tools"].append("edit")
                self.assert_check("TOOL-1")

    def test_git_worker_has_exact_tool_profile(self):
        expected = {"read", "search", "execute", "github/*"}
        self.assertEqual(VALIDATOR["tool_profile"]("GovGitWorkflowAgent"), (expected, expected))
        self.assertEqual(set(self.agent("GovGitWorkflowAgent")["fm"]["tools"]), expected)

    def test_web_research_has_exact_read_only_profile(self):
        expected = {"read", "search", "io.github.ihor-sokoliuk/mcp-searxng/*"}
        self.assertEqual(VALIDATOR["tool_profile"]("GovWebResearchAgent"), (expected, expected))
        worker = self.agent("GovWebResearchAgent")
        self.assertEqual(set(worker["fm"]["tools"]), expected)
        self.assertEqual(worker["fm"]["agents"], [])
        self.assertIs(worker["fm"]["user-invocable"], True)

    def test_web_research_rejects_mutation_and_delegation_tools(self):
        for tool in ("edit", "execute", "agent", "github/*"):
            with self.subTest(tool=tool):
                self.files = copy.deepcopy(self.baseline)
                self.agent("GovWebResearchAgent")["fm"]["tools"].append(tool)
                report = VALIDATOR["Report"]()
                VALIDATOR["check_tool_profiles"](self.files, report)
                self.assertTrue(any(
                    finding["check"] == "TOOL-1" and "GovWebResearchAgent" in finding["path"]
                    for finding in report.findings
                ))

    def test_web_research_embeds_evidence_and_safety_procedure(self):
        definition = self.agent("GovWebResearchAgent")["text"]
        for clause in (
            "without loading local skills", "untrusted evidence", "generic queries",
            "searxng_web_search", "web_url_read", "searxng_instance_info",
            "version applicability", "mark it unverified", "Return BLOCKED",
            "Orchestrator alone", "source titles and URLs",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, definition)

    def test_web_research_requires_all_profile_tools(self):
        required, _ = VALIDATOR["tool_profile"]("GovWebResearchAgent")
        for tool in required:
            with self.subTest(tool=tool):
                self.files = copy.deepcopy(self.baseline)
                self.agent("GovWebResearchAgent")["fm"]["tools"].remove(tool)
                report = VALIDATOR["Report"]()
                VALIDATOR["check_tool_profiles"](self.files, report)
                self.assertTrue(any("GovWebResearchAgent" in finding["path"] for finding in report.findings))

    def test_web_research_is_routed_through_dispatcher(self):
        domain = self.domain("DocsGovernanceAdvisor")
        self.assertIn("GovWebResearchAgent", domain["children"])
        self.assertEqual(
            domain["routes"]["SearXNG, internet search/research, public URL reading, current documentation, source verification or web comparisons"],
            "GovWebResearchAgent",
        )
        dispatcher = self.agent("Orchestrator")
        self.assertEqual(dispatcher["fm"]["agents"].count("GovWebResearchAgent"), 1)
        self.assertNotIn("io.github.ihor-sokoliuk/mcp-searxng/*", dispatcher["fm"]["tools"])
        self.assertIn("invoke research\n  first", dispatcher["text"])
        self.assertIn("GovWebResearchAgent", self.agent("DocsGovernanceAdvisor")["text"])

    def test_web_research_dispatch_precedes_factual_shortcut_and_tool_blocker(self):
        definition = self.agent("Orchestrator")["text"]
        self.assertLess(
            definition.index("Route SearXNG"),
            definition.index("Answer simple factual questions directly only"),
        )
        for clause in (
            "searxng_web_search", "web_url_read",
            "Invoke the worker before declaring web research unavailable",
            "discover/load its deferred", "runtime-exposed tool names",
            "report BLOCKED only after an invocation failure",
            "worker reports missing tools or a service error",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, definition)
        self.assertIn("owns SearXNG tools", self.agent("DocsGovernanceAdvisor")["text"])

    def test_dispatcher_rejects_searxng_access(self):
        self.agent("Orchestrator")["fm"]["tools"].append("io.github.ihor-sokoliuk/mcp-searxng/*")
        self.assert_check("TOOL-1")

    def test_web_research_source_procedure_is_read_only(self):
        definition = self.agent("GovWebResearchAgent")["text"]
        self.assertIn("do not edit files, execute commands", definition)
        self.assertIn("not authorization to implement", definition)

    def test_git_worker_requires_workflow_tools(self):
        for tool in ("read", "search", "execute", "github/*"):
            with self.subTest(tool=tool):
                self.files = copy.deepcopy(self.baseline)
                self.agent("GovGitWorkflowAgent")["fm"]["tools"].remove(tool)
                self.assert_check("TOOL-1")

    def test_git_worker_is_not_user_invocable_and_routed(self):
        worker = self.agent("GovGitWorkflowAgent")
        self.assertIs(worker["fm"]["user-invocable"], False)
        self.assertEqual(worker["fm"]["agents"], [])
        domain = self.domain("DocsGovernanceAdvisor")
        self.assertIn("GovGitWorkflowAgent", domain["children"])
        self.assertEqual(
            domain["routes"]["Git branches, staging, commits, pushes or PR lifecycle"],
            "GovGitWorkflowAgent",
        )
        self.assertEqual(self.agent("Orchestrator")["fm"]["agents"].count("GovGitWorkflowAgent"), 1)

    def test_tool_profile_rejects_duplicate_tools(self):
        self.agent("CodeGeneralist")["fm"]["tools"].append("read")
        self.assert_check("TOOL-1")

    def test_tool_profile_rejects_unknown_tool_groups(self):
        self.agent("CodeGeneralist")["fm"]["tools"].append("unknown/*")
        self.assert_check("TOOL-1")

    def test_implementation_planning_tool_is_optional(self):
        self.agent("CodeNextJsSpecialist")["fm"]["tools"].remove("todo")
        self.assertEqual(self.validate().findings, [])

    def test_documentation_worker_requires_search(self):
        self.agent("GovDocumentationSuiteGenerator")["fm"]["tools"].remove("search")
        self.assert_check("TOOL-1")

    def test_framework_diagnostician_requires_search(self):
        self.agent("CodeFrameworkDiagnostician")["fm"]["tools"].remove("search")
        self.assert_check("TOOL-1")


if __name__ == "__main__":
    unittest.main()