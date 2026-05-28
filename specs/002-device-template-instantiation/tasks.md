# Tasks: Device Template Instantiation — Schema

**Input**: Design documents from `specs/002-device-template-instantiation/`
**Branch**: `002-device-template-instantiation`
**Artifact cycle**: 1 of 2 — Schema only (Generator tasks come in cycle 2)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the working state of the schema file before making changes.

- [x] T001 Read `schemas/otn.yml` in full to confirm current structure (generics, nodes, extensions blocks)
- [x] T002 Run `uv run infrahubctl schema check schemas/` to establish a clean baseline before any edits

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The two new nodes have a dependency on each other (`OtnDesignDeviceEntry` references `OtnDeviceTemplate`). The device template node must be written first so the schema remains valid throughout editing.

**⚠️ CRITICAL**: T003 must complete before T004; T004 must complete before T005.

- [x] T003 Add `OtnDeviceTemplate` node to the `nodes:` list in `schemas/otn.yml` — attributes: `name` (Text, unique), `platform` (Text), `device_type` (Text), `role` (Text, optional), `description` (Text, optional); set `generate_template: true`, `human_friendly_id: [name__value]`, `display_label: name__value`
- [x] T004 Add `device_entries` relationship to the `OtnSiteDesign` generic in `schemas/otn.yml` — `kind: Component`, `cardinality: many`, `optional: true`, `on_delete: cascade`, `identifier: design__device_entries`, `peer: OtnDesignDeviceEntry`
- [x] T005 Add `OtnDesignDeviceEntry` node to the `nodes:` list in `schemas/otn.yml` — attribute: `count` (Number, `default_value: 1`); relationships: `design` (`kind: Attribute`, cardinality one, `optional: false`, `on_delete: no-action`, `identifier: design__device_entries`, peer `OtnSiteDesign`) and `template` (`kind: Attribute`, cardinality one, `optional: false`, `on_delete: no-action`, `identifier: device_template__entries`, peer `OtnDeviceTemplate`); set `include_in_menu: false`, `human_friendly_id: [design__name__value, template__name__value]`

> **Note**: `kind: Parent` was changed to `kind: Attribute` on `OtnDesignDeviceEntry.design` during implementation. `kind: Parent` implicitly cascades deletion to the parent node — the correct approach for independent lifecycle is `kind: Attribute` with explicit `on_delete: no-action`.

**Checkpoint**: Foundation ready — all three YAML edits applied, schema file is complete.

---

## Phase 3: User Story 1 — Define a Device Template (Priority: P1) 🎯 MVP

**Goal**: `OtnDeviceTemplate` node is valid, loadable, and usable — a network engineer can create a template with name/platform/device_type/role and retrieve it.

**Independent Test**: Load the schema, create one `OtnDeviceTemplate` object via SDK or the UI, and confirm it's retrievable.

### Implementation for User Story 1

- [x] T006 [US1] Run `uv run infrahubctl schema check schemas/` — fix any validation errors before proceeding
- [x] T007 [US1] Run `uv run infrahubctl schema load schemas/` to apply the schema change to the running Infrahub instance
- [x] T008 [US1] Verify `OtnDeviceTemplate` and `OtnDesignDeviceEntry` appear in the Infrahub schema registry with correct relationships
- [x] T009 [US1] Create a test `OtnDeviceTemplate` instance (`border-router`, platform `IOS-XE`, device_type `ISR4451`, role `edge`) and confirm all attributes persist correctly

**Checkpoint**: User Story 1 complete — device templates can be defined and retrieved.

---

## Phase 4: User Story 2 — Reference Templates in a Site Design (Priority: P1)

**Goal**: `OtnDesignDeviceEntry` links a design to a template with a count. An existing `OtnCampusSite` can have multiple entries (e.g., 2 × border-router, 4 × access-switch).

**Independent Test**: Create two `OtnDesignDeviceEntry` records on a design with different templates and counts; confirm both are retrievable and the design's `device_entries` returns them.

### Implementation for User Story 2

- [x] T010 [US2] Verify `OtnDesignDeviceEntry` appears in the Infrahub schema and that the `device_entries` panel is present on `OtnSiteDesign` subtypes
- [x] T011 [US2] Create a second `OtnDeviceTemplate` instance (`access-switch`, platform `IOS`, device_type `C9300-24P`) to support the multi-template test
- [x] T012 [P] [US2] Create an `OtnDesignDeviceEntry` linking an existing `OtnCampusSite` to `border-router` with `count: 2` — verified entry saves and design shows 1 entry
- [x] T013 [P] [US2] Create a second `OtnDesignDeviceEntry` on the same design linking to `access-switch` with `count: 4` — verified design now shows 2 entries
- [x] T014 [US2] Update the `border-router` entry count from 2 to 3 — confirmed design reflects the change
- [x] T015 [US2] Delete one entry and confirm the design survives (design was NOT cascade-deleted) — verified with `kind: Attribute` on design relationship

**Checkpoint**: User Story 2 complete — template references with counts are fully functional.

---

## Phase 5: User Story 3 — Validate Template References (Priority: P2)

**Goal**: Confirm that the schema's referential structure prevents silent broken references.

**Independent Test**: Attempt to create a `Design Device Entry` with a non-existent template and confirm the API returns an error.

### Implementation for User Story 3

- [x] T016 [US3] Test referential integrity: attempt to create an `OtnDesignDeviceEntry` with an invalid/missing template — confirmed `GraphQLError` is raised, system rejects the bad reference
- [x] T017 [US3] Verify backward compatibility: confirmed all existing `OtnCampusSite` and `OtnDataCenterSite` objects (medium-campus, small-campus, dc-standard) load without errors; `router_count` and other attributes intact
- [x] T018 [US3] Confirm existing `LocationSite` objects are unaffected — 3 sites present, design relationships intact where set

**Checkpoint**: User Story 3 complete — referential integrity confirmed, backward compatibility verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T019 [P] Re-run `uv run infrahubctl schema load schemas/` — confirmed "already up to date, no changes required"
- [x] T020 Verify existing objects are valid — all OtnCampusSite, OtnDataCenterSite, LocationSite objects intact after schema load
- [x] T021 [P] Review `schemas/otn.yml` for readability — removed redundant `uniqueness_constraints` block from `OtnDeviceTemplate` (attribute-level `unique: true` is sufficient)
- [x] T022 Clean up test `OtnDeviceTemplate` and `OtnDesignDeviceEntry` objects created during smoke testing — `border-router`, `access-switch` templates and all test entries cleaned up

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — can start once T003/T004/T005 complete
- **US2 (Phase 4)**: Depends on Phase 3 completion (needs the schema loaded and a template to exist)
- **US3 (Phase 5)**: Depends on Phase 4 (needs entries to exist for validation testing)
- **Polish (Phase 6)**: Depends on all story phases complete

### Within Foundational Phase

- T003 → T004 → T005 (strict sequence — each node references the one before it)

### Parallel Opportunities

- T012 and T013 can run in parallel (different objects, no file conflict)
- T019 and T021 can run in parallel (read-only operations)

---

## Parallel Example: Phase 2 YAML edits

Each task edits the same file (`schemas/otn.yml`) so they MUST be sequential:

```
T003 (add OtnDeviceTemplate) → T004 (add device_entries to OtnSiteDesign) → T005 (add OtnDesignDeviceEntry)
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1: Setup (baseline check)
2. Complete Phase 2: Foundational (all three YAML edits)
3. Complete Phase 3: US1 (validate + load + smoke test DeviceTemplate)
4. **STOP and VALIDATE**: Template can be created and retrieved
5. Continue with US2 and US3

### Incremental Delivery

1. Phase 1 + 2 → schema YAML complete
2. Phase 3 → `OtnDeviceTemplate` works in Infrahub (MVP)
3. Phase 4 → template references in designs work
4. Phase 5 → backward compat and integrity confirmed
5. Phase 6 → polish and cleanup

---

## Notes

- [P] = tasks operating on different objects or read-only, safe to run in parallel
- All `infrahubctl` commands run via `uv run infrahubctl ...` in this project
- No Python files are modified in this schema cycle; generator changes are cycle 2
- The existing `router_count` / `access_switch_count` attributes on design nodes are intentionally preserved — do not remove or deprecate them in this cycle
- `kind: Parent` was found to cascade-delete the parent node when the child is deleted; use `kind: Attribute` with `on_delete: no-action` for independent lifecycle relationships
