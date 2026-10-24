# Agent Roster Maintenance

This repository contains user-level VS Code agents. Follow the Naming Convention
and Agent Checklist in README.md whenever adding, renaming, or changing an agent.

- Use PascalCase ASCII names with the owning domain's Code, Infra, or Gov prefix
  and a descriptive role suffix. Filename must be <Name>.agent.md and frontmatter
  name must match exactly. Advisors end in Advisor. Do not invent new unprefixed
  names or silently expand the documented exceptions.
- Update the README Agent Index, Domain Organization diagram, Domain Map, and any
  affected tool or workflow documentation in the same change. Document changed
  behavior, including CLI preferences and fallback paths, not just the agent name.
- Keep Orchestrator's agents allowlist, Embedded Routing Index, Embedded Ownership,
  and the owning advisor's selection cues synchronized. Routing must be self-contained
  in the agent definition; do not add external runtime routing files. Remove obsolete
  operational references when renaming; record the old/new name in Name Migration.
- Preserve role boundaries: only Orchestrator delegates, advisors remain tool-free,
  and a new worker gets a suitable tool_profile in tools/agent-roster-validator.py.
- Run `python tools/agent-roster-validator.py` and
  `python -m unittest discover -s tests -v` after roster changes. Add
  focused regression coverage for new validation rules. Report existing failures
  separately; do not weaken rules or claim a passing roster when checks fail.

Do not commit, push, or change unrelated agent permissions without authorization.