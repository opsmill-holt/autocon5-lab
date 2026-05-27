# Implementation Plan: Device Template Instantiation — Schema

**Branch**: `002-device-template-instantiation` | **Date**: 2026-05-27 | **Spec**: [spec.md](./spec.md)
**Artifact Cycle**: 1 of 2 — Schema (Generator planned separately)

## Summary

Add two new nodes to `schemas/otn.yml` — `OtnDeviceTemplate` (a reusable device blueprint with platform/device_type/role) and `OtnDesignDeviceEntry` (a junction linking a design to a template with a count) — and extend the existing `OtnSiteDesign` generic with a `device_entries` Component relationship. This replaces the hardcoded role→platform dictionaries in the generator with data stored in Infrahub.

## Technical Context

**Language/Version**: YAML (Infrahub schema DSL), Python 3.12 (infrahubctl tooling)
**Primary Dependencies**: Infrahub 1.9.6, infrahub-sdk 1.20.1
**Storage**: Infrahub graph database (managed)
**Testing**: `infrahubctl schema check`, manual UI smoke test
**Target Platform**: Infrahub instance at http://localhost:8000
**Project Type**: Infrahub schema extension (YAML-only change)
**Performance Goals**: N/A — schema load is a one-time operation
**Constraints**: Must not break existing `OtnCampusSite` / `OtnDataCenterSite` objects or the current `CampusSiteGenerator`
**Scale/Scope**: 2 new nodes, 1 modified generic, 1 YAML file

## Constitution Check

*Constitution not configured for this project (template placeholders only). No gates to enforce.*

## Project Structure

### Documentation (this feature)

```text
specs/002-device-template-instantiation/
├── plan.md          ← this file
├── spec.md
├── research.md      ← Phase 0 complete
├── data-model.md    ← Phase 1 complete
├── quickstart.md    ← Phase 1 complete
├── checklists/
│   └── requirements.md
└── tasks.md         ← Phase 2 (created by /speckit-tasks)
```

### Source Code (repository root)

```text
schemas/
└── otn.yml          ← only file modified by this feature

# No new files. No Python changes in this cycle.
# Generator update is a separate feature cycle.
```

**Structure Decision**: Single schema file modification. The `Otn` namespace lives in `schemas/otn.yml` and both new nodes belong to the same namespace — no file split warranted.

## Implementation Steps

### Step 1 — Add `OtnDeviceTemplate` node to `schemas/otn.yml`

Insert after the existing nodes block. Full YAML in `data-model.md`.

Key properties:
- `generate_template: true` — enables clone-from-template UX
- `name` is unique; serves as `human_friendly_id`
- Attributes: `name`, `platform`, `device_type`, `role` (optional), `description` (optional)

### Step 2 — Add `OtnDesignDeviceEntry` node to `schemas/otn.yml`

Insert after `OtnDeviceTemplate`. Full YAML in `data-model.md`.

Key properties:
- `include_in_menu: false` — exposed only through its parent design
- Composite `human_friendly_id`: `[design__name__value, template__name__value]`
- `count` attribute with `default_value: 1`
- `design` relationship: `kind: Parent`, cardinality one, `on_delete: cascade`, identifier `design__device_entries`
- `template` relationship: `kind: Attribute`, cardinality one, `on_delete: no-action`, identifier `device_template__entries`

### Step 3 — Extend `OtnSiteDesign` generic

Add `device_entries` relationship to the existing `OtnSiteDesign` generic definition:
- `kind: Component`, cardinality many, `on_delete: cascade`, identifier `design__device_entries`

This is a direct edit to the `generics:` list in `otn.yml`, NOT an `extensions:` block (both nodes live in the same file).

### Step 4 — Validate and load

```bash
uv run infrahubctl schema check schemas/
uv run infrahubctl schema load schemas/
```

### Step 5 — Smoke test

1. Create an `OtnDeviceTemplate` (e.g., `border-router`, platform `IOS-XE`, device_type `ISR4451`).
2. Open an `OtnCampusSite` design → add a `Design Device Entry` → select template, count 2.
3. Verify entry appears under the design.
4. Confirm existing campus/DC designs are unaffected.

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Junction node vs attributed edge | Junction node (`OtnDesignDeviceEntry`) | Infrahub edges cannot carry attributes; count requires a node |
| design→entries relationship kind | Component + cascade | Entries have no meaning without a parent design |
| template→entries on_delete | no-action | Templates are shared; auto-cascade would silently destroy other designs' entries |
| generate_template on DeviceTemplate | yes | Clone UX for "golden" templates is the core user story |
| Backward compatibility | Keep existing count attrs | Generator still reads them; deprecation is a Generator-cycle concern |

See `research.md` for full decision rationale.
