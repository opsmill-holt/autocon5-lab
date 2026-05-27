# Tasks: OtterNet Infrahub Lab — Full Implementation

**Input**: Design documents from `specs/001-otternet-infrahub-lab/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓

**Organization**: Tasks grouped by user story in dependency order. Schema (foundational) first, then objects, checks, generator, transform.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1–US5)

---

## Phase 1: Setup (Project Structure)

**Purpose**: Create directory structure and initial files before implementation begins.

- [x] T001 Create directory structure: `generators/`, `checks/`, `queries/`, `transforms/` at repo root
- [x] T002 [P] Create `generators/__init__.py` (empty)
- [x] T003 [P] Create `checks/__init__.py` (empty)

---

## Phase 2: Foundational — Schema (Blocking for all phases)

**Purpose**: Define the OTN data model. MUST be loaded into Infrahub before any objects, checks, generators, or transforms can work.

**⚠️ CRITICAL**: No downstream work can proceed until schema is loaded and verified.

- [x] T004 Create `schemas/otn.yml` with `OtnSiteDesign` generic (`name`, `description`, `router_count`, `bgp_asn` attrs; `site` → `LocationSite` relationship)
- [x] T005 Add `OtnCampusSite` node to `schemas/otn.yml` (inherits `OtnSiteDesign` + `CoreArtifactTarget`; attrs: `access_switch_count`, `distribution_switch_count`; uniqueness on `name__value`)
- [x] T006 Add `OtnDataCenterSite` node to `schemas/otn.yml` (inherits `OtnSiteDesign` + `CoreArtifactTarget`; attrs: `spine_count`, `leaf_count`, `border_leaf_count`; uniqueness on `name__value`)
- [x] T007 Run `uv run infrahubctl schema check schemas/` — fix any errors before continuing
- [x] T008 Load schema into Infrahub: `uv run infrahubctl schema load schemas/`

**Checkpoint**: `uv run infrahubctl schema list | grep Otn` should show `OtnCampusSite` and `OtnDataCenterSite`.

---

## Phase 3: User Story 2 — Seed Data (P1)

**Goal**: Two existing sites (lon-01, ams-01) fully represented in Infrahub with locations, design instances, and devices.

**Independent Test**: `uv run infrahubctl object load objects/` completes with no errors; GraphQL query returns lon-01 and ams-01 with correct designs.

- [x] T009 [US2] Create `objects/locations.yml` with `LocationCountry` (United Kingdom, Netherlands), `LocationMetro` (London, Amsterdam), `LocationSite` (lon-01, ams-01)
- [x] T010 [P] [US2] Create `objects/organizations.yml` with `OrganizationManufacturer` (Cisco), `DcimPlatform` (IOS-XE, IOS), `DcimDeviceType` (ISR4451, C9300-48P, C9300-24P)
- [x] T011 [US2] Create `objects/design_instances.yml` with 4 design instances: `small-campus` (1 RTR, 1 ASW, bgp_asn 65001), `medium-campus` (1 RTR, 1 DSW, 2 ASW, bgp_asn 65002), `large-campus` (2 RTR, 2 DSW, 4 ASW, bgp_asn 65003), `dc-standard` (OtnDataCenterSite: 2 spine, 4 leaf, 2 border-leaf)
- [x] T012 [US2] Create `objects/lon01_devices.yml` with 8 `DcimPhysicalDevice` objects for lon-01: LON-RTR-01, LON-RTR-02, LON-DSW-01, LON-DSW-02, LON-ASW-01..04 — each referencing site `lon-01` and correct DeviceType/Platform
- [x] T013 [P] [US2] Create `objects/ams01_devices.yml` with 4 `DcimPhysicalDevice` objects for ams-01: AMS-RTR-01, AMS-DSW-01, AMS-ASW-01, AMS-ASW-02
- [x] T014 [US2] Load all objects: `uv run infrahubctl object load objects/`

**Checkpoint**: All 12 devices visible in Infrahub UI. `lon-01` shows large-campus design, `ams-01` shows medium-campus design.

---

## Phase 4: User Story 3 — Enforcement Checks (P2)

**Goal**: Python checks fire on proposed changes to block invalid device names and devices without sites.

**Independent Test**: Run `uv run infrahubctl check run --name check_device_hostname` — passes on clean seed data.

- [x] T015 [US3] Create `queries/all_devices.gql` — query all `DcimPhysicalDevice` with `id`, `name.value`, and `site.node.{id, shortname.value}`
- [x] T016 [US3] Create `checks/device_checks.py` with `CheckDeviceHostname` class (validates `^[A-Z]{3}-[A-Z]{2,5}-\d{2}$` regex against each device name) and `CheckDeviceSite` class (validates `site.node` is non-null)
- [x] T017 [US3] Register both checks in `.infrahub.yml` under `check_definitions` (two entries, both using `all_devices` query via class `query` attribute)
- [x] T018 [US3] Register `all_devices` query in `.infrahub.yml` under `queries`

**Checkpoint**: `uv run infrahubctl check run --name check_device_hostname` exits 0.

---

## Phase 5: User Story 4 — Generator (P1)

**Goal**: Running the Generator on `small-campus` creates MUC-RTR-01, MUC-SW-01 and links them to the muc-01 site.

**Independent Test**: Create a `LocationSite` for muc-01 and an `OtnCampusSite` design named `small-campus` linked to it. Run generator. Verify devices created.

- [x] T019 [US4] Create `queries/campus_site.gql` — query `OtnCampusSite` by `$name: String!`, return `name.value`, `router_count.value`, `access_switch_count.value`, `distribution_switch_count.value`, `site.node.{id, shortname.value}`
- [x] T020 [US4] Create `generators/campus_site_generator.py` with `CampusSiteGenerator(InfrahubGenerator)` class: `generate()` method extracts site code from `campus["name"]["value"][:3].upper()`, iterates roles (RTR/DSW/ASW with counts from design), creates `DcimPhysicalDevice` objects with `allow_upsert=True`, creates `DcimInterface` objects per role using `ROLE_INTERFACES` dict
- [x] T021 [US4] Add `CoreGeneratorGroup` object for `campus_sites` to `objects/design_instances.yml` (or a new `objects/groups.yml`)
- [x] T022 [US4] Register generator in `.infrahub.yml`: query `campus_site`, file `generators/campus_site_generator.py`, class `CampusSiteGenerator`, targets `campus_sites`, parameters `name: name__value`
- [x] T023 [US4] Register `campus_site` query in `.infrahub.yml` under `queries`
- [x] T024 [US4] Add `OtnCampusSite` design instance `small-campus` membership in `campus_sites` group (via `member_of_groups`)
- [x] T025 [US4] Test generator: `uv run infrahubctl generator run --name campus_site_generator --identifier small-campus`

**Checkpoint**: Generator creates devices without errors. Re-running produces no duplicates (idempotent).

---

## Phase 6: User Story 5 — Transform / Config Rendering (P2)

**Goal**: Jinja2 Transform renders a complete router config for any campus device with hostname, interfaces, BGP ASN, and OtterNet banner.

**Independent Test**: `uv run infrahubctl transform run --name router_config --identifier MUC-RTR-01` outputs a non-empty text config with `hostname MUC-RTR-01` and `! Managed by OtterNet SoT`.

- [x] T026 [US5] Create `queries/router_config.gql` — query `DcimPhysicalDevice` by `$device_name: String!`, return `name.value`, `interfaces.edges[].node.{name.value, primary_address.node.address.value}`, `site.node.{shortname.value}` + traverse to `OtnCampusSite` design for `bgp_asn.value`
- [x] T027 [US5] Create `transforms/router_config.j2` Jinja2 template rendering: `! Managed by OtterNet SoT` banner, `hostname <name>`, interface stanzas (with `no ip address` fallback when no IP assigned), `router bgp <bgp_asn>` stanza (when bgp_asn present)
- [x] T028 [US5] Register transform in `.infrahub.yml` under `jinja2_transforms` (name: `router_config`, query: `router_config`, template_path: `transforms/router_config.j2`)
- [x] T029 [US5] Register `router_config` query in `.infrahub.yml` under `queries`
- [x] T030 [US5] Register artifact definition in `.infrahub.yml` under `artifact_definitions` (name: `router_config`, targets: `campus_sites`, transformation: `router_config`, parameters: `device_name: name__value`)
- [x] T031 [US5] Test transform: `uv run infrahubctl transform run --name router_config --identifier MUC-RTR-01`

**Checkpoint**: Config output contains `hostname MUC-RTR-01`, at least one interface block, BGP stanza, and OtterNet banner.

---

## Phase 7: Polish & Integration

**Purpose**: Final wiring, validation of full end-to-end flow, and quickstart verification.

- [x] T032 [P] Run `uv run infrahubctl schema check schemas/` — verify clean
- [x] T033 Run `uv run infrahubctl check run --name check_device_hostname && uv run infrahubctl check run --name check_device_site` — both pass
- [x] T034 Verify quickstart.md steps work end-to-end on a clean schema state

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Schema)**: Depends on Phase 1 — BLOCKS everything else
- **Phase 3 (Objects)**: Depends on Phase 2 (schema must be loaded first)
- **Phase 4 (Checks)**: Depends on Phase 2; independent of Phase 3
- **Phase 5 (Generator)**: Depends on Phase 2 + Phase 3 (needs design instances in Infrahub)
- **Phase 6 (Transform)**: Depends on Phase 5 (needs Generator-created devices for testing)
- **Phase 7 (Polish)**: Depends on all phases complete

### Parallel Opportunities

```
Phase 1: T001, T002, T003 in parallel
Phase 2: T004 → T005, T006 (sequential, same file) → T007 → T008
Phase 3+4: After T008 — T009..T014 (objects) and T015..T018 (checks) can run in parallel
Phase 5: After T014 (objects loaded) — T019..T025 sequential
Phase 6: After T025 (generator tested) — T026..T031 sequential
```

---

## Implementation Strategy

### MVP Scope (Phases 1–3)

1. Phase 1: Setup directories
2. Phase 2: Schema loaded → foundation ready
3. Phase 3: Seed data loaded → lon-01 and ams-01 visible in Infrahub

### Full Delivery (All Phases)

1. MVP scope above
2. Phase 4: Checks enforcing hostname + site rules
3. Phase 5: Generator deploying muc-01 site in < 5 min
4. Phase 6: Transform rendering deployable router config
5. Phase 7: End-to-end validation

---

## Notes

- All `uv run infrahubctl` commands require Infrahub running at `http://localhost:8000`
- `[P]` tasks touch different files and have no cross-dependencies — safe to parallelize
- Generator idempotency is guaranteed by `allow_upsert=True` + SDK tracking
- Schema library files (`schemas/base/`, `schemas/location_minimal/`) are already in place from `invoke schema-library-get`
- Total tasks: 34 | Schema: 5 | Objects: 6 | Checks: 4 | Generator: 7 | Transform: 6 | Polish: 3 | Setup: 3
