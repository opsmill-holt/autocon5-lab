# Feature Specification: Site Resource Allocation

**Feature Branch**: `004-site-resource-allocation`
**Created**: 2026-05-28
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Schema enforces resource pools on sites (Priority: P1)

A workshop participant extends the OtterNet schema so that each `LocationSite` carries a direct BGP ASN (allocated by the Generator) and a pointer to its management IP pool. The `OtnSiteDesign` generic no longer holds a static `bgp_asn` — resource allocation is the Generator's responsibility, not the design blueprint's.

**Why this priority**: Without this schema foundation every downstream change (Generator, Transform, objects) is blocked. This is the load-bearing change.

**Independent Test**: Load the updated schemas, confirm `LocationSite` accepts `bgp_asn` and `mgmt_pool`, confirm `OtnSiteDesign` no longer has `bgp_asn`, confirm `OtnDesignDeviceEntry.count` rejects values outside 1–8, confirm `DcimGenericDevice` exposes a read-only `fqdn` field.

**Acceptance Scenarios**:

1. **Given** the updated schema is loaded, **When** a `LocationSite` is saved with `bgp_asn: 65001` and a `mgmt_pool` relationship to a `CoreIPAddressPool`, **Then** both fields are stored and readable via GraphQL.
2. **Given** the updated schema is loaded, **When** an `OtnDesignDeviceEntry` is saved with `count: 0`, **Then** Infrahub rejects the save with a validation error citing the `min_value: 1` constraint.
3. **Given** the updated schema is loaded, **When** an `OtnDesignDeviceEntry` is saved with `count: 9`, **Then** Infrahub rejects the save with a validation error citing the `max_value: 8` constraint.
4. **Given** a device named `MUC-RTR-01` is linked to location `muc-01`, **When** the `fqdn` attribute is read, **Then** it returns `MUC-RTR-01.muc-01.otternet.net` without any manual input.
5. **Given** an existing campus design with `bgp_asn` set, **When** the migration is applied, **Then** the `bgp_asn` field is absent from `OtnSiteDesign` objects.

---

### User Story 2 — IPAM prefixes and resource pools are seeded (Priority: P2)

A workshop participant loads the IPAM management address space and per-site prefix objects, plus `CoreIPAddressPool` instances for LON, AMS, and MUC sites and a `CoreNumberPool` for ASN allocation.

**Why this priority**: The Generator cannot allocate IPs or ASNs without these pool objects existing first. Seed data must be in place before Challenge 4.

**Independent Test**: Run `invoke load-objects`, then query Infrahub to confirm the supernet prefix, three /24 prefixes, three address pools, and one number pool all exist with correct parameters.

**Acceptance Scenarios**:

1. **Given** the objects are loaded, **When** `172.16.0.0/16` is queried, **Then** it exists as a parent prefix covering the management space.
2. **Given** the objects are loaded, **When** per-site prefixes are queried, **Then** `172.16.1.0/24` (LON), `172.16.2.0/24` (AMS), and `172.16.3.0/24` (MUC) each exist and are linked to their respective `CoreIPAddressPool`.
3. **Given** the objects are loaded, **When** `otn-asn-pool` is queried, **Then** it exists as a `CoreNumberPool` with start `65000` and end `65534`.
4. **Given** the objects are loaded, **When** `lon-01` is queried, **Then** its `mgmt_pool` relationship points to `lon-mgmt-pool`.

---

### User Story 3 — Generator allocates BGP ASN and management IPs idempotently (Priority: P3)

A workshop participant runs the `CampusSiteGenerator` against `muc-01`. The Generator reads the site's `mgmt_pool`, allocates one BGP ASN from `otn-asn-pool` and writes it to `LocationSite.bgp_asn`, then allocates one management IP per device from the site pool and sets it as each device's `primary_address`. Re-running the Generator produces identical output.

**Why this priority**: Design-driven resource allocation is the payoff of Challenge 4. Once the schema and pools exist this can be developed and tested independently.

**Independent Test**: Run the Generator against `muc-01`, verify BGP ASN written to `muc-01.bgp_asn`, verify each generated device has a `primary_address` from `172.16.3.0/24`. Run again — no new allocations, same values.

**Acceptance Scenarios**:

1. **Given** `muc-01` has `mgmt_pool: muc-mgmt-pool` and the Generator runs, **When** the run completes, **Then** `muc-01.bgp_asn` is set to a value in range 65000–65534.
2. **Given** the Generator has run once, **When** it runs again on the same site, **Then** `muc-01.bgp_asn` is unchanged and no duplicate IP allocations are created.
3. **Given** the Generator has run, **When** each device under `muc-01` is queried, **Then** every device has a `primary_address` from `172.16.3.0/24`.
4. **Given** the Generator query `campus_site.gql` is updated, **When** it is executed for `muc-01`, **Then** it returns `mgmt_pool` alongside the existing design device entries.

---

### User Story 4 — Transform renders complete device config from SoT values (Priority: P4)

A workshop participant updates the `router_config` transform so the rendered config uses the computed `fqdn`, the `primary_address` allocated by the Generator, and `LocationSite.bgp_asn` (not any field on the design).

**Why this priority**: Transform completeness is the final milestone. It can only be tested after the Generator has populated `bgp_asn` and `primary_address`.

**Independent Test**: Trigger the `router_config` artifact for `MUC-RTR-01`. Verify the rendered output contains the correct FQDN, management IP, and BGP ASN — none of which were typed by hand.

**Acceptance Scenarios**:

1. **Given** the Generator has run and `router_config.gql` is updated, **When** the artifact is rendered for `MUC-RTR-01`, **Then** the output contains `hostname MUC-RTR-01`.
2. **Given** the Generator has run, **When** the artifact is rendered, **Then** the output contains the FQDN `MUC-RTR-01.muc-01.otternet.net` sourced from the computed attribute (not a manually constructed string).
3. **Given** the Generator has allocated a management IP, **When** the artifact is rendered, **Then** the output contains that IP address sourced from `primary_address`.
4. **Given** the Generator has written `bgp_asn` to `muc-01`, **When** the artifact is rendered, **Then** the BGP ASN in the config matches `LocationSite.bgp_asn` (not any field on `OtnCampusSite`).

---

### User Story 5 — Proposed change scenario triggers validation checks (Priority: P5)

A scenario file seeds a branch with a device named `my-router-01` assigned to a `LocationMetro` (wrong location type). Opening a Proposed Change targeting `main` fires both `CheckDeviceHostname` (regex mismatch) and `CheckDeviceSite` (wrong location type).

**Why this priority**: This is Challenge 3 lab material. It is independent of resource allocation and can be authored and tested on its own once the schema changes from P1 are in place.

**Independent Test**: Load `scenarios/ch3_break_validation.yml` on a branch, open a Proposed Change, confirm both checks report failures.

**Acceptance Scenarios**:

1. **Given** `scenarios/ch3_break_validation.yml` is loaded on a branch, **When** a Proposed Change is opened, **Then** `CheckDeviceHostname` fails with a message citing the regex pattern.
2. **Given** the same Proposed Change, **When** checks run, **Then** `CheckDeviceSite` fails citing that the device is assigned to a `LocationMetro` rather than a `LocationSite`.

---

### Edge Cases

- What happens when a Generator run targets a site that has no `mgmt_pool`? The Generator must fail clearly rather than silently skipping IP allocation.
- What happens when `otn-asn-pool` is exhausted? Allocation call returns an error; the Generator should surface it rather than writing `null` to `bgp_asn`.
- What happens if the schema migration removes `bgp_asn` from `OtnSiteDesign` but existing design objects still carry the value? The `state: absent` migration pattern must handle existing data gracefully.
- What if `count: 0` is attempted via the API (not only the UI)? The `min_value: 1` parameter constraint applies at the API layer.

---

## Requirements *(mandatory)*

### Functional Requirements

**Schema**

- **FR-001**: `DcimGenericDevice` MUST expose a `fqdn` computed attribute with template `{{ name__value }}.{{ location__shortname__value }}.otternet.net`; the attribute MUST be `read_only: true` and `optional: true`.
- **FR-002**: `OtnDesignDeviceEntry.count` MUST enforce `min_value: 1` and `max_value: 8` via the `parameters` block (not top-level deprecated fields).
- **FR-003**: `OtnSiteDesign` MUST have the `bgp_asn` attribute removed (marked `state: absent` in the migration).
- **FR-004**: `LocationSite` MUST be extended with a `bgp_asn` attribute (`kind: Number`, `optional: true`) and a `mgmt_pool` relationship (`peer: CoreIPAddressPool`, `cardinality: one`, `optional: true`).

**Objects**

- **FR-005**: The `IpamPrefix` `172.16.0.0/16` MUST exist as the OtterNet management supernet.
- **FR-006**: Per-site `/24` prefixes MUST exist for LON (`172.16.1.0/24`), AMS (`172.16.2.0/24`), and MUC (`172.16.3.0/24`).
- **FR-007**: A `CoreIPAddressPool` MUST exist per site (`lon-mgmt-pool`, `ams-mgmt-pool`, `muc-mgmt-pool`), each backed by its site's `/24` prefix.
- **FR-008**: A `CoreNumberPool` named `otn-asn-pool` MUST exist with `start_range: 65000` and `end_range: 65534`.
- **FR-009**: `objects/06_design_patterns.yml` MUST NOT contain hardcoded `bgp_asn` values on campus design objects.
- **FR-010**: Existing `LocationSite` objects for `lon-01` and `ams-01` MUST have their `mgmt_pool` relationship set to their respective pools.

**Generator**

- **FR-011**: The Generator MUST allocate one BGP ASN from `otn-asn-pool` per site and write it to `LocationSite.bgp_asn`; allocation MUST be idempotent (same site always receives the same ASN).
- **FR-012**: The Generator MUST allocate one management IP from the site's `CoreIPAddressPool` per device and set it as `primary_address`; allocation MUST be idempotent.
- **FR-013**: `queries/campus_site.gql` MUST fetch `mgmt_pool` (id and name) from the `LocationSite` object.

**Transform**

- **FR-014**: `queries/router_config.gql` MUST return `fqdn`, `primary_address` (IP value), and `bgp_asn` sourced from `LocationSite` (not from the design).
- **FR-015**: `transforms/router_config.j2` MUST render hostname from `name`, FQDN from the computed `fqdn` attribute, management IP from `primary_address`, and BGP ASN from `LocationSite.bgp_asn`.

**Proposed Change Scenario**

- **FR-016**: `scenarios/ch3_break_validation.yml` MUST define a device named `my-router-01` assigned to a `LocationMetro` node, suitable for loading on a branch and triggering both Python checks when a Proposed Change is opened.

### Key Entities

- **`DcimGenericDevice`**: Extended with computed `fqdn`; the base generic from which all campus devices inherit.
- **`OtnDesignDeviceEntry`**: Join node linking a design to a device template; `count` now enforces a 1–8 range.
- **`OtnSiteDesign`**: Abstract design blueprint; `bgp_asn` removed — this is now a runtime allocation, not a design property.
- **`LocationSite`**: Physical site; gains `bgp_asn` (Generator-written) and `mgmt_pool` (operator-set relationship to the site's IP pool).
- **`CoreIPAddressPool`**: Built-in Infrahub pool that allocates `IpamIPAddress` objects from a prefix; one per site.
- **`CoreNumberPool`**: Built-in Infrahub pool that allocates integer values from a range; `otn-asn-pool` covers ASNs 65000–65534.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All four schema changes load cleanly — `infrahubctl schema check` reports zero errors after applying the updated schema files.
- **SC-002**: A workshop participant can run `invoke load-objects` once and have all IPAM prefixes, address pools, and the ASN number pool present and queryable without manual intervention.
- **SC-003**: Running the Generator against `muc-01` completes in under 30 seconds and leaves every generated device with a unique management IP and the site with a BGP ASN; re-running produces no changes.
- **SC-004**: The rendered `router_config` artifact for `MUC-RTR-01` contains all five required values (hostname, FQDN, management IP, BGP ASN, banner) with zero hand-typed values — every field is sourced from the SoT or computed by Infrahub.
- **SC-005**: Loading the proposed change scenario on a branch and opening a Proposed Change causes both `CheckDeviceHostname` and `CheckDeviceSite` to report failures within a single check run.

---

## Assumptions

- The `CoreIPAddressPool` and `CoreNumberPool` kinds are built into Infrahub 1.x and require no custom schema definition — only object instances.
- Idempotent allocation in the Generator is achieved by using the resource pool's built-in identifier mechanism (passing a stable `identifier` argument per allocation call), not by querying existing values before allocating.
- The `location__shortname__value` traversal in the `fqdn` Jinja2 template resolves correctly through the `DcimGenericDevice → location` relationship; the `LocationSite.shortname` is always populated.
- The `mgmt_pool` relationship on `LocationSite` is set by a human operator (or the seed data loader) before the Generator runs — the Generator reads it but does not create it.
- Removing `bgp_asn` from `OtnSiteDesign` is a breaking schema migration; the `state: absent` marker handles in-place removal and existing loaded data must not carry the field after migration.
- `objects/06_design_patterns.yml` currently contains `bgp_asn` values on campus design entries; these must be removed before schema migration is applied.
- The proposed change scenario file is a standalone YAML object file (not a Generator or Transform) — it creates a device and a metro location that conflict with existing validation rules.
