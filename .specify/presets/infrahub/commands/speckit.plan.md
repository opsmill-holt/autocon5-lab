---
description: Execute the implementation planning workflow using the plan template to generate design artifacts. Infrahub-aware — invokes the matching Infrahub skill before Phase 0 research.
handoffs:
  - label: Create Tasks
    agent: speckit.tasks
    prompt: Break the plan into tasks
    send: true
  - label: Create Checklist
    agent: speckit.checklist
    prompt: Create a checklist for the following domain...
---

## Infrahub Skill Integration (pre-core)

**MANDATORY — do NOT skip, defer, or rationalize around this.**

Before generating any design artifacts (research.md, data-model.md, contracts/), invoke the Infrahub skill that matches the feature's artifact type. The skill loads authoritative reference material that design decisions MUST be consistent with.

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

After installing, restart this session and re-run /speckit.plan.
```

Do NOT proceed further until the skills are installed.

### Detection

1. Read the feature spec (`spec.md`) from the current feature directory.
2. Classify the Infrahub artifact type from the spec content:

   | Artifact Type | Signals in Spec | Skill to Invoke |
   |---------------|-----------------|-----------------|
   | **Schema**    | schema, data model, nodes, attributes, relationships, generics, namespace, kind, CoreFileObject, inherit_from | `infrahub-managing-schemas` |
   | **Transform** | transform, render, config, artifact, jinja, device config | `infrahub-managing-transforms` |
   | **Check**     | check, validate, validation, enforce, rule, constraint | `infrahub-managing-checks` |
   | **Generator** | generator, auto-create, design-driven, topology, provision | `infrahub-managing-generators` |
   | **Menu**      | menu, navigation, sidebar, UI | `infrahub-managing-menus` |

3. If the spec involves multiple artifact types, invoke the skill for the PRIMARY type (the one being designed in this cycle).

### Invocation

Invoke the matched skill using the Skill tool BEFORE Phase 0 research begins. Use the skill's reference material when:

- Writing `data-model.md` (entity definitions, attribute kinds, relationship types)
- Making research decisions (SDK patterns, API conventions, naming rules)
- Validating the design against Infrahub capabilities

**Anti-rationalization check** — if you think "I already researched this via WebFetch" or "I know Infrahub well enough", invoke the skill anyway. The skill has curated reference material that general knowledge and web fetches do not provide.

---

{CORE_TEMPLATE}
