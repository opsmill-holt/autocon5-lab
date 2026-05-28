---
description: Create or update the feature specification from a natural language feature description, with Infrahub artifact routing when .infrahub.yml is detected.
handoffs:
  - label: Build Technical Plan
    agent: speckit.plan
    prompt: Create a plan for the spec. I am building with...
  - label: Clarify Spec Requirements
    agent: speckit.clarify
    prompt: Clarify specification requirements
    send: true
---

## Infrahub Routing (pre-core)

**This preset wraps `/speckit.specify` with Infrahub-aware artifact routing.** The steps below run BEFORE the core specify workflow embedded at the end of this file. If `.infrahub.yml` is not present, skip straight to the core workflow.

### Step 1 — Detect Infrahub project

Check if `.infrahub.yml` exists in the repository root.

- **If it does NOT exist**: Skip Infrahub routing entirely. Do not run Steps 2–8. Proceed to the core workflow below.
- **If it exists**: Continue to Step 2.

### Step 2 — Verify required Infrahub skills are installed

This preset MANDATES invoking the `infrahub-managing-*` skills during specification. Before continuing, confirm these skills appear in your available-skills inventory:

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

After installing, restart this session and re-run /speckit.specify.
```

Do NOT proceed further until the skills are installed. The "MUST invoke" rules in Step 5 are meaningless without them.

### Step 3 — Verify Infrahub connectivity

Run `infrahubctl info` to verify that the Infrahub instance is reachable.

- **If the command fails or Infrahub is not reachable**, stop and warn the user:
  ```
  Infrahub is not reachable. Please start your Infrahub instance first:
    invoke start
  Then re-run /speckit.specify
  ```
  Do NOT proceed further.
- **If it succeeds**: Continue to Step 4.

### Step 4 — Classify artifact types from the user's input

Match the user's prompt case-insensitively against this table. A prompt can match multiple rows.

| Artifact Type | Keywords / Signals | Extension Template |
|---------------|-------------------|-------------------|
| **Schema**    | schema, data model, nodes, attributes, relationships, hierarchy, generics, namespace, kind, store information, model | `spec-schema-template` |
| **Transform** | transform, render, config, artifact, output, template, jinja, generate config, device config, configuration | `spec-transform-template` |
| **Check**     | check, validate, validation, enforce, rule, constraint, verify | `spec-check-template` |
| **Generator** | generator, auto-create, design-driven, topology, provision, generate objects | `spec-generator-template` |
| **Menu**      | menu, navigation, sidebar, UI, organize | `spec-menu-template` |

If nothing matches, default to `spec-schema-template` (schema-first principle — everything downstream depends on the data model).

### Step 5 — Handle single vs. multiple artifact types

**Single match** — proceed with that template.

**Multiple matches** — present the dependency chain to the user and start with the first:

```markdown
## Infrahub Artifact Routing

Your feature involves multiple Infrahub artifact types:

1. **Schema** — Define the data model (must be done first)
2. **<Second artifact>** — depends on schema

The spec-driven workflow handles one artifact type per cycle:
`/speckit.specify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.implement`

**Starting with: Schema**
After completing this cycle, run `/speckit.specify` again for the next artifact.
```

Dependency order (earlier must complete first):

1. Schema (always first — everything depends on the data model)
2. Check, Generator, Transform, Menu (all depend on schema; independent of each other)

### Step 6 — Invoke the corresponding Infrahub skill

**MANDATORY — do NOT skip, defer, or rationalize around this.** (Availability was already verified in Step 2.)

Invoke the skill using the Skill tool BEFORE any spec content is written. The skill provides curated reference material (schema properties, validation rules, naming conventions, API patterns) that the spec MUST be consistent with.

| Artifact Type | Skill to Invoke | What It Provides |
|---------------|-----------------|------------------|
| **Schema**    | `infrahub-managing-schemas`    | Schema property reference, node/generic definitions, attribute kinds, relationship types, CoreFileObject, naming conventions, validation rules |
| **Transform** | `infrahub-managing-transforms` | Transform types (Python/Jinja2), query patterns, artifact definitions, content types |
| **Check**     | `infrahub-managing-checks`     | Check definition structure, validation logic patterns, proposed change pipeline |
| **Generator** | `infrahub-managing-generators` | Generator class patterns, target groups, query parameters, idempotent creation |
| **Menu**      | `infrahub-managing-menus`      | Menu structure, node organization, sidebar customization |

For multi-artifact prompts, invoke the skill for the FIRST artifact type in the dependency chain (the one being specified in this cycle).

**Anti-rationalization check** — if any of these thoughts appear, invoke the skill anyway:
- "I already know Infrahub schemas" — the skill has validated reference material that's not in training data
- "I fetched the docs via WebFetch" — web docs can be incomplete or outdated
- "This is a simple change" — simple changes still need correct attribute kinds, cardinalities, and naming
- "I'll invoke it later during planning" — the spec fixes entities and requirements NOW

### Step 7 — Select the template for the core workflow

Resolve the template path for the selected artifact type:

1. Prefer `.specify/extensions/infrahub/templates/<template-name>.md` (e.g. `spec-schema-template.md`).
2. If that file does not exist, fall back to `.specify/templates/spec-template.md` and warn the user that the Infrahub extension templates are missing.

**Override for the core workflow below** — When the core instructions reference `templates/spec-template.md` or "spec-template", use the Infrahub template selected above instead. The rest of the core flow (branch creation hook, feature directory, quality checklist, reporting, after_specify hooks) runs unchanged.

### Step 8 — Proceed to the core workflow

Continue with the wrapped core command content below. Remind the user at completion, if multiple artifacts were detected, to re-run `/speckit.specify` for the next artifact in the chain.

---

{CORE_TEMPLATE}
