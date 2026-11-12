# Agent Roster

This repository holds definitions for agents available for routing and optional
repository-local skills. Each `.agent.md` file is a self-contained prompt that
governs one agent's behavior, tools, and triggers.

Keep shared artifacts generic: no personal information, account/organization
identities, external repository inventories/URLs, activity/session identifiers,
private host details, credentials or absolute user paths. Use synthetic examples
and repository-relative paths. Gather task-specific context at runtime instead
of embedding it in reusable agents, skills, scenarios or reports. See the
[generic improvements summary](agent-roster-improvements.md).

## Optional Skills

`agent-model-benchmark` is a user-invocable workflow for paired, read-only model
comparisons using this roster's pilot tasks. It is opt-in and depends on runtime
support for explicit-model subagent calls and usage telemetry; no agent workflow
requires it.

## Architecture

Execution and ownership are separate. **Orchestrator is the only dispatcher**
and directly invokes the selected worker. Its embedded routing and ownership tables contain
names, ownership, and selection cues, not every specialist's full instructions.
The roster has seven tool-free **advisors**, including the business knowledge domain. Clear tasks skip
them; ambiguous tasks consult at most one advisor, which returns a decision to
the dispatcher rather than invoking a worker.

Run Orchestrator as the main chat agent. Workers inspect relevant implementation
locally and return concise evidence. Do not copy whole prompts, chat history, or
unrelated file dumps into their payloads. Independent tasks with disjoint write sets may use separate workers concurrently;
overlapping edits and dependent interfaces must be sequenced.

This reduces required routing hops and intentional context copying; it does not
guarantee a measured token or latency reduction. The runtime may still expose
agent names and descriptions for discovery. Full specialist prompts must not be
manually loaded into the dispatcher just to select a worker.

### Remote SSH Routing

Orchestrator embeds the compact worker selection index in its definition, so
ordinary dispatch does not need access to this folder or a local Windows path
from remote read/search tools. Its Embedded Routing Index and Embedded Ownership
tables are the only routing source of truth; no separate JSON catalog is needed.
Never search the remote host or client profile for routing files. Advisors receive
the relevant rows directly from Orchestrator. The selected worker must still
be exposed by the runtime agent tool; otherwise Orchestrator reports BLOCKED.

Required workflows must be embedded in their owning agent definitions. Local
skills and client-profile files are not assumed accessible from Remote SSH.
Do not load an external workflow or copy all worker procedures into the dispatcher;
the runtime supplies the selected worker's self-contained definition. Missing
tools, model metadata or task-specific evidence remain explicit blockers.

## Execution

```mermaid
flowchart TD
    U["User task"] --> D["Orchestrator: compact routing index"]
    D --> Q{"Specialist clear?"}
    Q -->|Yes| P["Minimal task payload"]
    Q -->|No| A["One tool-free domain advisor"]
    A --> J["Routing decision only"]
    J --> D
    P -->|One task| S["One direct specialist"]
    P -->|Independent tasks| M["Concurrent direct specialists"]
    S --> V["Focused validation"]
    M --> V
    V --> R["Concise result and evidence"]
    R --> D
    D --> F["User-facing answer"]
```

The advisor and worker are separate calls from the main dispatcher. Independent
workers may run concurrently only when their write sets are disjoint; Orchestrator
waits for their results and reconciles them before responding. No subagent needs
to invoke another subagent. An advisor decision is not an execution receipt.

## Domain Organization

This graph groups agents by domain; it is not a call chain or approval hierarchy.
Each arrow places the right-hand agent in the left-hand group: read it as
"belongs to," not "invokes." Advisors do not supervise, approve, or invoke their
grouped specialists. Actual calls are shown separately in the Execution diagram.

The source of truth is the embedded routing and ownership tables in
[Orchestrator.agent.md](Orchestrator.agent.md). Each non-root
agent has exactly one organizational owner. CodeGeneralist is the coding fallback
worker; advisors return selection advice and never implement changes.

```mermaid
flowchart LR
    O["Orchestrator<br/>(Dispatcher; parallel independent work)"]
    O --> CodeDomainAdvisor["CodeDomainAdvisor<br/>(Coding domain)"]
    O --> InfraDevOpsAdvisor["InfraDevOpsAdvisor<br/>(Infrastructure domain)"]
    O --> DocsGovernanceAdvisor["DocsGovernanceAdvisor<br/>(Documentation and governance)"]
    O --> BusinessKnowledgeAdvisor["BusinessKnowledgeAdvisor<br/>(Business knowledge)"]
    O --> UtilityAdvisor["UtilityAdvisor<br/>(Utility domain)"]
    CodeDomainAdvisor --> CodeFrontendAdvisor["CodeFrontendAdvisor<br/>(Frontend group)"]
    CodeDomainAdvisor --> CodeBackendAdvisor["CodeBackendAdvisor<br/>(Backend group)"]
    CodeDomainAdvisor --> MultiLanguageBuilder["MultiLanguageBuilder"]
    CodeDomainAdvisor --> CodeFrameworkDiagnostician["CodeFrameworkDiagnostician"]
    CodeDomainAdvisor --> CodeGeneralist["CodeGeneralist"]
    CodeDomainAdvisor --> CodeComfyUICustomNodeSpecialist["CodeComfyUICustomNodeSpecialist"]

    CodeFrontendAdvisor --> CodeNextJsSpecialist["CodeNextJsSpecialist<br/>(Next.js applications and UI)"]
    CodeFrontendAdvisor --> CodeReactViteSpecialist["CodeReactViteSpecialist<br/>(React/Vite applications and UI)"]
    CodeFrontendAdvisor --> CodeDesignSystemSpecialist["CodeDesignSystemSpecialist<br/>(shared components and tokens)"]
    CodeFrontendAdvisor --> CodeMockupWireframeSpecialist["CodeMockupWireframeSpecialist"]

    CodeBackendAdvisor --> CodeSpringBootSpecialist["CodeSpringBootSpecialist"]
    CodeBackendAdvisor --> CodeExpressSpecialist["CodeExpressSpecialist"]
    CodeBackendAdvisor --> CodeGraphQLTRPCAgent["CodeGraphQLTRPCAgent"]
    CodeBackendAdvisor --> CodeDatabaseORMGenerator["CodeDatabaseORMGenerator"]
    CodeDomainAdvisor --> CodeRebuildEngineer["CodeRebuildEngineer<br/>(roadmap, migration and integration)"]
    CodeDomainAdvisor --> CodeProductModernizationExpert["CodeProductModernizationExpert"]
    CodeDomainAdvisor --> CodeArchitectureExpert["CodeArchitectureExpert"]
    CodeDomainAdvisor --> CodeContextSchemaAuditor["CodeContextSchemaAuditor"]
    CodeDomainAdvisor --> CodeQualityGuardrailReviewer["CodeQualityGuardrailReviewer"]
    CodeBackendAdvisor --> CodeFastApiSpecialist["CodeFastApiSpecialist"]

    InfraDevOpsAdvisor --> InfraMonorepoManager["InfraMonorepoManager"]
    InfraDevOpsAdvisor --> InfraDevContainerSpecialist["InfraDevContainerSpecialist"]
    InfraDevOpsAdvisor --> InfraMCPServerGenerator["InfraMCPServerGenerator"]
    InfraDevOpsAdvisor --> InfraObservabilitySpecialist["InfraObservabilitySpecialist"]
    InfraDevOpsAdvisor --> InfraCloudDeploymentAgent["InfraCloudDeploymentAgent"]
    InfraDevOpsAdvisor --> InfraKubernetesEngineer["InfraKubernetesEngineer"]
    InfraDevOpsAdvisor --> InfraSecurityAuthAgent["InfraSecurityAuthAgent"]
    InfraDevOpsAdvisor --> InfraIaCGenerator["InfraIaCGenerator"]
    InfraDevOpsAdvisor --> InfraPerformanceProfiler["InfraPerformanceProfiler"]
    InfraDevOpsAdvisor --> InfraLLMInferenceSpecialist["InfraLLMInferenceSpecialist"]
    InfraDevOpsAdvisor --> InfraTestInfrastructureGenerator["InfraTestInfrastructureGenerator"]
    InfraDevOpsAdvisor --> InfraReleaseManager["InfraReleaseManager"]
    InfraDevOpsAdvisor --> InfraCIDiagnostics["InfraCIDiagnostics"]

    DocsGovernanceAdvisor --> GovArchitectureRecordsExpert["GovArchitectureRecordsExpert"]
    DocsGovernanceAdvisor --> GovDocumentationSuiteGenerator["GovDocumentationSuiteGenerator"]
    DocsGovernanceAdvisor --> GovGithubAgent["GovGithubAgent"]
    DocsGovernanceAdvisor --> GovGitWorkflowAgent["GovGitWorkflowAgent"]
    DocsGovernanceAdvisor --> GovWebResearchAgent["GovWebResearchAgent"]

    BusinessKnowledgeAdvisor --> BusinessKnowledgeExpert["BusinessKnowledgeExpert<br/>(requirements, rules and evidence)"]

    UtilityAdvisor --> AgentOptimizer["AgentOptimizer"]
    UtilityAdvisor --> Brainstorm["Brainstorm"]
    UtilityAdvisor --> ContextSummarizer["ContextSummarizer"]

    classDef hub fill:#3b3f7d,stroke:#e0e0e0,color:#fff;
    classDef domainAdvisor fill:#6f9e6f,stroke:#516399,color:#000;
    classDef subdomainAdvisor fill:#a3c1ad,stroke:#516399,color:#000;
    classDef worker fill:#9db8ff,stroke:#516399,color:#000;
    classDef frameworkWorker fill:#f2d49b,stroke:#516399,color:#000;
    
    class O hub;
    class CodeDomainAdvisor,InfraDevOpsAdvisor,DocsGovernanceAdvisor,BusinessKnowledgeAdvisor,UtilityAdvisor domainAdvisor;
    class CodeFrontendAdvisor,CodeBackendAdvisor subdomainAdvisor;
    class CodeNextJsSpecialist,CodeReactViteSpecialist,CodeGraphQLTRPCAgent,CodeFastApiSpecialist,CodeExpressSpecialist,CodeSpringBootSpecialist,CodeDatabaseORMGenerator,CodeDesignSystemSpecialist,CodeRebuildEngineer frameworkWorker;
    class CodeMockupWireframeSpecialist worker;
    class CodeComfyUICustomNodeSpecialist frameworkWorker;
    class BusinessKnowledgeExpert,CodeProductModernizationExpert,CodeArchitectureExpert,CodeContextSchemaAuditor,CodeQualityGuardrailReviewer worker;
    class AgentOptimizer,Brainstorm,ContextSummarizer,CodeGeneralist,CodeFrameworkDiagnostician,MultiLanguageBuilder,InfraObservabilitySpecialist,InfraMonorepoManager,InfraDevContainerSpecialist,InfraMCPServerGenerator,InfraCloudDeploymentAgent,InfraKubernetesEngineer,InfraSecurityAuthAgent,InfraIaCGenerator,InfraPerformanceProfiler,InfraLLMInferenceSpecialist,InfraTestInfrastructureGenerator,InfraReleaseManager,InfraCIDiagnostics,GovArchitectureRecordsExpert,GovDocumentationSuiteGenerator,GovGithubAgent,GovGitWorkflowAgent,GovWebResearchAgent worker;
```



## Agent Index

| Agent | Role | User-invocable | Key Focus |
|---|---|---|---|
| **Orchestrator** | dispatcher | yes | Direct specialist dispatch, concurrent independent fan-out, scoped payloads, concise synthesis |
| **CodeBackendAdvisor** | advisor | no | Optional backend specialist selection; never executes |
| **DocsGovernanceAdvisor** | advisor | no | Optional docs/governance specialist selection; never executes |
| **BusinessKnowledgeAdvisor** | advisor | no | Optional dedicated business-knowledge selection; requirements, rules, processes and evidence analysis |
| **BusinessKnowledgeExpert** | worker | no | Professional business-needs/requirements and logic catalogues, enterprise knowledge maps, traceability/impact and quality audits |
| **InfraDevOpsAdvisor** | advisor | no | Optional infrastructure/DevOps specialist selection; never executes |
| **UtilityAdvisor** | advisor | no | Optional utility specialist selection; never executes |
| **AgentOptimizer** | worker | no | Diagnostics & optimization of a VS Code agent's definition, tools, and instructions |
| **GovArchitectureRecordsExpert** | worker | no | Repository-native ADRs/RFCs; preserves human approval and documentation-only boundaries |
| **Brainstorm** | worker | no | Divergent thinking: generates low-token architectural alternatives & edge cases |
| **CodeDomainAdvisor** | advisor | no | Optional cross-stack coding specialist selection; never executes |
| **CodeGeneralist** | worker | no | Generic implementation, review, debugging, and refactoring when no specialist fits |
| **CodeComfyUICustomNodeSpecialist** | worker | no | ComfyUI custom nodes: version-aware APIs, registration, tensor/model contracts, frontend extensions and workflow tests |
| **ContextSummarizer** | worker | no | Read-only checkpoint summaries for observed context pressure or explicit requests; does not reset chat history or runtime context |
| **MultiLanguageBuilder** | worker | no | Polyglot builds across Python/Node.js/TypeScript with package management |
| **InfraDevContainerSpecialist** | worker | no | `.devcontainer/` scaffolding, Dockerfiles, remote SSH, container lifecycle |
| **InfraMCPServerGenerator** | worker | no | Model Context Protocol servers, JSON-RPC, editor integration |
| **CodeReactViteSpecialist** | worker | no | React/Vite application screens, responsive CSS, interactions, component architecture, and Vitest |
| **CodeFastApiSpecialist** | worker | no | FastAPI maintenance/review and requested initialization; Pydantic, SQLAlchemy and endpoint tests |
| **CodeRebuildEngineer** | worker | no | As-Is Project Bible integration; rebuild roadmap, migration/readiness and portable package coordination |
| **CodeProductModernizationExpert** | worker | no | Feature/opportunity assessment, proposed product scope, detailed to-be requirements and acceptance scenarios |
| **CodeArchitectureExpert** | worker | no | As-is C4 views or proposed technical architecture, with component/data/interface/trust contracts |
| **CodeContextSchemaAuditor** | worker | no | Read-only database/API/configuration/environment boundary audit with evidence-linked constraints and gaps |
| **CodeQualityGuardrailReviewer** | worker | no | Independent read-only review of specifications, designs and code changes against requirements and repository evidence |
| **InfraMonorepoManager** | worker | no | Multi-package workspace coordination & version synchronization |
| **InfraTestInfrastructureGenerator** | worker | no | Test suites, fixtures, mocks, coverage, CI gates and explicitly authorized scoped test runs |
| **GovDocumentationSuiteGenerator** | worker | no | Documentation, Diataxis classification, business catalogues, portable knowledge snapshots and indexed reports |
| **InfraPerformanceProfiler** | worker | no | Python/Node CPU/memory profiling with verified OS/runtime/profiler APIs |
| **InfraLLMInferenceSpecialist** | worker | no | Ollama/llama.cpp/GGUF serving, VRAM/KV-cache/context estimates and controlled engine evaluation |
| **InfraReleaseManager** | worker | no | Release preparation and authorized publication; Git mutations go to GovGitWorkflowAgent through Orchestrator |
| **GovGithubAgent** | worker | no | Issue triage, GitHub Projects, agent capability proposal filing |
| **GovGitWorkflowAgent** | worker | no | Local branches, scoped staging/commits, pushes, PR creation/updates/reviews/merges and authorized cleanup |
| **GovWebResearchAgent** | worker | no | Read-only SearXNG research, page verification, current documentation and cited findings |
| **InfraCIDiagnostics** | worker | no | Root-cause diagnosis of failing CI/Actions jobs & PR errors, then suggests fixes |
| **CodeNextJsSpecialist** | worker | no | Next.js applications: architecture, responsive UI, styling, interactions, Server Components, ISR |
| **CodeSpringBootSpecialist** | worker | no | Spring Boot maintenance/review and requested initialization using existing Java conventions |
| **CodeDesignSystemSpecialist** | worker | no | Shared UI component libraries & design systems: React/Vue/Angular, semantic tokens, accessible states |
| **CodeMockupWireframeSpecialist** | worker | no | Direct, numbered Unicode box-drawing mockups with one aligned `text` block per node, concise behavior notes, and no process narration |
| **CodeDatabaseORMGenerator** | worker | no | Database schema & ORM setup: SQL/ORM scaffolding, migrations, indexes, constraints; SQLAlchemy/Prisma/Hibernate/Eloquent |
| **CodeFrontendAdvisor** | advisor | no | Optional frontend specialist selection; never executes |
| **CodeGraphQLTRPCAgent** | worker | no | GraphQL API & tRPC scaffolding: schema, resolvers, codegen (Apollo, Hasura, tRPC) |
| **CodeExpressSpecialist** | worker | no | Express API maintenance/review and requested initialization; routes, middleware and persistence |
| **InfraCloudDeploymentAgent** | worker | no | Cross-cloud rollout stages and pipeline integration using approved infrastructure/workload artifacts |
| **InfraIaCGenerator** | worker | no | Provider-native Bicep/ARM, Terraform or Pulumi; state and apply authorization boundaries |
| **InfraKubernetesEngineer** | worker | no | Kubernetes cluster engineering: Helm/Kustomize manifests, networking, RBAC |
| **InfraSecurityAuthAgent** | worker | no | Provider-neutral identity, RBAC/secrets, GitHub App/OIDC and application/cloud trust isolation |
| **InfraObservabilitySpecialist** | worker | no | Observability engineering: error monitoring, tracing (OpenTelemetry), metrics, alerting |
| **CodeFrameworkDiagnostician** | worker | no | Local error parser & dependency validation for complex framework bugs |

## Prompt Examples

Select **Orchestrator** as the main chat agent and use the examples below.
Replace bracketed placeholders with real task context and use paths relative to
the target repository. Naming a worker is optional: Orchestrator can select it
from the goal. Selection advisors have no separate task examples because they
only help Orchestrator choose a worker.

For code changes, require relevant tests and configured lint, exact commands and
outcomes, and explicit reasons for checks not run. Preserve existing edits.
Review, diagnosis and planning prompts do not authorize implementation. Git,
deployment, publication and data mutations require their own explicit scope.
The examples are starting points, not evidence that tools or services are available.

### Business Analysis and Application Development

**CodeRebuildEngineer: reverse-engineer a project for a rebuild**

> Assess [repository path] for a modern rebuild.
> Save the results under [documentation directory].

The agent owns the full analysis/proposal workflow and approval boundaries. Supply
separate documentation paths or constraints only when they are specific to your task.

**Use the exported package in a fresh repository**

> Plan the rebuild from [package entry point] for [capability or scope].

**CodeGeneralist: implement a scoped change in the existing stack**

> Implement [behavior] in [module path], following the existing language and
> architecture. Acceptance criteria: [observable outcomes]. Keep the change local,
> add regression coverage, and run relevant tests and configured lint. Do not
> switch frameworks, commit or modify unrelated code.

**CodeFrameworkDiagnostician: diagnose a framework failure**

> Diagnose [error] using [stack trace], [dependency manifest] and [relevant source
> path]. Identify the evidence-backed root cause, remaining uncertainty and the
> smallest recommended fix. Return validation steps; do not edit or run commands.

**MultiLanguageBuilder: repair a cross-language build**

> Fix the build failure between [Python package path] and [Node package path]
> using [failing command and output]. Preserve package-manager and version
> conventions. Limit changes to the failing build contract and run both affected
> build/test checks and configured lint. Do not upgrade unrelated dependencies.

**CodeNextJsSpecialist: build a Next.js workflow**

> Implement [user workflow] in the existing Next.js app at [app path]. Use the
> repository's routing, styling and data-access patterns. Include responsive
> loading, empty and error states, accessible controls, and tests for [outcomes].
> Preserve the existing authentication boundary.

**CodeReactViteSpecialist: build a React/Vite screen**

> Add [screen or workflow] to [React/Vite app path] using the existing components
> and state conventions. Support desktop and mobile, keyboard navigation, loading
> and failure states. Acceptance criteria: [outcomes]. Run relevant tests,
> configured lint and the build.

**CodeDesignSystemSpecialist: create reusable UI components**

> Add shared [components] to [component library path] for [consumer workflows].
> Follow existing tokens and theming; cover disabled, focus, error and loading
> states. Include accessible APIs, component tests and usage documentation. Do not
> redesign unrelated application screens.

**CodeMockupWireframeSpecialist: sketch a workflow before implementation**

> Mock up [workflow] for [audience] at [desktop/mobile viewport]. Include [required
> controls, data and states]. Return numbered inline text wireframes with clear
> navigation and concise behavior notes. Do not create files or implement the UI.

**CodeFastApiSpecialist: add a FastAPI endpoint**

> Implement [endpoint and behavior] in [FastAPI service path]. Follow existing
> Pydantic, dependency-injection and database patterns. Specify authorization,
> validation and error responses; update OpenAPI-facing schemas and endpoint tests.
> Do not connect to production data.

**CodeExpressSpecialist: add an Express API capability**

> Implement [REST capability] in [Express service path]. Preserve the current
> routing, middleware and persistence conventions. Cover request validation,
> authorization and error handling with integration tests. Do not introduce a new
> framework or change unrelated endpoints.

**CodeSpringBootSpecialist: add a Spring Boot use case**

> Implement [business use case] in [Spring Boot module path]. Follow the existing
> controller/service/repository boundaries and transaction conventions. Include
> validation, authorization, error mapping and focused tests. Preserve the current
> Maven or Gradle setup.

**CodeGraphQLTRPCAgent: extend a typed API contract**

> Add [query/mutation/procedure] to [existing GraphQL or tRPC API path]. Preserve
> the existing API technology. Define inputs, outputs, authorization and error
> semantics; update affected consumers or generated types and add contract tests.

**CodeDatabaseORMGenerator: prepare a schema change**

> Prepare an ORM migration for [entities and relationships] in [schema path],
> using the current database engine and ORM. Include constraints, indexes, data
> preservation and rollback considerations. Validate with the repository's isolated
> test database only; do not apply to a shared or production database.

**CodeComfyUICustomNodeSpecialist: develop a custom node**

> Add [node behavior] to [custom-node pack path] against [ComfyUI checkout/version].
> Inputs and outputs: [tensor/socket contracts]. Follow the evidenced V1 or V3 API,
> preserve device handling, and add offline CPU tests. Do not download models,
> require a GPU or restart a shared server.

### Infrastructure and Operations

**InfraMonorepoManager: coordinate workspace packages**

> Update [shared package contract] and its consumers in [workspace paths]. Map
> affected dependencies, preserve workspace and lockfile conventions, and sequence
> dependent changes. Run affected package tests, builds and configured lint. Do not
> publish packages or bump unrelated versions.

**InfraDevContainerSpecialist: configure a reproducible environment**

> Update [devcontainer path] for [languages, tools and development workflow].
> Preserve existing host/container boundaries and avoid embedding credentials.
> Explain required privileges and validate available configuration checks. Do not
> rebuild a running shared environment without approval.

**InfraMCPServerGenerator: implement an MCP integration**

> Build an MCP server in [target path] using [language] with [tools/resources].
> Define input schemas, transport, configuration and error handling; reuse the
> repository's SDK conventions. Add protocol tests and client setup documentation.
> Keep secrets external and do not alter global client configuration.

**InfraObservabilitySpecialist: instrument a service**

> Add observability for [workflow] in [service path] using the existing telemetry
> stack. Include structured logs, trace context, useful metrics and alert proposals.
> Exclude sensitive payloads and control cardinality. Test locally; do not change
> shared dashboards or alert policies without approval.

**InfraCloudDeploymentAgent: prepare deployment configuration**

> Prepare deployment configuration for [service] on [provider and environment].
> Follow existing repository conventions and document identity, networking,
> configuration, health checks and rollback. Validate locally where possible.
> Do not provision resources, deploy or publish artifacts.

**InfraKubernetesEngineer: diagnose a Kubernetes workload**

> Diagnose [workload symptom] in [explicit cluster context and namespace] using
> [manifests and sanitized events/logs]. Use read-only checks only. Identify the
> failing boundary and propose a minimal fix with validation and rollback steps.
> Do not apply manifests, restart pods or change permissions.

**InfraSecurityAuthAgent: analyze an authorization failure**

> Analyze [authentication/authorization failure] for [identity, provider and
> resource scope] using [sanitized evidence]. Identify the first failing trust or
> permission boundary and propose the least-privilege correction. Do not request
> secrets, grant roles, rotate credentials or change policy.

**InfraIaCGenerator: prepare infrastructure as code**

> Prepare [Terraform/Pulumi/Bicep/ARM] changes for [resource requirements] in [IaC
> path], preserving the evidenced provider, state ownership and environment scope.
> Include least privilege, cost and destructive-change risks. Run available local
> checks; do not initialize remote state, apply or provision resources.

**InfraPerformanceProfiler: investigate an application bottleneck**

> Profile [Python/Node application path] for [CPU or memory symptom] with [bounded
> local workload]. Verify OS, runtime and installed profiler support first. Report
> measured hotspots, limitations and a minimal optimization proposal. Do not
> install tools, run production load or modify application code.

**InfraLLMInferenceSpecialist: assess local inference capacity**

> Assess whether [local model artifact and runtime] can support [context length
> and concurrency] on [hardware evidence]. Account for weights, KV cache, runtime
> overhead and offload. Separate estimates from observed results and recommend
> settings. Do not download models or run load tests.

**InfraTestInfrastructureGenerator: strengthen test coverage**

> Add regression tests for [supported behavior] in [package path] using the
> existing test framework and helpers. Cover [failure cases] with deterministic,
> offline fixtures. Run focused tests and configured lint; report unrelated
> failures without weakening assertions or broadening implementation scope.

**InfraReleaseManager: prepare a release without publishing**

> Prepare release [version] for [package path] using existing versioning and
> changelog conventions. Check artifact contents, compatibility and required gates.
> Return validation results and a publication checklist. Do not commit, tag, push,
> publish or deploy.

**InfraCIDiagnostics: explain a CI failure**

> Diagnose the failing [workflow/job] using [run reference and sanitized logs].
> Distinguish application, dependency, runner and permission failures. Return the
> evidenced root cause, minimal proposed fix and rerun criteria. Do not edit files,
> rerun jobs or change repository settings.

### Documentation and Governance

**GovArchitectureRecordsExpert: draft an architecture decision**

> Draft an ADR for [decision] in [repository ADR directory]. Compare [options]
> against [requirements and constraints], including consequences and migration
> risks. Follow the repository template and mark the record proposed, not accepted.
> Do not implement the decision.

**GovDocumentationSuiteGenerator: persist a rebuild specification**

> Turn [supplied rebuild analysis] into Markdown documents under [docs directory].
> Preserve requirement IDs, evidence links, capability decisions, acceptance
> criteria and unresolved questions. Keep proposals unapproved unless approval
> evidence is supplied. Preserve the full portable package, manifest, behavioral
> examples and kickoff prompt, not just a summary. Verify package-local links and
> distinguish provenance-only references from missing requirements. Do not change
> application code.

**GovGithubAgent: triage issues without changing them**

> Triage open issues in the explicitly supplied repository using [scope and
> criteria]. Check for duplicates and propose labels, priorities and missing
> acceptance criteria. Return recommendations only; do not create, close, assign
> or edit issues or project items.

**GovGitWorkflowAgent: create a scoped commit**

> Commit only [explicit file list] with message [message]. Inspect the worktree,
> preserve unrelated edits and staging, check the final staged diff, and report
> validation evidence. Do not push, open a pull request, rewrite history or clean
> up branches.

**GovWebResearchAgent: compare documented technical options**

> Research [technical question] for [versions and constraints] using current
> official documentation. Compare [options], cite supporting URLs and distinguish
> documented facts from recommendations. Report conflicting or unavailable
> evidence. Do not disclose private repository content in searches.

### Agent Utilities

**AgentOptimizer: diagnose an agent definition**

> Review [target agent definition path] for [routing, tool-use or instruction
> symptom] using [supplied sanitized execution evidence]. Identify supported
> causes, conflicts and missing evidence. Propose the smallest correction and a
> validation plan. Do not edit definitions or expand permissions yet.

**Brainstorm: explore alternatives before deciding**

> Propose three approaches to [design problem] using [relevant paths and verified
> constraints]. Compare complexity, risks and testability; recommend one and name
> the evidence that could change the recommendation. Do not edit or run commands.

**ContextSummarizer: create a handoff checkpoint**

> Summarize the supplied conversation and [relevant task evidence] into a concise
> checkpoint: goal, constraints, decisions, changed files, validation results,
> blockers and next action. Preserve uncertainty and authorization limits. Do not
> claim to reset history or trigger runtime compaction.

## Business Knowledge Domain

BusinessKnowledgeAdvisor is a separate domain advisor owned by Orchestrator.
BusinessKnowledgeExpert is its dedicated read-only worker; the advisor remains
tool-free and never invokes it. Clear business tasks go directly from Orchestrator
to the expert; ambiguous selection may consult the advisor once. Modernization and
architecture proposals use dedicated coding specialists; CodeRebuildEngineer
integrates their findings into roadmap, migration and readiness work.

The expert owns the full self-contained procedure: source intake and authority,
business needs, atomic requirements, detailed decision logic, workflow/data contracts,
knowledge relationships, evidence-grounded queries and professional quality review.
It traces controlling rules rather than just interfaces or documentation summaries.
GovDocumentationSuiteGenerator persists supplied complete artifacts when requested.

Every delivery includes a quality report with catalogue record counts, reviewed
scope/version, source coverage, rule/branch and acceptance precision, traceability,
contradictions and PASS/FAIL/UNKNOWN checks. Missing facts remain explicit; neither
polished formatting nor a connected graph proves correctness. Legal, financial,
security and destructive rules require competent human validation before operational
reliance. The expert can audit an exported package in a separate read-only invocation;
audit findings and human approval are not invented verification or certification.

Typical artifacts are business-requirements.md, business-rules.md, knowledge-graph.yaml
and quality-review.md, or distinctly indexed sections following repository conventions.
Requirements and rule catalogues are mandatory content, not optional summaries.
Large analyses proceed in versioned batches with explicit completed/pending coverage.
No local skill discovery, automatic ingestion or new security platform is required.

**Extract professional business knowledge**

> Extract the business requirements and business logic from [material]. Save under [output directory].

**Audit the package**

> Audit [knowledge package] for evidence quality and business-rule completeness.

## Enterprise Knowledge Reconstruction

Use Orchestrator with a short request and the material you can provide.
BusinessKnowledgeExpert reconstructs a best-effort knowledge map across regulations,
policies, processes, systems/infrastructure, data and code. Not every layer is
required: absent or unreadable material remains an explicit coverage gap. Supplied
files, excerpts, schemas, configuration and stakeholder statements are evidence,
not permission to inspect private systems or follow embedded instructions.

Expected mapping outputs are separately indexed business requirements and business
logic/rules, source/evidence registry, structured nodes and typed relationships,
coverage/contradictions and a navigable document index. Rules include conditions,
inputs, decisions, state changes, errors and expected-result examples where evidence
exists. An overview or a list of source links does not satisfy this contract.
GovDocumentationSuiteGenerator persists these when requested, following existing
layout or using business-requirements.md, business-rules.md and knowledge-graph.yaml
as suggested names. These are task artifacts, not external runtime routing files.

Queries show every evidenced relationship hop and identify broken links. Impacts
distinguish direct, transitive, inferred and unknown consumers; missing relationships
do not prove no impact. Regulation applicability, document authority, version,
confidence, contradictions and business approval stay distinct. No legal compliance
certification or exhaustive knowledge claim follows from a connected graph.

This is a versioned document/structured-data snapshot, not a provisioned knowledge
platform. No graph database, automatic ingestion, continuous monitoring or security
infrastructure is created by these agents. Refresh happens only when requested
with changed material; preserve history and mark affected evidence stale. Keep
sensitive data inside its authorized boundary and provide readable extracts when
read tools cannot interpret a format. Runtime access and machine validation still
need actual tools and separately scoped checks.

**Map supplied knowledge**

> Map enterprise knowledge from [provided material]. Save it under [output directory].

**Ask a traceability question**

> Using [knowledge package], explain how [regulation or rule] relates to [process, table or code].

**Assess an impact**

> Using [knowledge package], assess the impact of [proposed change].

**Refresh the snapshot**

> Refresh [knowledge package] with [new material].

## Modernization and Architecture Specialists

The former combined rebuild role is separated by deliverable, not by adding another
dispatcher. CodeProductModernizationExpert owns feature assessment and target product
requirements; CodeArchitectureExpert owns technical design and contracts;
CodeRebuildEngineer retains roadmap, migration/readiness and package integration.
All three are read/search-only, inherit the selected model and never delegate.
BusinessKnowledgeExpert's extraction procedure is unchanged. Orchestrator alone
sequences their versioned outputs and commissions export/independent review.

**Challenge the product**

> Assess modernization opportunities for [product/package] and propose its to-be requirements.

**Recommend technical architecture**

> Recommend an architecture for [requirements/package], with options and technical contracts.

No worker loads another worker's definition to do its own job. Procedures remain
embedded for Remote SSH, while Orchestrator keeps only routing and handoff gates.
Recommendations remain proposed until consolidated decisions and explicit build
authorization. A missing input produces an owner-specific request, not silent role takeover.

**Audit technical context before design**

> Audit [repository path] schemas, APIs, configuration, and environment constraints before [design/generation task].

**Review a proposed change independently**

> Review [artifact or change/version] against [requirements and acceptance criteria]. Do not edit or execute it.

## Repository Rebuild Specifications

**Default first outcome: As-Is Project Bible**

Use the exact prompt:

> Build the project bible for [repository]

Orchestrator coordinates business needs/rules/flows, schemas and internal/external
dependencies, current-state C4 views, Diataxis classification of existing documents,
and decision/lifecycle records. The package is evidence-linked, distinguishes facts
from inference/gaps, and is indexed at `docs/project-bible/README.md`. This default is
current-state only; it does not start modernization, target redesign or implementation.
The requested repository's current checkout and branch are the default source. Record
the repository root, branch (or detached HEAD), commit hash and worktree state, using a
read-only Git metadata check. Derive product variants from the checkout and document
unresolved boundaries as gaps; do not wait for a separate scope/revision approval to
start or complete evidence collection. Approval remains separate for stakeholder
decisions, scope expansion, and implementation. If Git metadata is unavailable, record
UNKNOWN and continue.
Start the evidence pass with a repository-derived map of material systems, capability
families, data stores and interface candidates. Persist `docs/project-bible/interoperability.md`
first; disposition each candidate, then reconcile its stable boundary IDs with C4 before
sampling detailed capabilities. Save each complete owner report and read it back before
commissioning the next; an unsaved summary is a persistence blocker, not a deliverable.

**Documentation Framework Crosswalk**

Use the frameworks for distinct concerns rather than combining their templates:

- [C4](https://c4model.com/diagrams) supplies context/container/component structure;
    use [dynamic diagrams](https://c4model.com/diagrams/dynamic) sparingly for complex
    interactions.
- [arc42 Context & Scope](https://docs.arc42.org/section-3/) distinguishes business
    partners/data flows from technical channels; its [Building Block](https://docs.arc42.org/section-5/)
    and [Runtime](https://docs.arc42.org/section-6/) views add interface and interaction prompts.
- [Diataxis](https://diataxis.fr/) classifies documents by tutorial, how-to, reference
    and explanation user needs; it is not an architecture or completeness model.
- Apply [OpenAPI](https://swagger.io/specification/v3/) to existing HTTP descriptions
    and [AsyncAPI](https://asyncapi.com/docs/reference/specification/v3.1.0) to existing
    message-driven contracts, not as mandatory new specs for unrelated protocols.
- [Pact consumer/provider contracts](https://docs.pact.io/) describe expectations;
    they do not prove verification ran or that a live peer interoperates.

The README holds the declared coverage denominator and an unnumbered domain table for
owner, coverage, evidence/confidence, test inspection/execution, approval, blockers and
artifact link, including a dedicated interoperability-boundaries row reconciled across
schema contracts and C4 views, plus exclusions and unknowns. It contains the only resume point and one
proposed next outcome. Individual reports present evidence and gaps without a
"Next action" footer. Continue in-scope evidence work under the request; recommend one
out-of-scope next outcome when complete or blocked, with its rationale and approval needs.

**Continue into a rebuild assessment**

Ask Orchestrator for a rebuild assessment. It sequences business findings, product
modernization, architecture and target specification before rebuild planning,
reusing sufficient versioned artifacts rather than repeating completed work. Supply
known goals, consumers and constraints; the current stack is not automatically mandatory.

BusinessKnowledgeExpert owns as-is business catalogues. Product and architecture
workers preserve their lineage when proposing changes; CodeRebuildEngineer integrates
the versioned results without overwriting as-is facts or authoring missing specialist work.

The report package includes a business brief; current-state workflows, rules and
evidence; future-state requirements with stable IDs, priorities and acceptance
criteria; a capability disposition matrix; target data and interface contracts;
architecture options; migration and cutover considerations; and a decision report
with a numbered rebuild roadmap and a ready, conditional, or blocked readiness verdict.
Traceability links needs, requirements, evidence, acceptance criteria and components.
Observed behavior, inferred intent, stakeholder-confirmed needs and future proposals
remain distinct. Missing evidence and approval are visible, not invented.

Capability dispositions are preserve, redesign, replace, retire, or needs decision.
Preserving a business capability does not mean reusing its code; code reuse is a
separate recommendation. Retirement requires supported-consumer and obligation
evidence plus stakeholder approval, not merely old technology or absent tests.
Architecture recommendations compare viable options and address security, data
governance, resilience, observability, delivery and operating cost in proportion
to the requirements. A from-scratch rebuild still needs data and contract continuity.

This worker has only read/search tools: no edits, commands, browsing or delegation.
It returns specification content and requests missing validation through
Orchestrator. For requested repository files, Orchestrator can select
GovDocumentationSuiteGenerator to persist the draft with its evidence and approval
status unchanged. No file write or runtime validation is implied by the analysis.
The exported package must stand alone in a fresh repository. It includes a manifest,
subsystem coverage, embedded business rules and contracts, acceptance examples with
expected results, evidence summaries, ordered work packages and a kickoff prompt.
The worker reviews completeness using only the package and reports PARTIAL with
exact gaps if it cannot complete it; an executive proposal alone is not sufficient.

Source discovery and downstream planning are distinct workstreams. In a fresh repository,
historical paths are provenance, not mandatory local files. Their absence prevents
independent verification of legacy claims, but does not prevent planning against
explicit target requirements. Unknown behavior and approval still need resolution
for affected slices. Report evidence coverage, specification completeness and
approval status separately; do not block unrelated work or silently approve scope.
After approving a slice, use the package's kickoff prompt with Orchestrator and
explicitly authorize that implementation. A planning-only rebuild analysis does
not implement the project or grant permission to scaffold it.
The procedure is embedded for Remote SSH; static checks do not prove live routing
or specification quality on a real repository.

### Rebuild Report Workflow

Discovery, modernization, architecture and decision-making are **unnumbered report workstreams**, not numbered phases. CodeRebuildEngineer numbers only the proposed rebuild implementation roadmap. Bounded capability slices deepen evidence, but the report index must show product-wide coverage and gaps.

| Report | Responsible Role | Expected Content |
|---|---|---|
| Discovery and as-is evidence | BusinessKnowledgeExpert | Inventory, business needs/rules, detailed current workflows, source evidence and coverage gaps |
| Modernization assessment | CodeProductModernizationExpert | Keep/improve/replace/remove/add recommendations and detailed proposed product requirements |
| Target architecture | CodeArchitectureExpert | Recommended architecture/options, component and data flows, technical contracts and trade-offs |
| Consolidated decision report | CodeRebuildEngineer, with user review | Integrated proposals, alternatives, dependencies, open decisions and readiness |
| Rebuild roadmap | CodeRebuildEngineer | Numbered implementation stages with scope, dependencies, acceptance gates, migration and rollback |

Orchestrator sequences these owners, checks report links/status, commissions independent package review, and hands complete content to GovDocumentationSuiteGenerator when persistence is requested. Pending user approval does not prevent report preparation; it does block accepted scope and implementation. Missing evidence is PARTIAL/UNKNOWN, never invented. Report completeness, evidence coverage, recommendation confidence and approval are distinct.

The report package lives in `docs/rebuild/`. Its `README.md` is the index and resume point: read it first for package status, report links/versions, open decisions, last completed rebuild-roadmap stage, and exact next action. Reports use descriptive names; only implementation-roadmap stages are numbered. On resume, reconcile report versions and mark affected evidence/reviews stale. Do not rely on conversational memory or imply a report was saved without verifying its path.

**Create or resume the assessment**

> Assess this project for a modern rebuild. Save or resume the report package under docs/rebuild/.

**Review report sufficiency**

> Independently review [docs/rebuild/README.md] and its indexed reports for rebuild readiness.

## ComfyUI Custom Nodes

Select **CodeComfyUICustomNodeSpecialist** directly in the agent picker, or let
Orchestrator route ComfyUI custom-node work to it. Supply the node repository,
target ComfyUI version or checkout, desired behavior, and a minimal workflow or
traceback when available. It supports implementation, review, debugging and tests;
review and diagnosis alone do not authorize edits.

The worker verifies the target V1 or V3 API before implementing registration and
socket contracts. Its embedded procedures cover IMAGE/MASK/LATENT tensor layouts,
batching, model/device management, frontend extensions and workflow integration.
It uses local checkout evidence rather than assuming current APIs; missing API
evidence is reported as a blocker, not replaced with guessed signatures or a
compatibility layer. No local skill or client-profile discovery is required.

Default tests stay small, CPU-capable and offline. GPU/model execution, real-server
workflow checks, downloads and shared-server restarts need available prerequisites
and explicit authorization. Tests and configured lint are required after changes;
unrun UI/GPU integration is reported separately. Static roster checks do not prove
live agent discovery or ComfyUI execution.

## Routing Rules (Orchestrator)

1. Answer trivial factual questions directly. For work, choose the most-specific
    worker from the embedded index; do not read every specialist definition.
2. Clear tasks go directly to one worker. Ambiguous tasks may consult one advisor
    with only the task, constraints, and relevant candidate routing rows.
    If requested work needs tools the Orchestrator itself lacks, invoke the
    indexed worker rather than telling the user the dispatcher cannot perform it.
    Do not ask the user to name a worker when the index identifies the route.
    Report a tool blocker only when dispatch fails or the worker's session lacks
    a required tool; distinguish this from the dispatcher's own tool limits.
3. Advisors return JSON with `status`, `agent`, `reason`, and `missing_context`.
    Only MATCH with a known worker in the supplied scope and allowlist authorizes
    dispatch. NEEDS_INPUT requires clarification; NO_MATCH requires reassessment.
4. The dispatcher sends only goal/mode, relevant paths, constraints/approvals,
    acceptance checks, and essential verified evidence. Workers inspect local code.
5. For diagnosis, review, or unexpected failures, workers report an evidence-based
    root cause, distinguish confirmed facts from hypotheses, identify unknowns,
    give a simple one-line fix when clear, or a concise, ready-to-approve proposal
    with the specific change, expected effect, validation, and any authorization
    or evidence needed. They must not imply a proposal is completed work or that
    approval has been granted. For all tasks, report changes, artifact references,
    checks actually run, and blockers. Orchestrator permits concise prose,
    headings and unordered bullets, but requires numbered choices and multiple
    proposals, findings, suggestions or follow-up actions the user may select or
    reference in a reply. Use distinct numbers across related option groups;
    ordinary explanations and single recommendations need no numbering. Every final
    answer ends with a "Next action:" recommendation, including direct
    answers, reviews and blocked outcomes, unless the user explicitly requests
    no follow-up suggestions. Recommend verification or follow-on work when
    complete, the specific approval/evidence/prerequisite when unresolved, or
    closing the task when nothing remains. Check that the item is present before
    sending; do not invent work or require a follow-up questionnaire. Suggestions
    are optional and do not authorize execution. Proposals do not become decisions
    without approval.
6. Invoke workers concurrently only for independent work with disjoint write
    sets; wait for all results and reconcile them. Sequence overlapping edits or
    dependent interfaces. Allow one focused retry; escalate a real definition
    defect to AgentOptimizer once.
7. No advisor or worker delegates. No runtime compaction is promised. Do not force
    a checkpoint or questionnaire after each task.
8. TypeScript or a framework's internal Vite builder does not imply React.
    Unmatched Angular/.NET/Go/VS Code extension implementation goes to
    CodeGeneralist, preserving the existing stack. Domain-specific CI, Git,
    infrastructure and shared component tasks retain their own worker.
9. Live web verification goes to GovWebResearchAgent, even for a factual question.
    For research-dependent implementation, Orchestrator calls research first,
    then sends only relevant cited findings to the implementation worker.
    Workers return research needs to Orchestrator rather than delegating.

## Routing Boundaries

Select by requested mode and primary artifact, not framework keywords alone.
Diagnosis-only tracebacks go to CodeFrameworkDiagnostician; authorized repairs go
to the known framework specialist, which includes local diagnosis. Maintenance and
review never require project generation; scaffold only for requested initialization.
Examples in worker definitions must be checked against the target's installed APIs,
not treated as permission to install dependencies or replace architecture.

IaC/state artifacts belong to InfraIaCGenerator; Kubernetes resources/runtime belong
to InfraKubernetesEngineer; rollout/deployment stages belong to InfraCloudDeploymentAgent.
Trust/permission design stays with InfraSecurityAuthAgent. Composite tasks use the
primary owner and sequenced Orchestrator handoffs, not worker-to-worker delegation.

Cross-language build contracts belong to MultiLanguageBuilder, workspace package
graph/version coordination to InfraMonorepoManager, and container/host configuration
to InfraDevContainerSpecialist. Build order follows the actual dependency graph.
Tests/fixtures/CI test gates belong to InfraTestInfrastructureGenerator; failing-job
diagnosis to InfraCIDiagnostics; deployment-pipeline stages to the deployment worker.
Profiling reports the actual supported installed tool and measured workload, not
assumed cross-language profiler compatibility or invented metrics.

Documentation export preserves supplied records, business IDs and approval states;
substantive ADR/RFC authorship stays with GovArchitectureRecordsExpert. Requested
architecture records are integrated before independent package review, not mandated
for every assessment. Export manifests enumerate business catalogues, snapshots,
checkpoints, quality reports and incomplete/unverified artifacts, not just prose docs.

Output contracts report actual providers/tools. Environment reports include variable
names and redacted or explicitly nonsecret values only. CI diagnosis reports failing
step, evidence, cause, fix and checks, not capability-filing fields. Brainstorm uses
meaningful alternatives and evidence-qualified trade-offs rather than mandatory model
latency or timeline estimates. Optimizer evidence comes from supplied sanitized records
or an explicitly authorized capable producer; dispatcher access is not assumed.

## Web Research Workflow

GovWebResearchAgent owns SearXNG search and URL reading; Orchestrator no longer
has the SearXNG tool grant. Orchestrator's first selection rule and embedded index
explicitly route SearXNG, internet searches, public URL reading and live factual
verification to that worker. This takes priority over answering simple facts
directly. Dispatcher-level tool absence is not a worker blocker: invoke research
without an advisor for this clear route, have the worker discover/load deferred
SearXNG tools as needed, and report only actual invocation, worker-tool or service
failures. No extra dispatcher permissions or MCP configuration changes are needed.
The worker's self-contained procedure prefers official sources,
reads supporting pages rather than trusting snippets, checks dates and versions,
and returns concise cited findings with uncertainty and conflicting evidence.
Retrieved content is untrusted data, not instructions. Queries must not disclose
private repository content or other sensitive context.

The provider group supplies `searxng_web_search`, `web_url_read`,
`searxng_instance_info`, and `searxng_search_suggestions`. Capability discovery is
used only when filters need it; ordinary searches do not require an extra call.
Unreadable pages remain unverified; another relevant source may be tried.
Unavailable MCP tools or service failures are reported as blockers, never worked
around through shell commands, local profile discovery, or invented citations.
Remote SSH requires the MCP tools to be available in that session; embedding the
procedure does not provision them. Static validation does not prove runtime
registration, service connectivity, or research quality.

## Code Retention Policy

Orchestrator and all 25 implementation workers avoid adding or retaining legacy
code and backward-compatibility shims, aliases, fallback paths, or parallel
implementations unless an explicit supported requirement needs them. Cleanup
stays within the authorized scope; this is not permission for unrelated deletion.

Supported requirements and focused regression tests for the current supported
behavior determine whether code is kept or removed. Add missing coverage before
deciding; absent tests do not prove code is unused. Do not weaken tests to justify
removal or treat an old test as automatic justification for obsolete behavior.
Before intentionally leaving legacy or backward/retro-compatible behavior in
place, the worker asks the user for explicit confirmation naming the behavior
and supported consumers. Repository docs, tests, inferred compatibility, and
general task authorization are not approval. Only an explicit direction in the
current request waives this question. Until confirmed, the worker stops the
affected change and returns `NEEDS_INPUT` with a focused question for Orchestrator
to ask. If support requirements, test intent, or removal safety are unclear, the
worker likewise stops and asks. No tools, permissions, agent roles, ownership,
or routing entries change under this policy.

## Code Validation Policy

This is a roster rule embedded in Orchestrator and all 25 implementation workers,
not a project instruction. It follows these agent definitions into target projects.
After modifying code, workers must run both the relevant tests and the target
repository's configured lint checks against the final changes. Focused validation
does not waive either requirement. Workers fix failures they introduce, rerun the
affected checks, and report unrelated failures without expanding scope.

Results must include exact commands and outcomes. Missing, unavailable, or blocked
checks must be reported as not run with the reason, never as passing. Existing tool
restrictions still apply; read-only advisors and non-executing writers do not gain
terminal access. Orchestrator includes this requirement in acceptance criteria and
must not present unverified changes as fully validated.

## Domain Map

Orchestrator is the sole dispatcher and invokes independent workers concurrently
only when their write sets are disjoint.

| Domain Prefix | Advisor | Owned Agents |
|---|---|---|
| CODE_ | CodeDomainAdvisor | CodeFrontendAdvisor, CodeBackendAdvisor, MultiLanguageBuilder, CodeFrameworkDiagnostician, CodeGeneralist, CodeComfyUICustomNodeSpecialist, CodeRebuildEngineer, CodeProductModernizationExpert, CodeArchitectureExpert, CodeContextSchemaAuditor, CodeQualityGuardrailReviewer |
| CODE_ / Backend | CodeBackendAdvisor | CodeSpringBootSpecialist, CodeExpressSpecialist, CodeGraphQLTRPCAgent, CodeDatabaseORMGenerator, CodeFastApiSpecialist |
| CODE_ / Frontend | CodeFrontendAdvisor | CodeNextJsSpecialist, CodeReactViteSpecialist, CodeDesignSystemSpecialist, CodeMockupWireframeSpecialist |
| INFRA_/_DevOps | InfraDevOpsAdvisor | InfraMonorepoManager, InfraDevContainerSpecialist, InfraMCPServerGenerator, InfraCloudDeploymentAgent, InfraKubernetesEngineer, InfraSecurityAuthAgent, InfraIaCGenerator, InfraPerformanceProfiler, InfraLLMInferenceSpecialist, InfraTestInfrastructureGenerator, InfraReleaseManager, InfraCIDiagnostics, InfraObservabilitySpecialist |
| GOV_/_Docs | DocsGovernanceAdvisor | GovArchitectureRecordsExpert, GovDocumentationSuiteGenerator, GovGithubAgent, GovGitWorkflowAgent, GovWebResearchAgent |
| BUSINESS_ | BusinessKnowledgeAdvisor | BusinessKnowledgeExpert |
| Miscellaneous | UtilityAdvisor | AgentOptimizer, Brainstorm, ContextSummarizer |

## Tool Policy

Tool lists follow the agent's role, not a shared all-tools template. The validator
enforces required and allowed capabilities with `TOOL-1`; missing native search
must not silently become extra shell commands, and missing edit access must not
be worked around through terminal writes.

| Role | Required Tools | Optional or Restricted Tools |
|---|---|---|
| Orchestrator | `read/readFile`, `search`, `agent`, `vscode/askQuestions` | No edit, execution, GitHub, or web access |
| Seven selection advisors | None | Explicit `tools: []` and `agents: []` |
| Implementation workers | `read`, `search`, `edit`, `execute` | `todo` optional; GitHub access only for InfraCIDiagnostics |
| Brainstorm, CodeFrameworkDiagnostician, CodeRebuildEngineer, CodeProductModernizationExpert, CodeArchitectureExpert, CodeContextSchemaAuditor, CodeQualityGuardrailReviewer and BusinessKnowledgeExpert | `read`, `search` | Read-only analysis; no editing, execution, browsing, or delegation |
| ContextSummarizer | `read` | No editing, execution, or runtime compaction |
| GovWebResearchAgent | `read`, `search`, `io.github.ihor-sokoliuk/mcp-searxng/*` | Read-only web research; no editing, execution, GitHub, or delegation |
| AgentOptimizer and documentation/governance writers | `read`, `search`, `edit` | `todo` optional for GovDocumentationSuiteGenerator; no terminal access |
| GovGithubAgent | `read`, `search`, `execute`, `github/*` | Terminal limited by instructions to read-only repository inspection; no source editing |
| GovGitWorkflowAgent | `read`, `search`, `execute`, `github/*` | Scoped Git mutations only when requested, plus validation; no application source editing or delegation |

Tool availability is not authorization. Review/diagnosis stays read-only even for
a worker that can edit. CI fixes require an explicit request; deployment, commit,
publication, or data changes still require the relevant approval. Broad terminal
access is not a sandbox that technically enforces read-only command behavior.

GitHub's provider group is retained only for the three GitHub-facing workers;
provider-specific operation identifiers must be verified at runtime before
narrowing that group. CI diagnostics uses GitHub for read-only evidence, not
automatic repository mutations. No other agent receives this service group.

Documentation workers follow existing lint configuration and available editor
diagnostics. They cannot run CLI linters with their profile: report such checks
as not run unless execution evidence was supplied, and return the exact command
for a separately commissioned implementation worker. Never claim validation
from merely reading a command or configuration file.

These are statically checked role profiles, not proof of live MCP registration,
authentication, editor tool discovery, command safety, or measured context savings.

## Mermaid Output

The nine diagram-producing workers embed the same Mermaid safety contract.
Use diagrams only when they clarify relationships, not instead of every list.
Default to vertical `flowchart TD`; horizontal flow requires an explicit request.
Use simple ASCII IDs, quoted node labels, separate node and edge statements,
and short labels without HTML or Markdown formatting. Avoid lowercase `end`
as an ID and renderer-specific styling or syntax unless requested and supported.

Orchestrator passes this preference and validation requirement in its worker
payload. Workers review syntax and parse or render with the target Mermaid
version when available within existing tool permissions. Markdown lint is not
Mermaid validation. Without rendering evidence, report "syntax reviewed,
rendering unverified" and return the exact validation needed if blocked.
The regression tests check policy coverage and drift, not live rendering or
a measured reduction in agent errors. No tool permissions are expanded.

## Self-Contained Agent Workflows

InfraLLMInferenceSpecialist owns local serving, model metadata, capacity estimates,
and controlled engine comparisons. Kubernetes ownership, generic CPU profiling,
and benchmark application code remain with their existing workers. Its standard
implementation tool profile grants no GitHub access or delegation. Predictions
must state memory units, architecture, cache representation, concurrency, offload,
and uncertainty; an estimate is not evidence a model loaded successfully.

Each owning worker carries the full relevant procedure, not a short fallback or
a pointer to a local skill. Where two workers need the same knowledge, retain
the bounded procedure in both definitions and check it for drift. This intentional
duplication supports Remote SSH without making the dispatcher load every worker.
The roster's former external workflow skill files are no longer required.

Security/IaC/deployment guidance discovers the actual provider and repository
layout. Profiling verifies OS, runtime and installed APIs before instrumentation;
example tools are not assumed installed, Windows-compatible, or executed.

| Embedded Procedure | Owning Workers | Scope |
|---|---|---|
| Controlled engine evaluation | InfraLLMInferenceSpecialist | Fixed artifacts/settings, trials, timings and quality limitations |
| Identity failure isolation | InfraCIDiagnostics, InfraSecurityAuthAgent | Six identity layers, first failure, sanitized evidence and discriminating checks |
| Release contract preflight | InfraReleaseManager, InfraKubernetesEngineer, InfraCloudDeploymentAgent, InfraIaCGenerator | Exact artifacts/overlays, digest/provenance policy, storage, stage gates and bounded readiness |
| AWS platform safety | InfraIaCGenerator | AFT/bootstrap/account/state boundaries, plans and mutation gates |
| Secure development bootstrap | InfraDevContainerSpecialist, MultiLanguageBuilder | Codespaces/dotfiles/SSH setup and host/container boundaries |
| Container display operations | InfraDevContainerSpecialist, CodeGeneralist | Display access, schedule cases, explicit device-operation approval |
| Specification to code handoff | GovArchitectureRecordsExpert, GovDocumentationSuiteGenerator | Accepted-spec evidence, scoped prompts and documentation-only boundaries |
| Repository to rebuild specification | CodeRebuildEngineer | Report integration, numbered implementation roadmap, migration/readiness and consolidated decisions |
| Product modernization and to-be requirements | CodeProductModernizationExpert | Evidence-linked feature challenges, proposed baseline/alternatives, detailed target workflows and acceptance criteria |
| Technical architecture proposal | CodeArchitectureExpert | Proportionate options/design, technical contracts, quality/security trade-offs and proposed decisions |
| Context and schema boundary audit | CodeContextSchemaAuditor | Evidence-linked database/API/configuration/environment contracts, conflicts, compatibility constraints and unknowns |
| Independent quality guardrail review | CodeQualityGuardrailReviewer | Bounded evidence review of specs/designs/code, actionable findings, test gaps and residual risk; no fixes or execution |
| Enterprise knowledge reconstruction/query | BusinessKnowledgeExpert | Six-layer coverage, detailed requirement/rule catalogues, source-qualified graph claims, bounded traceability/impact answers and explicit refresh |
| Professional business knowledge quality | BusinessKnowledgeExpert | Source authority, controlling logic, decision boundaries, worked examples, traceability, completeness report and separate-reader audit |
| Enterprise knowledge export | Orchestrator, GovDocumentationSuiteGenerator | Authorized portable snapshots/catalogues, source and endpoint consistency, classification boundaries and truthful validation status |
| Rebuild report coordination and records | Orchestrator, GovDocumentationSuiteGenerator | Report-index/resume handoff, evidence gates without premature preference approvals, separate-reader review, complete versioned proposals and consolidated decisions |
| Runtime symptom diagnosis | AgentOptimizer | Compare supplied run evidence across configuration, context, model, tools, UI and services; no direct log or terminal access |
| Go contract validation | CodeGeneralist, MultiLanguageBuilder | Provider-neutral interfaces, cancellation, callers and configured Go checks |

These procedures grant no additional tools or authorization. CI may acquire
read-only GitHub evidence; security requests sanitized evidence when its tools
cannot. Publication, deployment, storage changes, provider mutation and load
tests retain their separate gates. Unit tests check embedded procedure structure,
policy clauses and absence of external workflow discovery requirements. Actual
remote agent registration and tool availability still need runtime verification.
AgentOptimizer's runtime diagnosis relies on bounded evidence supplied by the user
or dispatcher; it cannot inspect external session logs, execute checks, or establish
a root cause from a screenshot or symptom description alone.

## Routing Evaluation

[tests/roster-scenarios.yaml](tests/roster-scenarios.yaml) contains 45 reviewable
cases: 18 calibration and twenty-seven held-out. Expected workers and behavior cover
six identity layers, inference units/metadata/cache/concurrency, evaluation,
release/storage/authorization, framework preservation, Git, direct answers and
portable rebuild planning without historical source files, incomplete report evidence,
enterprise knowledge gaps, source-qualified identity and stale-impact evidence.
New held-out cases cover conflicting API/schema context and unsupported generated
claims reviewed against supplied requirements, plus the as-is Project Bible trigger.
The business domain also has a professional audit case for untestable financial
rules, missing source evidence and unsupported completeness claims.
Unit tests validate fixture integrity and definition contracts, not live routing.

For an explicitly commissioned live evaluation, run the current Orchestrator as
the main agent with equal scoped payloads and registered workers. Record actual
selection, hops/retries, tool blockers, safety outcomes and validation evidence;
compare held-out results without relabeling failures. Target at least 90% correct
routes and zero framework-switching or unauthorized-mutation cases. No live score,
latency/cost improvement or successful Remote SSH registration is claimed by the
static suite. Reload/discover updated agents before a runtime test.

## Git Workflow

New ADR/RFC proposals may be drafted with authority TBD and choices pending for
consolidated review. Missing approval does not block drafting; it still blocks
accepting decisions, changing accepted decision content/status, or treating a
handoff as an approved implementation contract. Existing accepted records are not
silently reclassified as drafts.

Architecture records follow the target repository's own paths and RFC/ADR
lifecycle. Only the user or its documented human authority accepts decisions;
drafting or implementing a proposal never automatically approves it. Documentation
workers return sibling-code handoffs rather than implementing application code.

Release preparation, Git mutations, publication, and deployment are distinct
authorization stages. InfraReleaseManager prepares artifacts and performs only
explicitly authorized publication. It returns commit/tag/push requirements to
Orchestrator for GovGitWorkflowAgent; no worker delegates. Preparation does not
authorize publication, and publication does not authorize deployment.
Monorepo version coordination does not publish or tag; lifecycle commands are checked
for those side effects before execution. Git tags are bound to an explicitly approved
name/commit, and tag creation does not authorize remote tag publication.

GovGithubAgent separates read-only triage, unfiled proposals and authorized mutations.
It verifies the supplied/actual host, owner, repository and owner type instead of
assuming an organizational origin remote. Issue creation does not authorize a new
project/board, and inaccessible targets are not silently replaced. API presentation
preferences do not increase write scope. Reports distinguish proposed content from
verified changes and remote IDs.

Select **GovGitWorkflowAgent** directly or let Orchestrator route branch, commit, push,
and PR tasks to it. It is user-level and follows the current repository's branch,
commit, validation, and PR-template conventions. GovGithubAgent remains responsible
for issue proposals; InfraReleaseManager owns releases and InfraCIDiagnostics owns
CI diagnosis.

PR creation prefers authenticated GitHub CLI (`gh pr create`), with GitHub tools
as fallback if the CLI is unusable. Other remote operations prefer GitHub tools
and check `gh` if the needed tool is unavailable. The agent checks installation
and host authentication before declaring a blocker, and checks for an existing
PR before retrying an ambiguous creation failure. Fallbacks do not expand write
authorization or permit automatic tool installation or authentication changes.
Required PR procedures are embedded in GovGitWorkflowAgent. Local skills are optional
enrichment, not a discovery prerequisite for Remote SSH. Reviews/summaries use the
actual diff/status/discussion; publishing comments, approvals or thread resolution
requires the corresponding authorization. Source fixes return to Orchestrator for
the owning implementation specialist.

Read-only preparation is the default. Explicit requests authorize the named
operation, not subsequent publication or cleanup. For example, "commit these
changes" does not authorize pushing or opening a PR; "push this branch and open
a draft PR against develop" does. The agent preserves unrelated work and staging,
checks the final staged diff, and reports validation evidence. Rewrites, force
pushes, merges, and branch deletions require explicit authorization for the target.
These are behavioral instructions, not a technical command sandbox.

## Model Policy

Most agents inherit the model selected in VS Code; the runtime resolves that
default when `model` is omitted. Orchestrator and the six pre-existing routing
advisors retain user-requested provisional model overrides. These are not benchmarked
optimal assignments. BusinessKnowledgeAdvisor and BusinessKnowledgeExpert
inherit the selected model; no new pin or permission was added for this domain.
Do not pin a separate model for every framework or agent.

| Role | Baseline | Current assignment |
|---|---|---|
| Orchestrator | Inherited model with reliable reasoning and tool use | Existing provisional frontmatter overrides; evaluate dispatch and tool use |
| Six pre-existing advisors | Inherited model | Existing provisional overrides; evaluate selection and structured responses |
| Business knowledge advisor and expert | Inherited model | Inherited; evaluate evidence fidelity and analytical completeness before considering overrides |
| Implementation specialists and CodeGeneralist | Same inherited coding baseline | Keep inherited unless a focused comparison justifies an override |
| Security, architecture, and complex diagnostics | Inherited model | Keep inherited unless task-specific evidence justifies an override |
| ContextSummarizer | Inherited model | Keep inherited; evaluate constraint and state preservation before overriding |

Override rules:

- A user may explicitly request a provisional pin before evaluation. Label it
    unbenchmarked and do not describe it as optimal; otherwise keep the inherited
    baseline until the candidate passes.
- Use exact model identifiers available in the user's model picker and supported
    by the active harness. Confirm tool use, structured output, context capacity,
    and organization policy before adding frontmatter overrides.
- Where supported, `model` can be an ordered list of verified available fallback
    identifiers. An availability fallback is not task-aware model routing or a
    quality guarantee. Do not configure placeholders or guess model identifiers.
- Leave `reasoning-effort` unset unless the chosen model supports it and a
    measured task-specific benefit warrants a pin. Do not globally force high effort.
- If a configured model fails, use only an approved available fallback or report
    the blocker. Never silently downgrade a security-sensitive task to save cost.

Evaluation gate:

1. Compare the inherited baseline and candidate on the same representative tasks
     with equivalent payloads, tool permissions, and acceptance checks.
2. For advisors, include clear, ambiguous, missing-context, and out-of-domain cases.
     Check valid JSON, expected status, and selection of a worker from the supplied
     candidates, not another advisor or an invented agent.
3. For workers, check accepted outputs, regressions, scope compliance, and actual
     validation evidence. For summaries, check preservation of constraints, active
     failures, and essential contracts rather than brevity alone.
4. Record exact model identifiers, task outcomes, retries, elapsed time, and usage
     or cost when exposed. Compare total cost per successful task, including failed
     attempts and retries, not just the first call. Do not invent missing telemetry.
5. Treat provisional pins as unverified until they demonstrate benefit without
    unacceptable quality loss. Keep the baseline when evidence is inconclusive
    and repeat comparisons after a model or harness change. Existing roster tests
    are not model benchmarks.

Model choice does not itself reduce the payload. The embedded index, minimal
task context, local worker inspection, and concise results remain the context
controls. Existing provisional overrides remain unchanged; the new business domain
inherits its model. No candidate-model comparison has been performed for this domain.

## Existing Edit Protection

Orchestrator includes existing-edit protection in every worker payload. Workers
that can edit files or run commands also embed the rule for direct invocation:
preserve existing edits, including changes discovered during a task. Before
restoring, reverting, resetting, overwriting, or otherwise discarding those edits,
ask the user for explicit approval naming the affected files and proposed
restoration. General task authorization is not approval to discard edits.
Without approval, preserve the edits and return NEEDS_INPUT through Orchestrator,
or ask the user directly when running as the main agent. Read-only roles remain
read-only; this safeguard grants no new tools or permissions.

## Naming Convention

Canonical names use ASCII PascalCase (acronyms such as API, CI, MCP, and ORM are
allowed), without spaces, underscores, or hyphens. The filename is exactly
`<Name>.agent.md` and frontmatter `name` must equal `<Name>`.

Domain workers use `<Domain><Capability><Role>`:

| Owner | Prefix | Example |
|---|---|---|
| CodeDomainAdvisor, CodeFrontendAdvisor, CodeBackendAdvisor | Code | CodeReactViteSpecialist |
| InfraDevOpsAdvisor | Infra | InfraReleaseManager |
| DocsGovernanceAdvisor | Gov | GovGitWorkflowAgent |
| BusinessKnowledgeAdvisor | Business | BusinessKnowledgeExpert |

The standalone business knowledge domain uses `Business`; `Gov` remains the
documentation/governance prefix. This is an explicit domain prefix, not a naming exception.

Worker role suffixes are `Agent`, `Specialist`, `Expert`, `Generator`, `Manager`,
`Builder`, `Diagnostician`, `Diagnostics`, `Generalist`, `Engineer`, or `Profiler`.
Prefer `Specialist` for new framework specialists, `Manager` for lifecycle ownership, and `Agent` for
workflow roles. Describe the capability rather than adding framework/version
numbers or long implementation inventories to the name.

Selection advisors end in `Advisor`; the current seven advisor names and dispatcher
name Orchestrator are reserved architectural roles. Existing explicit exceptions
are MultiLanguageBuilder under CodeDomainAdvisor, and AgentOptimizer, Brainstorm,
and ContextSummarizer under UtilityAdvisor. New unprefixed names require an
explicit policy and validator update; these exceptions are not a general fallback.
Do not rename unrelated existing agents merely to standardize role suffixes.

## Agent Checklist

Every new or renamed agent must include all of the following in the same change:

1. A matching definition filename/frontmatter name, meaningful description,
    invocation settings, and a role-appropriate validated tool profile.
2. One embedded owner, a worker selection cue where applicable, Orchestrator
    allowlist membership, and a matching embedded routing row. Keep the owning
    advisor's selection cues synchronized; no worker or advisor delegates.
3. A README Agent Index row, Domain Organization diagram entry, and Domain Map
    membership. Update affected Tool Policy and workflow sections, including tool
    preference/fallback behavior. Record renames in Name Migration without keeping
    obsolete operational aliases.
4. Static validator and regression-suite results. Naming, index completeness,
    embedded-route parity, ownership docs, and tool profiles are required checks.
    Report pre-existing failures and unavailable checks explicitly.

AGENTS.md applies these requirements to repository maintenance. Static checks
enforce names and structural documentation coverage, not prose accuracy or live
agent discovery; review behavioral documentation and smoke-test changed workflows
when the required runtime is available.

## Name Migration

Update saved agent selections and external workflow references to these names.
Old filenames were removed; no alias agents are installed. Tools, ownership, and
execution responsibilities are unchanged by this naming migration.

```text
WebDiagnosisExpert                       -> CodeFrameworkDiagnostician
CompactionExpert                         -> ContextSummarizer
InfraDevContainerOrchestrator             -> InfraDevContainerSpecialist
InfraPRCIErrDiagnosticFix                 -> InfraCIDiagnostics
CodeComponentLibraryDesignSystemAgent    -> CodeDesignSystemSpecialist
CodeTypeScriptReactViteGenerator          -> CodeReactViteSpecialist
ObservabilityAgent                       -> InfraObservabilitySpecialist
MiscAdvisor                              -> UtilityAdvisor
CodeNextjsGenerator                      -> CodeNextJsSpecialist
CodePythonFastAPIBuilder                 -> CodeFastApiSpecialist
CodeNodeJsExpressGenerator               -> CodeExpressSpecialist
CodeSpringBootGenerator                  -> CodeSpringBootSpecialist
GitGithubAgent                           -> GovGitWorkflowAgent
GovBusinessKnowledgeAdvisor              -> BusinessKnowledgeAdvisor
GovBusinessKnowledgeExpert               -> BusinessKnowledgeExpert
```

## Notes

- Former DomainRouter definitions were renamed to Advisor definitions; select the
    updated names in saved workflows. Restart/select Orchestrator in a main chat
    when the editor has not refreshed its agent discovery list.
- Orchestrator's `agents:` is the direct invocation allowlist, not ownership.
    Only Orchestrator is user-invocable; workers and advisors are selected through
    its dispatch. Advisors have `tools: []` and `agents: []`; workers have no
    delegation tool.
- Orchestrator's embedded tables control ownership and selection cues; update them, the allowlist,
    and ownership documentation together when adding or renaming an agent.

## Validation

Run the static validator and its in-memory regression suite from this directory:

```powershell
python tools/agent-roster-validator.py
python -m unittest discover -s tests -v
```

Python and PyYAML are required. Validation checks two distinct contracts: flat
runtime invocation from Orchestrator, and its embedded single-parent ownership
tree with domain nesting and documentation parity. Indexed targets must resolve to
real workers, advisors must be tool-free, and role-specific required/allowed
tool profiles must match. NAM-1 enforces the naming convention; DOC-1 requires
exact README Agent Index coverage and embedded-route/model parity. The validator
derives its in-memory model from Orchestrator's embedded tables, not an external
routing file. Passing static checks does not
prove output quality, token savings, or runtime agent discovery.

## Runtime Verification

A prior nested-router smoke test on 2026-10-20 stopped at the coding router:
its subagent context had no agent-invocation tool. That failure motivated the
approved single-dispatcher contract. Do not invoke Orchestrator as a subagent and
expect it to delegate; it must be the main chat agent.

The main session exercised both replacement paths with read-only calls on 2026-10-20:

These results predate the naming-only migration above; the same definitions are
identified below by their current names. Runtime discovery under the new names
has not been re-tested; refresh agent selection after the migration.

- Direct worker: CodeReactViteSpecialist reviewed supplied JSX, found
    the missing stable key, and returned a minimal fix without files or commands.
- Optional advisor: CodeFrontendAdvisor returned MATCH for the shared component
    specialist. The main session checked that target against the supplied candidates
    and allowlist, then separately invoked CodeDesignSystemSpecialist.
    That worker returned a scoped approach without files, commands, or nested calls.

These historical tests verify direct worker invocation and advisor/worker separation
in that session; current user entry is through Orchestrator only.
They are not a full automatic-routing evaluation of a fresh Orchestrator main
chat, nor a benchmark of context size or output quality. Select the updated
Orchestrator as the main chat agent to use the contract; running it inside another
subagent would reintroduce the known nesting limitation.
