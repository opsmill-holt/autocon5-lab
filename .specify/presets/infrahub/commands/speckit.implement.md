---
description: Execute the implementation plan by processing and executing all tasks defined in tasks.md. Infrahub-aware — invokes the matching Infrahub skill before tasks that touch schemas, transforms, checks, generators, menus, or seed objects.
---

## Infrahub Skill Integration (pre-core)

**MANDATORY — do NOT skip, defer, or rationalize around this.**

Before implementing any task that touches Infrahub artifacts, invoke the corresponding Infrahub skill. The skill loads authoritative reference material, validation rules, and implementation patterns that the code MUST follow.

### Prerequisites

If the repository has no `.infrahub.yml`, skip this section entirely and proceed to the core workflow.

Otherwise, confirm these skills appear in your available-skills inventory:

- `infrahub-managing-schemas`
- `infrahub-managing-transforms`
- `infrahub-managing-checks`
- `infrahub-managing-generators`
- `infrahub-managing-menus`
- `infrahub-managing-objects`

**If ANY are missing**, halt and tell the user:

```
The Infrahub preset requires the opsmill/infrahub Claude Code skills.

Install (recommended):
  npx skills add opsmill/infrahub-skills

Or via the Claude Code plugin marketplace:
  /plugin marketplace add opsmill/claude-marketplace
  /plugin install infrahub@opsmill

Docs: https://docs.infrahub.app/skills/installation-setup

After installing, restart this session and re-run /speckit.implement.
```

Do NOT proceed further until the skills are installed.

### Detection

1. Read `tasks.md` and `plan.md` from the current feature directory.
2. Before starting each implementation phase, check whether any task in that phase touches an Infrahub artifact:

   | Task Involves | Skill to Invoke | When to Invoke |
   |---------------|-----------------|----------------|
   | Schema YAML files (`schemas/`)          | `infrahub-managing-schemas`    | Before the first schema task |
   | Python transforms (`transforms/`)       | `infrahub-managing-transforms` | Before writing transform code |
   | Python checks                           | `infrahub-managing-checks`     | Before writing check code |
   | Generator Python files (`generators/`)  | `infrahub-managing-generators` | Before writing generator code |
   | Menu YAML files (`menus/`)              | `infrahub-managing-menus`      | Before writing menu definitions |
   | Object data files (`objects/`)          | `infrahub-managing-objects`    | Before writing seed data |

3. Invoke each skill ONCE per artifact type per implementation session — you do not need to re-invoke for each task of the same type.

### Invocation Timing

- **Phase with schema tasks**: Invoke `infrahub-managing-schemas` before the FIRST schema task.
- **Phase with generator tasks**: Invoke `infrahub-managing-generators` before the FIRST generator task.
- **Phase with transform tasks**: Invoke `infrahub-managing-transforms` before the FIRST transform task.
- **Multiple artifact types in one phase**: Invoke each relevant skill before its first task.

**Anti-rationalization check** — if you think "I already loaded the skill during /speckit.specify" or "the plan has all the details I need", invoke the skill anyway. Skill content is NOT persisted across commands; each command session starts fresh.

---

{CORE_TEMPLATE}
