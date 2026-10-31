import copy
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

    def test_current_roster_passes(self):
        self.assertEqual(self.validate().findings, [])

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
        self.assertEqual(len(scenarios), 26)
        self.assertEqual(len({scenario["id"] for scenario in scenarios}), len(scenarios))
        self.assertEqual({scenario["split"] for scenario in scenarios}, {"calibration", "held-out"})
        self.assertEqual(sum(scenario["split"] == "held-out" for scenario in scenarios), 8)
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
        self.assertEqual(len(workers), 23)
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

    def test_orchestrator_requires_numbered_user_facing_answers(self):
        delivery = self.agent("Orchestrator")["text"].split("## Boundaries and Delivery\n", 1)[1].split("\n## ", 1)[0]
        self.assertIn("every user-facing answer as a numbered enumeration using an ordered list", delivery)
        self.assertIn("Do not use unordered bullets, standalone unnumbered prose, or unnumbered headings", delivery)
        self.assertIn("Number suggestions and follow-up items as part of the same enumeration", delivery)

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
            domain["routes"]["internet research, current documentation, source verification or web comparisons"],
            "GovWebResearchAgent",
        )
        dispatcher = self.agent("Orchestrator")
        self.assertEqual(dispatcher["fm"]["agents"].count("GovWebResearchAgent"), 1)
        self.assertNotIn("io.github.ihor-sokoliuk/mcp-searxng/*", dispatcher["fm"]["tools"])
        self.assertIn("invoke research\n  first", dispatcher["text"])
        self.assertIn("GovWebResearchAgent", self.agent("DocsGovernanceAdvisor")["text"])

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

    def test_git_worker_is_user_invocable_and_routed(self):
        worker = self.agent("GovGitWorkflowAgent")
        self.assertIs(worker["fm"]["user-invocable"], True)
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