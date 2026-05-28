# Tasks: Site Resource Allocation

**Input**: Design documents from `specs/004-site-resource-allocation/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US5)

---

## Phase 1: Setup

**Purpose**: Confirm tooling is in place before making changes.

- [x] T001 Verify `uv run infrahubctl info` reports Infrahub reachable at http://localhost:8000

**Checkpoint**: Infrahub reachable — proceed to schema work.

---

## Phase 2: User Story 1 — Schema enforces resource pools on sites (Priority: P1) 🎯 FOUNDATIONAL

**Goal**: Apply four schema changes: `fqdn` computed attr on devices, count constraints on design entries, `bgp_asn` removed from the design generic, and `bgp_asn` + `mgmt_pool` added to `LocationSite`.

**Independent Test**: After T007, run `uv run infrahubctl schema check schemas/` — zero errors. Confirm `OtnSiteDesign` has no `bgp_asn` field in the Infrahub UI. Confirm setting `OtnDesignDeviceEntry.count = 0` is rejected.

**⚠️ CRITICAL**: All subsequent phases depend on this schema migration being loaded successfully.

### Implementation for User Story 1

- [x] T002 [P] [US1] Add `fqdn` computed attribute to `DcimGenericDevice` generic in `schemas/base/dcim.yml` — use `computed_attribute.kind: Jinja2`, template `{{ name__value }}.{{ location__shortname__value }}.otternet.net`, `read_only: true`, `optional: true`, `order_weight: 1050`
- [x] T003 [US1] Mark `bgp_asn` attribute `state: absent` on `OtnSiteDesign` generic in `schemas/extensions/designs/design.yml`
- [x] T004 [US1] Add `parameters: { min_value: 1, max_value: 8 }` to the `count` attribute on `OtnDesignDeviceEntry` node in `schemas/extensions/designs/design.yml`
- [x] T005 [US1] Add `bgp_asn` attribute (`kind: Number`, `optional: true`, `order_weight: 2050`) to the `LocationSite` extension block in `schemas/extensions/designs/design.yml`
- [x] T006 [US1] Add `mgmt_pool` relationship (`peer: CoreIPAddressPool`, `cardinality: one`, `kind: Attribute`, `optional: true`, `identifier: location_site__mgmt_pool`, `order_weight: 2100`) to the `LocationSite` extension block in `schemas/extensions/designs/design.yml`
- [x] T007 [US1] Validate updated schemas with `uv run infrahubctl schema check schemas/` — fix any errors before proceeding
- [x] T008 [US1] Load schema migration with `uv run infrahubctl schema load schemas/ --wait 30`

**Checkpoint**: Schema loaded. `OtnSiteDesign.bgp_asn` is gone. `LocationSite` now has `bgp_asn` and `mgmt_pool`. `fqdn` is queryable on any device. Count constraints are enforced. All phases below can now begin.

---

## Phase 3: User Story 2 — IPAM prefixes and resource pools seeded (Priority: P2)

**Goal**: Load the management address space (supernet + per-site /24s) and create `CoreIPAddressPool` instances for LON, AMS, MUC and a `CoreNumberPool` for ASN allocation.

**Independent Test**: After T012, query Infrahub to confirm `172.16.0.0/16`, three `/24` prefixes, `lon-mgmt-pool`, `ams-mgmt-pool`, `muc-mgmt-pool`, and `otn-asn-pool` all exist. Query `lon-01.mgmt_pool` to confirm it links to `lon-mgmt-pool`.

### Implementation for User Story 2

- [x] T009 [P] [US2] Remove `bgp_asn` values from all three campus design objects in `objects/06_design_patterns.yml` (affects `small-campus`, `medium-campus`, `large-campus`)
- [x] T010 [P] [US2] Create `objects/10_ipam_mgmt.yml` — define `IpamPrefix` objects: `172.16.0.0/16` (supernet, role: management) plus children `172.16.1.0/24` (LON), `172.16.2.0/24` (AMS), `172.16.3.0/24` (MUC), each with role: management
- [x] T011 [P] [US2] Create `objects/11_resource_pools.yml` — CoreNumberPool otn-asn-pool only; CoreIPAddressPool objects require prefix IDs (no HFID on BuiltinIPPrefix) so they are created in `scripts/link_pools.py` via `invoke link-pools`
- [x] T012 [US2] Add `mgmt_pool` relationships to `lon-01`, `ams-01`, `muc-01` via `scripts/link_pools.py` (run `invoke link-pools` after `invoke load-objects`)
- [x] T013 [US2] Load all objects with `uv run invoke load-objects` then `uv run invoke link-pools` — both complete without errors

**Checkpoint**: IPAM tree and pools exist. Sites have `mgmt_pool` set. Generator can now run.

---

## Phase 4: User Story 3 — Generator allocates BGP ASN and management IPs idempotently (Priority: P3)

**Goal**: Extend `CampusSiteGenerator` to allocate a BGP ASN from `otn-asn-pool` (written to `LocationSite.bgp_asn`) and a management IP per device from the site's `CoreIPAddressPool` (set as `primary_address`), both idempotently.

**Independent Test**: After T018, run `uv run infrahubctl generator run campus_site_generator --identifier muc-01`. Confirm `muc-01.bgp_asn` is set to a value in 65000–65534. Confirm `MUC-RTR-01.primary_address` is an address from `172.16.3.0/24`. Re-run — confirm same values, no duplicates.

### Implementation for User Story 3

- [x] T014 [P] [US3] Update `queries/campus_site.gql`: remove `bgp_asn { value }` from the `... on OtnCampusSite` inline fragment; add `mgmt_pool { node { id } }` at the `LocationSite` node level (outside the design fragment)
- [x] T015 [US3] Add BGP ASN allocation to `generators/campus_site_generator.py`: after extracting `site_id`, fetch `site_node = await self.client.get(kind="LocationSite", id=site_id)`, fetch `asn_pool = await self.client.get(kind="CoreNumberPool", name__value="otn-asn-pool")`, assign `site_node.bgp_asn = asn_pool`, call `await site_node.save(allow_upsert=True)`
- [x] T016 [US3] Add management IP allocation to `generators/campus_site_generator.py`: extract `mgmt_pool_id` from `site["mgmt_pool"]["node"]["id"]`; fetch pool via `self.client.get(kind="CoreIPAddressPool", id=mgmt_pool_id)`; inside the device loop, after `device.save(allow_upsert=True)`, call `mgmt_ip = await self.client.allocate_next_ip_address(resource_pool=mgmt_pool, identifier=hostname, data={"description": f"Management IP for {hostname}"})`, set `device.primary_address = mgmt_ip`, call `await device.save(allow_upsert=True)` again
- [x] T017 [US3] Run `uv run infrahubctl generator campus_site_generator shortname=muc-01 --branch main` — muc-01.bgp_asn=65000, MUC-01-RTR-01 primary_address=172.16.3.2/32, MUC-01-ASW-01 primary_address=172.16.3.1/32
- [x] T018 [US3] Re-run the generator — bgp_asn=65000 unchanged, same IPs, no duplicates. Idempotent confirmed.

**Checkpoint**: Generator produces correct, idempotent allocations. Transform can now source real data.

---

## Phase 5: User Story 4 — Transform renders complete device config from SoT values (Priority: P4)

**Goal**: Update `router_config.gql` to fetch `fqdn`, `primary_address`, and `LocationSite.bgp_asn`; update `router_config.j2` to render all five values (hostname, FQDN, management IP, BGP ASN, banner) without any hand-typed values.

**Independent Test**: After T021, run `uv run infrahubctl render router_config --variables '{"device_name": "MUC-RTR-01"}'`. Confirm output contains `hostname MUC-RTR-01`, `fqdn MUC-RTR-01.muc-01.otternet.net`, the correct management IP, the correct BGP ASN, and the `! Managed by OtterNet SoT` banner. All values sourced from Infrahub.

### Implementation for User Story 4

- [x] T019 [P] [US4] Update `queries/router_config.gql`: add `fqdn { value }` and `primary_address { node { address { value } } }` to the device node fields; change the `location.node` fragment so `bgp_asn { value }` is fetched from `LocationSite` directly (remove traversal through `design.node.bgp_asn`)
- [x] T020 [P] [US4] Update `transforms/router_config.j2`: add `fqdn {{ device["fqdn"]["value"] }}` line after the hostname stanza; add a management interface block using `device["primary_address"]["node"]["address"]["value"]` (split on `/` for host-only); change the `router bgp` stanza to read `location["bgp_asn"]["value"]` instead of `design["bgp_asn"]["value"]`; preserve the `! Managed by OtterNet SoT` banner
- [x] T021 [US4] Rendered `router_config` for MUC-01-RTR-01 — all 5 values confirmed: hostname, fqdn=MUC-01-RTR-01.muc-01.otternet.net, mgmt IP=172.16.3.2, bgp_asn=65000, banner present

**Checkpoint**: Config render is fully SoT-driven. No values were typed by hand.

---

## Phase 6: User Story 5 — Proposed change scenario triggers validation checks (Priority: P5)

**Goal**: Create `scenarios/ch3_break_validation.yml` with a device named `my-router-01` assigned to a `LocationMetro` node, suitable for loading on a branch to demonstrate Challenge 3 validation.

**Independent Test**: Load `scenarios/ch3_break_validation.yml` on a branch, open a Proposed Change targeting `main`. Confirm both `CheckDeviceHostname` (regex) and `CheckDeviceSite` (wrong location type) report failures.

### Implementation for User Story 5

- [x] T022 [US5] Create `scenarios/ch3_break_validation.yml` — define a `LocationMetro` object (e.g., `bad-metro-01`, shortname `bad-01`) and a `DcimDevice` named `my-router-01` assigned to that metro location; both objects should use valid YAML object file format (same as objects/ files)

**Checkpoint**: Scenario file exists and is ready for Challenge 3 demo.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup.

- [x] T023 [P] Run `uv run infrahubctl schema check schemas/` once more on the final state to confirm zero warnings or errors — all 6 schema files Valid!
- [x] T024 Full quickstart validated end-to-end: schema load, load-objects, link-pools, generator run (bgp_asn=65000, IPs from 172.16.3.0/24), render (all 5 values present)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (US1 — Schema)**: Depends on Phase 1; **BLOCKS Phases 3–7** (schema migration must be applied first)
- **Phase 3 (US2 — Objects)**: Depends on Phase 2; loads seed data that the Generator reads
- **Phase 4 (US3 — Generator)**: Depends on Phases 2 and 3; needs schema fields and pool objects
- **Phase 5 (US4 — Transform)**: Depends on Phase 2 for schema fields; depends on Phase 4 for real test data
- **Phase 6 (US5 — Scenario)**: Depends on Phase 2 only; can be done in parallel with Phases 3–5
- **Phase 7 (Polish)**: Depends on all desired phases being complete

### User Story Dependencies

- **US1 (P1)**: Start immediately after Phase 1 — no story dependencies; blocks all others
- **US2 (P2)**: Depends on US1 schema load
- **US3 (P3)**: Depends on US1 + US2 (needs schema fields AND pool objects)
- **US4 (P4)**: Depends on US1 (schema fields); practically needs US3 data to verify render
- **US5 (P5)**: Depends on US1 only; fully independent of US2, US3, US4

### Within Each User Story

- T002 (dcim.yml) is independent of T003–T006 (design.yml); can be done in parallel
- T003–T006 all modify `design.yml`; do them sequentially or as a single edit session
- T009, T010, T011 touch different files; can be done in parallel

### Parallel Opportunities

- T002 [P] with T003–T006 (different schema files)
- T009 [P], T010 [P], T011 [P] (different object files)
- T014 [P] with T015–T016 (different files: gql vs py)
- T019 [P], T020 [P] (different files: gql vs j2)

---

## Parallel Example: User Story 3 (Generator)

```text
# These can run in parallel:
T014: Update queries/campus_site.gql (query file)
T015: Add ASN allocation to generators/campus_site_generator.py (Python file)

# Then sequentially:
T016: Add mgmt IP allocation (same Python file as T015)
T017: Run generator
T018: Re-run for idempotency check
```

---

## Implementation Strategy

### MVP First (User Story 1 Only — Schema migration)

1. Complete Phase 1: Setup
2. Complete Phase 2: US1 (schema) — FOUNDATIONAL
3. **STOP and VALIDATE**: Schema check passes, new fields visible in UI
4. Proceed to US2 seed data

### Incremental Delivery

1. Setup (T001) → Schema migration (T002–T008) → Foundation ✓
2. Seed IPAM + pools (T009–T013) → Data layer ✓
3. Generator allocations (T014–T018) → Design-driven deploy ✓
4. Transform updates (T019–T021) → Config render ✓
5. Scenario file (T022) → Lab demo ✓
6. Polish (T023–T024) → Done ✓

---

## Notes

- [P] tasks touch different files — safe to run in parallel or as concurrent subtasks
- Schema migration (state: absent) must complete before any object reload
- Object files must be cleaned of `bgp_asn` (T009) before `invoke load-objects` (T013)
- Generator idempotency test (T018) is a required step, not optional polish
- The scenario file (T022) uses the same YAML object format as files in `objects/` — see `objects/example.yml` for reference
