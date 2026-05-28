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

- `OtnSiteDesign` — Infrahub generic (abstract base: `name`, `description`)
  - `OtnCampusSite` — inherits from `OtnSiteDesign`; also inherits `CoreArtifactTarget` (enables config artifact generation)
  - `OtnDataCenterSite` — inherits from `OtnSiteDesign`; also inherits `CoreArtifactTarget`

- `OtnDesignDeviceEntry` — join node that links a design to a `TemplateDcimDevice` with a `count` (min: 1, max: 8); owned by the design via a `Component` relationship (cascade-deleted with the design)

- `LocationSite` is extended with:
  - `design` — relationship to `OtnSiteDesign`, linking a physical site to its design blueprint
  - `bgp_asn` — allocated by the Generator from a `CoreNumberPool` (not stored on the design)
  - `mgmt_prefix` — relationship to `IpamPrefix` (the site's `/24` management subnet); the Generator looks up the `CoreIPAddressPool` that references this prefix and allocates IPs from it

- `DcimGenericDevice` has a **computed attribute** `fqdn` — dynamically calculated as `{{ name }}.{{ location__shortname }}.otternet.net`. This is never stored manually; Infrahub computes it on read.

### IPAM & Resource Pool Seed Data

Pre-loaded alongside locations and devices:

| Object | Kind | Purpose |
|--------|------|---------|
| `172.16.0.0/16` | `IpamPrefix` (supernet) | OtterNet management address space |
| `172.16.0.0/24` | `IpamPrefix` (management) | LON site management subnet |
| `172.16.1.0/24` | `IpamPrefix` (management) | AMS site management subnet |
| `172.16.2.0/24` | `IpamPrefix` (management) | MUC site management subnet |
| `lon-mgmt-pool` | `CoreIPAddressPool` | Allocates management IPs for LON devices (resources: `172.16.0.0/24`) |
| `ams-mgmt-pool` | `CoreIPAddressPool` | Allocates management IPs for AMS devices (resources: `172.16.1.0/24`) |
| `muc-mgmt-pool` | `CoreIPAddressPool` | Allocates management IPs for MUC devices (resources: `172.16.2.0/24`) |
| `otn-mgmt-prefix-pool` | `CoreIPPrefixPool` | Allocates `/24` management subnets from `172.16.0.0/16` for new sites |
| `otn-asn-pool` | `CoreNumberPool` | Private ASN range 65000–65534; one ASN allocated per deployed site |

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

1. Create the `OtnSiteDesign` generic with shared base fields (`name`, `description`)
2. Create `OtnCampusSite` inheriting from `OtnSiteDesign` (and `CoreArtifactTarget`)
3. Create `OtnDataCenterSite` inheriting from `OtnSiteDesign` (and `CoreArtifactTarget`)
4. Create `OtnDesignDeviceEntry` to link designs to device templates with a `count`; add `min_count: 1` and `max_count: 8` — try setting `count: 0` to see schema enforcement fire immediately (no Python needed)
5. Extend `LocationSite` with a `design` relationship, a `bgp_asn` Number attribute, and a `mgmt_prefix` relationship to `IpamPrefix`
6. Add a `fqdn` **computed attribute** to `DcimGenericDevice` using the template `{{ name }}.{{ location__shortname }}.otternet.net` — Infrahub calculates this dynamically on every read; it is never stored manually
7. Populate 3 campus design instances (small, medium, large) + 1 DC design instance, each with `OtnDesignDeviceEntry` records that map to the correct device templates and counts
8. Link `lon-01` → `large-campus` and `ams-01` → `medium-campus`

**Stretch goal:** Add additional attributes to `OtnSiteDesign` (e.g. uplink speed, firewall flag).
**Bonus:** Design a second generic hierarchy for a new service type.

---

### Challenge 3 — Consumption & Enforcement (30 min)
**Pillar:** Consumption + Enforcement

Students query OtterNet data and observe enforcement in action:

**Consumption:**
- GraphQL query to list all devices and their site
- Filtered query by site type

**Enforcement triggers (layered — cheapest to most expensive):**

| Layer | Trigger | What fires |
|-------|---------|-----------|
| Schema | Set `OtnDesignDeviceEntry.count` to `0` | Immediate rejection — `min_count: 1` |
| Uniqueness | Create a second site with shortname `lon-01` | Uniqueness constraint, no Python needed |
| Referential integrity | Create a device with no location | Referential integrity check |
| Regex (schema) | Set a device hostname to `my-router` | Schema regex `^[A-Z]{3}-[A-Z]{2,5}-\d{2}$` rejects it |
| Python check (async) | Proposed change with bad data | `CheckDeviceHostname` and `CheckDeviceSite` fire and block merge |

**Proposed change scenario (concrete steps):**
1. Student creates a branch in the UI (or via `infrahubctl`)
2. On the branch: loads `scenarios/ch3_break_validation.yml` — a device named `my-router-01` assigned to a `LocationMetro` instead of a `LocationSite`
3. Opens a **Proposed Change** targeting `main`
4. Both Python checks fire automatically: hostname regex fails, site-type check fails
5. Student fixes the hostname and location on the branch
6. Checks re-run and pass → student merges

**Versioning is introduced here naturally** — the branch, proposed change, and merge are all versioned and visible in the audit trail.

---

### Challenge 4 — Design-Driven / Generator (60 min)
**Pillar:** Design-Driven

Students implement a full Infrahub Generator from scratch that deploys a new site.

**Target:** Deploy `muc-01` — Munich, small campus (conference tie-in).

The Generator reads a `CampusSite` design object and produces:
- Device objects (named by convention, e.g. `MUC-RTR-01`, `MUC-ASW-01`)
- Interface objects linked to each device (from device template)
- A unique BGP ASN allocated from `otn-asn-pool` (`CoreNumberPool`), written to `LocationSite.bgp_asn`
- A management IP per device allocated from the `CoreIPAddressPool` whose resources include the site's `mgmt_prefix`, attached to the management interface and set as `primary_address`
- All devices added to the `device_config` group for artifact targeting

**Resource allocation order in the Generator:**
1. Allocate BGP ASN from `CoreNumberPool` — idempotent (same site always gets the same ASN)
2. Resolve the `CoreIPAddressPool` whose resources include the site's `mgmt_prefix`
3. For each device: allocate management IP from that pool using the hostname as identifier — idempotent (same hostname always returns the same IP)
4. Create/upsert device with `primary_address` set

**Guided tier:** Instruqt walks through each section line by line. [Infrahub Generator docs](https://docs.infrahub.app) linked as reference.
**Stretch goal:** Extend the Generator to support `DataCenterSite`.
**Bonus:** Allocate loopback IPs from a second prefix pool and add them to Loopback0 interfaces.

---

### Challenge 5 — Transforms / Config Rendering (30 min)
**Pillar:** Consumption (Transforms)

Students write a Jinja2 Transform that renders a device config for `MUC-RTR-01`:

- Hostname from the device name
- FQDN from the computed attribute (`fqdn`) — no manual string building
- Management IP from `primary_address` (allocated by the Generator)
- Interface IPs from the SoT
- BGP ASN from `LocationSite.bgp_asn` (allocated by the Generator from the number pool)
- Banner: `! Managed by OtterNet SoT`

**Payoff moment:** The SoT arc is complete — schema → resource pools → Generator → deployable config. Every value in the config was either modeled, computed, or allocated by Infrahub — nothing was typed by hand.

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
