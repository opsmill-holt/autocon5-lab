# OtterNet Infrahub Lab — Design Document

AutoCon 5 · Munich · June 2026

---

## Scenario

**Company:** OtterNet — a fast-growing managed services provider deploying new customer sites across Europe.

> *OtterNet just signed 3 new enterprise customers and needs to deploy 6 new sites in 30 days. The current process takes 2 days per site — manually creating device records, assigning IPs, and building configs by hand. Your job today: build a Source of Truth that makes deploying a new site a 5-minute job.*

---

## Workshop Context

- **Platform:** Instruqt (each challenge starts in a predictable pre-configured state)
- **Time slot:** 2pm–6pm (~3.5 hours including one break)
- **Difficulty:** Intermediate
- **Pillars covered:** All 6 SoT building blocks from [Designing Network Automation at Scale](https://designingnetworkautomation.com/series/part2-architectural-building-blocks/04-source-of-truth/) — Modeling, Design-Driven, Consumption, Enforcement, Versioning, Aggregation

---

## Skill Level Strategy

One Instruqt track with three tiers per challenge:

| Tier | Description |
|------|-------------|
| **Guided** | Step-by-step instructions with copy-paste code snippets |
| **Stretch goals** | Unlocked when the core task is complete |
| **Bonus** | Open-ended, no instructions — for the fastest students |

---

## Seed Data

Two existing OtterNet sites are pre-loaded by the bootstrap script:

| Site | Location | Design |
|------|----------|--------|
| `lon-01` | London | Large campus |
| `ams-01` | Amsterdam | Medium campus |

---

## Site Design Tiers

Device counts are stored as `OtnDesignDeviceEntry` records linked to each design, not as fixed attributes.

| Design | Type | Device entries |
|--------|------|----------------|
| `small-campus` | `OtnCampusSite` | 1× border-router, 1× access-switch |
| `medium-campus` | `OtnCampusSite` | 1× border-router, 1× distribution-switch, 2× access-switches |
| `large-campus` | `OtnCampusSite` | 2× border-router, 2× distribution-switch, 4× access-switches |
| `dc-standard` | `OtnDataCenterSite` | 2× spine, 4× leaf, 2× border-leaf |

---

## Schema Design

Base nodes (locations, devices, interfaces) are loaded from the **Infrahub schema library**.

OtterNet-specific schema uses **generics and inheritance**:

- `OtnSiteDesign` — Infrahub generic (abstract base: `name`, `description`, `bgp_asn`)
  - `OtnCampusSite` — inherits from `OtnSiteDesign`; also inherits `CoreArtifactTarget` (enables config artifact generation)
  - `OtnDataCenterSite` — inherits from `OtnSiteDesign`; also inherits `CoreArtifactTarget`

- `OtnDesignDeviceEntry` — join node that links a design to a `TemplateDcimDevice` with a `count`; owned by the design via a `Component` relationship (cascade-deleted with the design)

- `LocationSite` is extended with a `design` relationship pointing to `OtnSiteDesign`, linking a physical site to its design blueprint

---

## Challenge Map

### Challenge 1 — Orientation & Setup (20 min)
**Pillar:** Foundation

Students bootstrap a blank Infrahub into a working OtterNet environment:

```bash
invoke schema-library-get        # pull schema library locally
infrahubctl schema load schemas/ # load schema into Infrahub
invoke load-objects              # load OtterNet seed data
```

---

### Challenge 2 — Modeling (45 min)
**Pillar:** Modeling

Students extend the schema with OtterNet-specific design nodes:

1. Create the `OtnSiteDesign` generic with shared base fields (`name`, `description`, `bgp_asn`)
2. Create `OtnCampusSite` inheriting from `OtnSiteDesign` (and `CoreArtifactTarget`)
3. Create `OtnDataCenterSite` inheriting from `OtnSiteDesign` (and `CoreArtifactTarget`)
4. Create `OtnDesignDeviceEntry` to link designs to device templates with a `count`
5. Extend `LocationSite` with a `design` relationship
6. Populate 3 campus design instances (small, medium, large) + 1 DC design instance, each with `OtnDesignDeviceEntry` records that map to the correct device templates and counts
7. Link `lon-01` → `large-campus` and `ams-01` → `medium-campus`

**Stretch goal:** Add additional attributes to `OtnSiteDesign` (e.g. uplink speed, firewall flag).
**Bonus:** Design a second generic hierarchy for a new service type.

---

### Challenge 3 — Consumption & Enforcement (30 min)
**Pillar:** Consumption + Enforcement

Students query OtterNet data and observe enforcement in action:

**Consumption:**
- GraphQL query to list all devices and their site
- Filtered query by site type

**Enforcement triggers:**
- Attempt to create a duplicate site (`lon-01` already exists → uniqueness constraint fires)
- Attempt to create a device with no site relationship → referential integrity fires
- Attempt to set a hostname that violates a regex pattern → schema constraint fires
- Create a branch, propose a bad change → Python check fires and blocks the merge

**Versioning is introduced here naturally** — the Python check runs on a proposed change branch.

---

### Challenge 4 — Design-Driven / Generator (60 min)
**Pillar:** Design-Driven

Students implement a full Infrahub Generator from scratch that deploys a new site.

**Target:** Deploy `muc-01` — Munich, small campus (conference tie-in).

The Generator reads a `CampusSite` design object and produces:
- Device objects (named by convention, e.g. `MUC-RTR-01`, `MUC-SW-01`)
- Interface objects linked to each device
- Relationships between devices and the site

**Guided tier:** Instruqt walks through each section line by line. [Infrahub Generator docs](https://docs.infrahub.app) linked as reference.
**Stretch goal:** Extend the Generator to support `DataCenterSite`.
**Bonus:** Add IP address allocation to the Generator output.

---

### Challenge 5 — Transforms / Config Rendering (30 min)
**Pillar:** Consumption (Transforms)

Students write a Jinja2 Transform that renders a device config for `MUC-RTR-01`:

- Hostname from the device name
- Interface IPs from the SoT
- BGP ASN from the site design
- Banner: `! Managed by OtterNet SoT`

**Payoff moment:** The SoT arc is complete — schema → objects → Generator → deployable config.

**Stretch goal:** Render configs for all devices in `muc-01` in one Transform.

---

### Bonus — Aggregation (stretch)
**Pillar:** Aggregation

Fast students only. Pull external data into Infrahub from a mock source (CSV/JSON) using a sync script. Demonstrates the "pull data in from other systems" pillar.

---

## Versioning

Not a standalone challenge — woven throughout:
- Every change students make is versioned automatically
- Challenge 3 explicitly uses branches for the Python check demo
- Challenge 4 Generator run can be proposed via a branch and merged
