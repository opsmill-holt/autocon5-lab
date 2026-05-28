# Infrahub Workflow Routing Preset

Wraps the core speckit workflow commands with Infrahub-specific artifact routing and mandatory skill invocation when `.infrahub.yml` is detected in the repository.

## What it does

Uses spec-kit's v0.8.0 `wrap` composition strategy to layer Infrahub-aware behavior *on top of* the core `/speckit.specify`, `/speckit.plan`, and `/speckit.implement` commands. The core command body is inherited automatically (via `{CORE_TEMPLATE}`), so upstream improvements to extension hooks, feature-directory handling, quality checklists, and agent-context updates flow through without manual porting.

### `/speckit.specify`

1. Checks for `.infrahub.yml` in the repo root — if absent, runs the core specify command unchanged.
2. Gates on Infrahub connectivity via `infrahubctl info`.
3. Classifies the user prompt into artifact types (schema, transform, check, generator, menu).
4. For multi-artifact prompts, presents the dependency chain and starts with Schema.
5. Invokes the matching Infrahub skill (`infrahub:schema-creator`, `infrahub:transform-creator`, …) before any spec is written.
6. Selects the Infrahub-specific spec template from the `infrahub` extension and runs the core workflow with that template.

### `/speckit.plan`

Invokes the artifact-matched Infrahub skill before Phase 0 research begins, then runs the core planning workflow.

### `/speckit.implement`

Invokes the artifact-matched Infrahub skill before each implementation phase that touches schema/transform/check/generator/menu/object files, then runs the core implementation workflow.

## Dependency chain

When a feature spans multiple artifact types:

```
Schema → [Check / Generator / Transform / Menu]
```

Schema is always first — everything else depends on the data model being loaded.

## Requires

- **`spec-kit >= 0.8.0`** — for `wrap` composition strategy
- **`opsmill/infrahub` Claude Code skills** (REQUIRED) — provides the `infrahub:schema-creator`, `infrahub:transform-creator`, `infrahub:check-creator`, `infrahub:generator-creator`, `infrahub:menu-creator`, and `infrahub:object-creator` skills. Each wrapped command halts with install guidance if the skills are not present.
- **`infrahub` spec-kit extension** (OPTIONAL) — provides the Infrahub-specific spec templates (`spec-schema-template`, `spec-transform-template`, `spec-check-template`, `spec-generator-template`, `spec-menu-template`). If absent, the specify command falls back to the core `spec-template.md` and warns.
- **`infrahubctl` CLI** — for the connectivity check against a running Infrahub instance.

## Installation

Install the spec-kit preset directly from this repository (latest `main`):

```bash
specify preset add --from https://github.com/opsmill/infrahub-speckit/archive/refs/heads/main.zip
```

Pin to a released version for stability:

```bash
specify preset add --from https://github.com/opsmill/infrahub-speckit/archive/refs/tags/v2.0.0.zip
```

Or, once it's published to the public spec-kit catalog:

```bash
specify preset add infrahub
```

Install the Infrahub skills (recommended — npx):

```bash
npx skills add opsmill/infrahub-skills
```

Or via the Claude Code plugin marketplace:

```
/plugin marketplace add opsmill/claude-marketplace
/plugin install infrahub@opsmill
```

Skills documentation: https://docs.infrahub.app/skills/installation-setup

Optionally install the spec-kit `infrahub` extension once it's in the public catalog:

```bash
specify extension add infrahub
```

## Usage

### Quick start

From a fresh directory:

```bash
# 1. Initialize a spec-kit project with Claude integration
specify init --here --integration claude

# 2. Install this preset (direct from repo — catalog publishing is pending)
specify preset add --from https://github.com/opsmill/infrahub-speckit/archive/refs/heads/main.zip

# 3. Install the required Infrahub skills
npx skills add opsmill/infrahub-skills

# 4. Mark the project as an Infrahub project
cat > .infrahub.yml <<'YAML'
---
schemas: []
jinja2_transforms: []
artifact_definitions: []
queries: []
YAML

# 5. Start your Infrahub instance (so the connectivity gate passes)
invoke start   # or however you start your local Infrahub

# 6. Drive the workflow from Claude Code
```

Then from Claude Code:

```
/speckit.specify Create a schema for Devices, Interfaces, and VLANs with a transform that renders interface config
/speckit.plan
/speckit.tasks
/speckit.implement
```

### What each command does (concretely)

**`/speckit.specify <prompt>`**

1. Verifies `.infrahub.yml` exists (else runs core specify unchanged).
2. Verifies the six `infrahub:*` skills are installed (else halts with install guidance).
3. Runs `infrahubctl info` (else halts with "start your Infrahub instance").
4. Matches your prompt against artifact-type keywords — `schema`, `transform`, `check`, `generator`, `menu`.
5. If multiple types match, presents the dependency chain and starts with Schema:
   ```
   Your feature involves multiple Infrahub artifact types:
     1. Schema — Define the data model (must be done first)
     2. Transform — depends on schema

   Starting with: Schema
   After completing this cycle, run /speckit.specify again for the next artifact.
   ```
6. Invokes the matching Infrahub skill (e.g. `infrahub:schema-creator`) — pulls in curated attribute-kind, relationship-kind, cardinality, and naming-convention reference material that the spec must be consistent with.
7. Selects the Infrahub-specific template (`spec-schema-template`, `spec-transform-template`, etc.) from the `infrahub` spec-kit extension if installed, or falls back to the core `spec-template` with a warning.
8. Runs the core specify workflow with the selected template — writes `spec.md`, creates the feature directory, produces the quality checklist, fires `after_specify` hooks.

**`/speckit.plan`**

Re-invokes the artifact-matched skill before Phase 0 research begins, then runs the core planning workflow (produces `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`). The skill's reference material feeds directly into the data model and contract decisions.

**`/speckit.implement`**

Re-invokes the relevant skill before the first task of each artifact type in each phase — `infrahub:schema-creator` before schema YAML tasks, `infrahub:transform-creator` before transform tasks, and so on. Each command invocation starts fresh so skills must be re-invoked per command, not just per feature.

### Multi-artifact features: the chain

A single feature request that touches multiple artifact types (like the quick-start example: "schema + transform") is split into separate `/speckit.specify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.implement` cycles, one per artifact, in dependency order.

```
Cycle 1 (Schema):    /speckit.specify Schema for Devices, Interfaces, VLANs
                     /speckit.plan
                     /speckit.tasks
                     /speckit.implement
                     → produces schemas/network.yml

Cycle 2 (Transform): /speckit.specify Render interface config from the schema
                     /speckit.plan
                     /speckit.tasks
                     /speckit.implement
                     → produces templates/interface_config.j2 + queries/interface_config.gql
```

Schema is always cycle 1 because checks, generators, transforms, and menus all depend on the data model being loaded first.

### What ends up in the repository

After a full schema + transform cycle:

```
.infrahub.yml                           # referenced schema + transform + query + artifact_def
schemas/
  network.yml                           # DcimDevice, DcimInterface, IpamVlan
queries/
  interface_config.gql                  # GraphQL query for the transform
templates/
  interface_config.j2                   # Jinja2 rendering the device config
specs/
  001-network-schema/
    spec.md, plan.md, research.md, data-model.md, tasks.md,
    checklists/requirements.md, contracts/
  002-interface-config-transform/
    (same set)
```

## Troubleshooting

**"The Infrahub preset requires the opsmill/infrahub Claude Code skills"** — the preflight check in Step 2 / Prerequisites is telling you the skills aren't installed in this Claude Code session. Run `npx skills add opsmill/infrahub-skills`, restart the session, and retry.

**"Infrahub is not reachable. Please start your Infrahub instance first"** — the `infrahubctl info` connectivity gate failed. Start your local Infrahub and retry.

**Spec falls back to the core `spec-template.md` and warns** — the `infrahub` spec-kit extension isn't installed (it may not be in the public catalog yet). The fallback produces a valid spec; the only thing you lose is the Infrahub-specific section scaffolding. Install the extension if and when available.

**`specify preset resolve speckit.specify` says "not found"** — known quirk in spec-kit v0.8.0 for composed (`strategy: "wrap"`) commands. Use `specify preset info infrahub` to confirm the preset is installed and wrapping the expected commands; inspect `.claude/skills/speckit-specify/SKILL.md` directly to verify composition produced the expected content.

**Skills exist but my agent didn't invoke them** — the preset instructs the agent to invoke the skills as a hard requirement, but agents with weak instruction-following may skip. Look for the "anti-rationalization check" in the preset's Step 5 and paste it verbatim to the agent if it tries to proceed without invoking.
