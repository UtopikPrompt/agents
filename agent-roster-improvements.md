# Agent Roster Improvements

This shareable summary describes reusable roster capabilities and their
verification boundaries. It contains no personal activity history, external
repository inventory, account names, organization names, or deployment details.

## Applied Improvements

| Area | Change | Boundary |
|---|---|---|
| Architecture records | Discover repository-native RFC/ADR formats and preserve human decision authority | A proposal is not an accepted decision; documentation writers do not implement sibling application code |
| Release ownership | Separate preparation, Git mutations, publication and deployment | Each mutation stage needs its own authorization; workers never delegate |
| Local inference | Add InfraLLMInferenceSpecialist for model/runtime metadata, serving and capacity diagnosis | No universal memory constants, invented hardware or unapproved model downloads |
| Evaluation | Provide controlled inference evaluation with explicit artifacts, settings, timing and quality criteria | Predictions and static fixtures are not measured runtime results |
| Identity | Isolate workflow permissions, OIDC claims, App installation, application authorization, cloud trust and Secret delivery | No raw tokens, automatic permission expansion or provider assumptions |
| Deployment | Validate exact artifacts/overlays, retained storage ownership, prerequisites and bounded readiness | Recorded digests do not prove reviewed matching or provenance; publication is not rollout approval |
| Routing | Keep Orchestrator classification-only and preserve existing frameworks in unmatched implementations | TypeScript or an internal Vite builder does not imply React |
| Runtime guidance | Verify OS, SDK/tool versions, supported APIs and repository tooling | Examples are not proof of installed tools, platform support or successful execution |
| Remote workflows | Embed focused operational procedures in the owning agent definitions | No local skill discovery, client-profile paths or external workflow files required |

## Embedded Procedures

- Inference evaluation in [InfraLLMInferenceSpecialist.agent.md](InfraLLMInferenceSpecialist.agent.md).
- Identity failure isolation in the CI and security agents.
- Release contract preflight in release, Kubernetes, deployment and IaC agents.
- AWS platform safety in the IaC agent.
- Secure development bootstrap in container and polyglot agents.
- Container display operations in container and generic coding agents.
- Specification handoff in architecture and documentation agents.
- Go contract validation in generic coding and polyglot agents.

Required workflows must be embedded in the selected worker definition, since
Remote SSH sessions cannot be assumed to access local skills. Bounded duplication
between owning agents is intentional. The dispatcher keeps only selection and
coordination rules; it does not copy every procedure into its context. No external
workflow file or personal junction is required. Runtime tools and task-specific
evidence remain explicit prerequisites rather than permission-expansion triggers.

## Validation

Run the repository's required gates after roster changes:

```text
python -B tools/agent-roster-validator.py
python -B -m unittest discover -s tests -v
git -c core.whitespace=cr-at-eol diff --check
```

The [static validation report](agent-roster-report.md) records definition,
ownership, routing and documentation checks. The unit suite also checks embedded
procedure coverage, absence of external workflow discovery, policy contracts and the integrity of the
[routing scenarios](tests/roster-scenarios.yaml).

Static checks do not establish live routing accuracy, latency savings, actual
model/profiler compatibility, workload readiness or remote agent registration.
Live evaluation must record actual outputs and safety outcomes separately. Report
missing lint configuration and unrun checks honestly rather than treating them
as passing checks.

## Future Extensions

Add dedicated framework or extension workers only when supported lifecycle,
recurring demand and measured fallback limitations justify them. Until then,
preserve the existing stack with the generic coding worker. Do not add a worker
for every tool or infer that an unobserved capability is unused.

## Shareability

Keep agents, skills, scenarios, reports and documentation independent of personal
or source-project identities. Use synthetic examples and repository-relative
paths. Do not retain account/organization names, repository inventories or URLs,
activity/session identifiers, private hosts, credentials, or absolute user paths.
Gather task-specific context only when needed; do not bake it into shared assets.