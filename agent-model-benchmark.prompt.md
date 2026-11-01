---
name: "Agent Model Benchmark"
description: "Run a bounded, read-only comparison of agent model choices using paired tasks, correctness rubrics, runtime model confirmation, and recorded usage counters."
---

# Agent Model Benchmark

Run a small, reproducible comparison of models for the requested agents. Do not edit agent definitions or change user settings. Do not benchmark more roles or models than requested.

## Protocol

1. Use the current runtime's subagent/task tool to invoke each named agent directly. Set its explicit `model` argument to an exact model choice exposed by the current runtime (for example, `Claude Haiku 5.5 (copilot)` or `GPT-6 Luna (copilot)`). The agent definition's frontmatter and the visible model label alone do not prove which model served a run.
2. Do not make debug-log or billing access a prerequisite for running trials. First attempt the explicit-model invocation. If the task tool is absent, an agent is not registered, or a requested model is rejected, report the exact error and mark only that comparison blocked; do not substitute a different agent or model. If the call succeeds but resolved-model or usage telemetry is unavailable, still score the completed response and mark those fields unverified.
3. For each requested agent/model pair, run the same task prompt twice in separate fresh subagent calls. Keep task input, parent payload, response limits, and tool restrictions identical. Randomize model order within each pair where practical.
4. Instruct benchmark agents not to use tools, inspect files, edit, execute commands, browse, delegate, or make external changes. Treat results as proposals only.
5. Independently score every response against the task rubric. Do not award points for verbosity, confidence, or self-reported checks. Report incomplete, unsafe, or incorrect claims explicitly.
6. When the current session's debug records are accessible, inspect them for the resolved model, input/output/cached tokens, model duration, and billed usage counter. Do not infer the resolved model from the requested model name. Keep parent coordination cost separate from subagent model cost. Do not inspect unrelated sessions or expose raw prompts, private data, or chain-of-thought.
7. Report per trial, not only averages: requested model, resolved model (verified or unverified), correctness score, critical failures, tokens, recorded usage, and duration. Distinguish a failed invocation from a successful trial with missing telemetry. Never claim a cost winner without comparable evidence.
8. Leave settings and agent definitions unchanged. Present any suggested model assignment as a recommendation requiring separate authorization.

## Pilot Tasks

Use one requested agent from each role and the following fixed tasks. Reuse the exact prompts and rubrics across model candidates.

### Advisor: CodeBackendAdvisor

Prompt:

> Classify each case using only the supplied candidate list. A: Fix an existing FastAPI dependency that validates a request with Pydantic; preserve the stack. B: Add an index and reversible migration to an existing Prisma schema, with no HTTP changes. C: Build an API; language, framework, requirements, and existing stack are unspecified. Candidates: CodeDatabaseORMGenerator for database schema/ORM/migrations; CodeGraphQLTRPCAgent for GraphQL/tRPC; CodeFastApiSpecialist for FastAPI/Pydantic; CodeExpressSpecialist for Express; CodeSpringBootSpecialist for Spring. Return only JSON array A/B/C with status, exact agent or null, reason, and missing_context.

Rubric: A -> CodeFastApiSpecialist; B -> CodeDatabaseORMGenerator; C -> NEEDS_INPUT with missing stack/requirements. No tools, extra routing, invented context, or execution claims.

### Coding: CodeGeneralist

Prompt:

> Provide a corrected JavaScript function with signature `async function mapLimit(items, limit, worker)`. `items` is an array; `worker(item, index)` may return a value or promise. Reject invalid `limit` with RangeError before invoking worker, including when items is empty. Limit concurrent calls; invoke each item exactly once on success; preserve result order; empty input returns an empty array. On the first observed synchronous throw or asynchronous rejection, start no more items, await already-started work to settle, then reject with the identical first observed thrown value, including undefined or null. Prevent unhandled rejections and do not cancel started work. Preserve the signature; no exports, dependencies, delays, logging, comments, or compatibility layers. Return only the complete function and one-sentence cause.

Rubric: Check input validation/order, bounded concurrency, stable result ordering, exact-once success, first-observed failure behavior for falsy thrown values, settlement of started work, and no unhandled rejections. Award correctness only when behavior is supported by an isolated test or a complete, defensible walkthrough; never claim an unrun test passed. Do not write files.

### Security: InfraSecurityAuthAgent

Prompt:

> Diagnose three independent synthetic cases using only these facts. A: An Actions job successfully requests OIDC; issuer and audience match AWS role trust. Sanitized caller subject is `repo:example/service:ref:refs/heads/feature`, but the reviewed trust policy permits only `repo:example/service:ref:refs/heads/main`; role assumption denies the request. Branch entitlement is not approved. B: Verified GitHub App installation identity is installation 42; metadata shows its selected repositories exclude target repository 77. Owner-approved configuration says installation 84 covers that target; existing API permissions suffice. C: Signature, issuer, and audience validate; caller tenant is tenant-a, but application lookup maps the caller to tenant-b. Repository-approved policy permits the caller only within tenant-a; API denies a tenant-b resource request. Return only JSON A/B/C with failing_boundary, evidence, one narrow next_read_only_check, minimal unexecuted proposal, and unknowns. Never request or expose secrets, widen trust/roles/tenant scope, rotate credentials, or mutate anything.

Rubric: A -> evidenced OIDC subject/trust-policy mismatch; no entitlement expansion while branch authorization is unapproved. B -> evidenced installation repository scope mismatch; verify installation/repository metadata and route authorized correction through owner, no API permission expansion. C -> application tenant authorization/mapping boundary; preserve tenant-a scope and investigate mapping/resource identity, no identity trust change. Unknowns stay unknown; no unsafe remediation or execution claim.

## Report

Summarize sample count and methodology, then list each trial with model and actual usage evidence. Include rubric scores, critical misses, and unavailable telemetry. State that results are preliminary and workload-specific. End with recommended next comparison only if the evidence supports it; otherwise state that the sample is too small to rank models.
