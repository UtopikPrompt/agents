import copy
import runpy
import unittest
from pathlib import Path
from unittest.mock import patch


VALIDATOR = runpy.run_path(str(Path(__file__).with_name("agent-roster-validator.py")))


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
        for name in ("GovGithubAgent", "GitGithubAgent"):
            with self.subTest(agent=name):
                self.files = copy.deepcopy(self.baseline)
                self.agent(name)["fm"]["tools"].append("edit")
                self.assert_check("TOOL-1")

    def test_git_worker_has_exact_tool_profile(self):
        expected = {"read", "search", "execute", "github/*"}
        self.assertEqual(VALIDATOR["tool_profile"]("GitGithubAgent"), (expected, expected))
        self.assertEqual(set(self.agent("GitGithubAgent")["fm"]["tools"]), expected)

    def test_git_worker_requires_workflow_tools(self):
        for tool in ("read", "search", "execute", "github/*"):
            with self.subTest(tool=tool):
                self.files = copy.deepcopy(self.baseline)
                self.agent("GitGithubAgent")["fm"]["tools"].remove(tool)
                self.assert_check("TOOL-1")

    def test_git_worker_is_user_invocable_and_routed(self):
        worker = self.agent("GitGithubAgent")
        self.assertIs(worker["fm"]["user-invocable"], True)
        self.assertEqual(worker["fm"]["agents"], [])
        domain = self.domain("DocsGovernanceAdvisor")
        self.assertIn("GitGithubAgent", domain["children"])
        self.assertEqual(
            domain["routes"]["Git branches, staging, commits, pushes or PR lifecycle"],
            "GitGithubAgent",
        )
        self.assertEqual(self.agent("Orchestrator")["fm"]["agents"].count("GitGithubAgent"), 1)

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