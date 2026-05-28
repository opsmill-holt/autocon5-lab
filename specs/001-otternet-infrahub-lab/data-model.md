# Data Model: OtterNet Infrahub Lab

## OTN Schema Nodes

### OtnSiteDesign (Generic)

Abstract base for all site design blueprints.

| Attribute | Kind | Optional | Default | Notes |
|-----------|------|----------|---------|-------|
| `name` | Text | No | — | Unique; uniqueness_constraint on `name__value` |
| `description` | Text | Yes | — | Free text |
| `router_count` | Number | No | 1 | Routers per site |
| `bgp_asn` | Number | Yes | — | BGP ASN used in Transform rendering |

**Relationship**:
- `site` → `LocationSite` — kind: Attribute, cardinality: one, optional: true — identifier: `site_design__site`

**Display**: `human_friendly_id: [name__value]`, `display_label: name__value`

---

### OtnCampusSite (Node)

Concrete campus design. Inherits `OtnSiteDesign` + `CoreArtifactTarget`.

| Attribute | Kind | Optional | Default |
|-----------|------|----------|---------|
| `access_switch_count` | Number | No | 1 |
| `distribution_switch_count` | Number | No | 0 |

**Uniqueness**: `[name__value]`
**menu_placement**: `OtnSiteDesign`

---

### OtnDataCenterSite (Node)

Concrete data center design. Inherits `OtnSiteDesign` + `CoreArtifactTarget`.

| Attribute | Kind | Optional | Default |
|-----------|------|----------|---------|
| `spine_count` | Number | No | 2 |
| `leaf_count` | Number | No | 4 |
| `border_leaf_count` | Number | No | 2 |

**Uniqueness**: `[name__value]`
**menu_placement**: `OtnSiteDesign`

---

## Schema Library Nodes (used, not modified)

| Kind | Purpose in Lab |
|------|----------------|
| `LocationCountry` | UK, Netherlands |
| `LocationMetro` | London, Amsterdam |
| `LocationSite` | lon-01, ams-01, muc-01 |
| `DcimPhysicalDevice` | All devices (routers, switches) |
| `DcimInterface` | Interfaces per device |
| `DcimPlatform` | IOS-XE (routers), IOS (switches) |
| `DcimDeviceType` | ISR4451 (router), C9300 (switch) |
| `OrganizationManufacturer` | Cisco |

---

## Seed Data Instances

### Design Instances

| Name | Kind | router_count | access_sw | dist_sw | bgp_asn |
|------|------|-------------|-----------|---------|---------|
| small-campus | OtnCampusSite | 1 | 1 | 0 | 65001 |
| medium-campus | OtnCampusSite | 1 | 2 | 1 | 65002 |
| large-campus | OtnCampusSite | 2 | 4 | 2 | 65003 |
| dc-standard | OtnDataCenterSite | — | — | — | — (spine:2, leaf:4, bleaf:2) |

### Sites

| Shortname | Name | Location | Design |
|-----------|------|----------|--------|
| lon-01 | London Site 01 | UK → London | large-campus |
| ams-01 | Amsterdam Site 01 | Netherlands → Amsterdam | medium-campus |

### Device Counts per Site (seed)

**lon-01 (large campus)**: LON-RTR-01, LON-RTR-02, LON-DSW-01, LON-DSW-02, LON-ASW-01..04 → 8 devices

**ams-01 (medium campus)**: AMS-RTR-01, AMS-DSW-01, AMS-ASW-01, AMS-ASW-02 → 4 devices

---

## Generator Output Schema

When `CampusSiteGenerator` runs on a `OtnCampusSite` target:

```
DcimPhysicalDevice
  name: "{SITE_CODE}-{ROLE}-{INDEX:02d}"
  device_type: → DcimDeviceType (ISR4451 for RTR, C9300 for ASW/DSW)
  platform: → DcimPlatform
  site: → LocationSite (the site linked in the design)

DcimInterface (Component of DcimPhysicalDevice)
  name: "{interface_name}"
  device: → parent device
```

Role-to-device mapping:
- `router_count` → RTR devices (ISR4451)
- `distribution_switch_count` → DSW devices (C9300-48)
- `access_switch_count` → ASW devices (C9300-24)

---

## Validation Rules

| Rule | Enforced by | Pattern |
|------|-------------|---------|
| Unique site name | Schema uniqueness_constraint | `[name__value]` on `OtnSiteDesign` subtypes |
| Unique LocationSite shortname | Schema library | `unique: true` on `shortname` |
| Hostname format | `CheckDeviceHostname` | `^[A-Z]{3}-[A-Z]{2,5}-\d{2}$` |
| Device must have site | `CheckDeviceSite` | non-null `site` relationship |
| Referential integrity | Infrahub core | Peer kind validation at load time |
