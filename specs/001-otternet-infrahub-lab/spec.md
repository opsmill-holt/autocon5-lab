# Feature Specification: OtterNet Infrahub Lab — Full Implementation

**Feature Branch**: `001-otternet-infrahub-lab`
**Created**: 2026-05-26
**Status**: Draft
**Input**: LAB_DESIGN.md — AutoCon 5 Munich workshop, June 2026

---

## Overview

OtterNet is a managed services provider that must deploy 6 new customer sites across Europe in 30 days. The current manual process (device records, IP assignment, config by hand) takes 2 days per site. This lab builds an Infrahub Source of Truth that reduces new-site deployment to under 5 minutes.

The implementation covers all five Infrahub artifact types in dependency order:

1. **Schema** — OTN namespace generics and design nodes
2. **Objects** — Seed data (two existing sites, four design instances)
3. **Checks** — Enforcement rules for proposed changes
4. **Generator** — Design-driven site provisioning
5. **Transform** — Jinja2 device config rendering

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Schema Extension: Model Site Design Tiers (Priority: P1)

A network architect extends the Infrahub schema with OtterNet-specific design nodes so that each site can be stamped with a reusable design blueprint (small campus, medium campus, large campus, or data center) rather than manually specifying device counts each time.

**Why this priority**: Every other artifact (objects, generator, transform) depends on the data model being in place first.

**Independent Test**: Can be fully tested by loading the OTN schema into Infrahub and verifying that `OtnSiteDesign`, `OtnCampusSite`, and `OtnDataCenterSite` kinds are visible and accept valid objects.

**Acceptance Scenarios**:

1. **Given** a blank Infrahub with only the schema library loaded, **When** the OTN schema is loaded via `infrahubctl schema load schemas/`, **Then** all three OTN kinds appear in the schema list with no validation errors.
2. **Given** the OTN schema is loaded, **When** a user creates a `CampusSite` object with `router_count=1`, `access_switch_count=1`, `distribution_switch_count=0`, **Then** the object is saved and retrievable by name.
3. **Given** the OTN schema is loaded, **When** a user attempts to create a second `SiteDesign` with the same name, **Then** a uniqueness constraint error is returned.

---

### User Story 2 — Seed Data: Two Existing Sites Pre-Loaded (Priority: P1)

An operations engineer runs a single load command and sees two existing OtterNet sites (`lon-01`, `ams-01`) fully represented in Infrahub, each with the correct design tier, location hierarchy (country → metro → site), and associated devices.

**Why this priority**: The seed data is the baseline state that every workshop challenge starts from.

**Independent Test**: Run `infrahubctl object load objects/` and verify `lon-01` (London, large campus) and `ams-01` (Amsterdam, medium campus) exist with their design objects and device records.

**Acceptance Scenarios**:

1. **Given** a fresh Infrahub with schema loaded, **When** `infrahubctl object load objects/` completes, **Then** two sites, four design instances, and all associated device objects are present.
2. **Given** the seed data is loaded, **When** a GraphQL query lists all sites with their design, **Then** `lon-01` returns `large` campus design and `ams-01` returns `medium` campus design.

---

### User Story 3 — Enforcement: Invalid Changes Are Blocked (Priority: P2)

A student attempts several invalid operations during the workshop (duplicate site, device without site, hostname violating naming pattern, bad proposed change) and observes that Infrahub's enforcement mechanisms block each one with a clear error message.

**Why this priority**: Demonstrates the Enforcement pillar — schema constraints and Python checks are the SoT's safety net.

**Independent Test**: Attempt each invalid operation via the Infrahub UI or `infrahubctl` and verify the expected error is returned.

**Acceptance Scenarios**:

1. **Given** `lon-01` exists, **When** a user attempts to create another site with shortname `lon-01`, **Then** a uniqueness constraint error fires.
2. **Given** the schema is loaded, **When** a user attempts to create a device with a hostname that does not match `^[A-Z]{3}-[A-Z]{2,3}-\d{2}$`, **Then** a regex validation error fires.
3. **Given** a proposed change branch contains a device with no site relationship, **When** the Python check runs, **Then** the check reports a failure and the merge is blocked.

---

### User Story 4 — Generator: Deploy a New Site in Under 5 Minutes (Priority: P1)

A student selects the `muc-01` Munich small-campus site design and runs the Infrahub Generator. Within 5 minutes, Infrahub has automatically created all device objects (`MUC-RTR-01`, `MUC-SW-01`), interface objects, and site relationships — without any manual record creation.

**Why this priority**: This is the core payoff of the workshop — moving from 2 days to 5 minutes per site.

**Independent Test**: Create a `CampusSite` design object for Munich (small campus), run the Generator, and verify all expected device and interface objects are created in Infrahub.

**Acceptance Scenarios**:

1. **Given** a `CampusSite` design for Munich (`muc-01`, small campus) exists, **When** the Generator runs, **Then** `MUC-RTR-01` and `MUC-SW-01` device objects are created and linked to the `muc-01` site.
2. **Given** the Generator has run, **When** it runs again on the same design, **Then** no duplicate objects are created (idempotent).
3. **Given** the Generator has created devices, **When** a GraphQL query lists devices for site `muc-01`, **Then** the correct count matches the small campus design tier (1 router, 1 access switch).

---

### User Story 5 — Transform: Render a Deployable Device Config (Priority: P2)

A student requests the rendered configuration for `MUC-RTR-01` and receives a complete, deployment-ready config file with hostname, interface IPs, BGP ASN from the site design, and the OtterNet management banner — all sourced from the SoT with no manual editing.

**Why this priority**: Closes the SoT arc (schema → objects → generator → deployable config), giving students the full end-to-end picture.

**Independent Test**: Run the Jinja2 Transform for `MUC-RTR-01` and verify the output contains the correct hostname, at least one interface, a BGP ASN, and the `! Managed by OtterNet SoT` banner.

**Acceptance Scenarios**:

1. **Given** `MUC-RTR-01` exists in Infrahub, **When** the Transform is executed, **Then** the output contains `hostname MUC-RTR-01` and `! Managed by OtterNet SoT`.
2. **Given** the Transform runs, **When** any interface IP changes in the SoT, **Then** re-running the Transform reflects the updated IP without modifying the template.

---

### Edge Cases

- What happens when a Generator runs on a design with zero devices of a given type? (e.g., medium campus with 0 border-leaf) — Generator must skip gracefully, not error.
- How does the Transform handle a device with no primary IP assigned? — Render with a placeholder comment rather than failing.
- What happens when the schema library nodes are not loaded before the OTN schema? — `infrahubctl schema load` must fail with a clear missing-peer error.

---

## Requirements *(mandatory)*

### Functional Requirements

**Schema:**
- **FR-001**: System MUST expose an `OtnSiteDesign` generic with `name`, `description`, and `router_count` attributes.
- **FR-002**: System MUST expose an `OtnCampusSite` node inheriting from `OtnSiteDesign` with `access_switch_count` and `distribution_switch_count` attributes.
- **FR-003**: System MUST expose an `OtnDataCenterSite` node inheriting from `OtnSiteDesign` with `spine_count`, `leaf_count`, and `border_leaf_count` attributes.
- **FR-004**: Both concrete design nodes MUST enforce a uniqueness constraint on `name`.
- **FR-005**: Both concrete design nodes MUST inherit `CoreArtifactTarget` so Generator and Transform definitions can target them.
- **FR-006**: The `OtnSiteDesign` generic MUST carry a relationship to `LocationSite` so each design can be linked to a physical site.

**Objects:**
- **FR-007**: The objects directory MUST contain seed data for two sites: `lon-01` (London, large campus) and `ams-01` (Amsterdam, medium campus).
- **FR-008**: The objects directory MUST contain four design instances: small campus, medium campus, large campus, and data center.
- **FR-009**: Each site seed object MUST include the correct location hierarchy: country → metro → site.
- **FR-010**: Each site seed object MUST reference a device type, platform, and device objects matching its design tier.

**Checks:**
- **FR-011**: A Python check MUST validate that device hostnames match the pattern `^[A-Z]{3}-[A-Z]{2,3}-\d{2}$`.
- **FR-012**: A Python check MUST validate that every device has a non-null site relationship.
- **FR-013**: Checks MUST run automatically on proposed changes and block merges on failure.

**Generator:**
- **FR-014**: The Generator MUST read an `OtnCampusSite` design object and create device objects named by convention (e.g., `MUC-RTR-01`, `MUC-SW-01`, `MUC-DSW-01`, `MUC-ASW-01`).
- **FR-015**: The Generator MUST create interface objects linked to each device.
- **FR-016**: The Generator MUST be idempotent — re-running on the same design MUST NOT create duplicates.
- **FR-017**: The Generator MUST link all created devices to the target site.

**Transform:**
- **FR-018**: A Jinja2 Transform MUST render a router configuration for any device matching a target group.
- **FR-019**: The rendered config MUST include: hostname, interface definitions, BGP ASN (from site design), and the banner `! Managed by OtterNet SoT`.
- **FR-020**: The Transform MUST be registered as an `artifact_definition` in `.infrahub.yml` targeting `OtnCampusSite` instances.

### Key Entities

- **OtnSiteDesign** (generic): Abstract design blueprint. Attributes: `name` (Text, unique), `description` (Text, optional), `router_count` (Number). Relationship: `site` → `LocationSite` (one, optional).
- **OtnCampusSite** (node): Concrete campus design. Inherits `OtnSiteDesign`. Adds: `access_switch_count` (Number), `distribution_switch_count` (Number).
- **OtnDataCenterSite** (node): Concrete DC design. Inherits `OtnSiteDesign`. Adds: `spine_count` (Number), `leaf_count` (Number), `border_leaf_count` (Number).
- **LocationSite**: From schema library — represents a physical site. Existing node, not modified.
- **DcimGenericDevice**: From schema library — base device node with `name`, `interfaces`, `primary_address`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new site can be fully provisioned (all device and interface objects created in Infrahub) in under 5 minutes from selecting the design.
- **SC-002**: All 5 schema validation constraints (uniqueness, hostname regex, site relationship, referential integrity) fire correctly and return actionable error messages.
- **SC-003**: The Generator produces the exact device count specified by the design tier (e.g., small campus → 1 router + 1 access switch, no more, no less).
- **SC-004**: The Transform output is a syntactically valid router configuration file that can be applied without manual editing.
- **SC-005**: Re-running the Generator on an already-provisioned site results in zero new objects created.
- **SC-006**: 100% of seed data loads without errors on a fresh Infrahub instance with schema library pre-loaded.

---

## Assumptions

- The Infrahub schema library (`base/` and `location_minimal/`) is loaded before the OTN schema. The lab bootstrap command handles this ordering.
- Devices modeled in this lab are logical Infrahub objects only — no actual network devices are provisioned.
- IP address allocation is out of scope for the Generator (stretch goal only); interface objects are created without IP assignments in the base implementation.
- BGP ASN values for the Transform are stored as an attribute on `OtnCampusSite` (added to schema) — a fixed value per design instance.
- The hostname convention `<SITE>-<ROLE>-<NUM>` uses the 3-letter site code (MUC, LON, AMS) derived from the site shortname.
- `OtnDataCenterSite` generator support is a stretch goal; the base Generator targets `OtnCampusSite` only.
- Object YAML files follow the Infrahub `infrahubctl object load` format.
- The lab runs on Infrahub 1.9.6 as confirmed by `infrahubctl info`.
