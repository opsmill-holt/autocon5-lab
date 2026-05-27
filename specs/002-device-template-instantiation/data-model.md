# Data Model: Device Template Instantiation — Schema

**Branch**: `002-device-template-instantiation` | **Date**: 2026-05-27

---

## New Nodes

### OtnDeviceTemplate

A reusable device blueprint. Users create one instance per device class (e.g., "BorderRouter", "AccessSwitch"). The clone-from-template UX (`generate_template: true`) lets engineers duplicate a golden template when onboarding a new model variant.

| Property | Value |
|----------|-------|
| **Kind** | `OtnDeviceTemplate` |
| **Namespace** | `Otn` |
| **Label** | Device Template |
| **Icon** | `mdi:content-copy` |
| **include_in_menu** | `true` |
| **generate_template** | `true` |
| **human_friendly_id** | `[name__value]` |
| **display_label** | `name__value` |
| **order_by** | `[name__value]` |

**Attributes**:

| Name | Kind | Required | Unique | Notes |
|------|------|----------|--------|-------|
| `name` | Text | yes | yes | Short identifier, e.g. `border-router` |
| `platform` | Text | yes | no | e.g. `IOS-XE`, `IOS-XR`, `EOS` |
| `device_type` | Text | yes | no | e.g. `ISR4451`, `C9300-48P` |
| `role` | Text | no | no | e.g. `edge`, `distribution`, `access` |
| `description` | Text | no | no | Free-text notes |

**Relationships**: none in v1 (back-reference from `OtnDesignDeviceEntry` is implicit via the `device_template__entries` identifier).

**Uniqueness constraints**: `[name__value]`

---

### OtnDesignDeviceEntry

A junction node linking one site design to one device template, with a count indicating how many device instances to create. Multiple entries on the same design model mixed-role deployments (e.g., 2 border routers + 4 access switches).

| Property | Value |
|----------|-------|
| **Kind** | `OtnDesignDeviceEntry` |
| **Namespace** | `Otn` |
| **Label** | Design Device Entry |
| **Icon** | `mdi:counter` |
| **include_in_menu** | `false` |
| **generate_template** | `false` |
| **human_friendly_id** | `[design__name__value, template__name__value]` (composite) |
| **display_label** | `"{{ template__name__value }} ×{{ count__value }}"` |
| **order_by** | `[template__name__value]` |

**Attributes**:

| Name | Kind | Required | Default | Notes |
|------|------|----------|---------|-------|
| `count` | Number | yes | `1` | Number of instances to create; must be ≥ 1 |

**Relationships**:

| Name | Peer | Kind | Cardinality | Optional | on_delete | Identifier |
|------|------|------|-------------|----------|-----------|------------|
| `design` | `OtnSiteDesign` | Attribute | one | no | no-action | `design__device_entries` |
| `template` | `OtnDeviceTemplate` | Attribute | one | no | no-action | `device_template__entries` |

**Uniqueness constraints**: The combination of (design, template) must be unique — enforced via a check (not schema constraint), since Infrahub uniqueness constraints on relationship traversal require extra care. See FR-007 in spec.

---

## Modified Generics

### OtnSiteDesign (existing generic — add relationship)

Add the back-reference for `OtnDesignDeviceEntry` entries:

| Name | Peer | Kind | Cardinality | Optional | on_delete | Identifier |
|------|------|------|-------------|----------|-----------|------------|
| `device_entries` | `OtnDesignDeviceEntry` | Component | many | yes | cascade | `design__device_entries` |

No attributes are added or removed. All existing concrete subtypes (`OtnCampusSite`, `OtnDataCenterSite`) inherit this relationship automatically.

---

## Unchanged Nodes

`OtnCampusSite` and `OtnDataCenterSite` — no changes. Their existing count attributes (`router_count`, `access_switch_count`, etc.) are preserved for backward compatibility with the existing generator.

---

## Entity Relationship Diagram (text)

```
OtnSiteDesign (generic)
  └─ device_entries [Component, many] ──→ OtnDesignDeviceEntry
                                               │
                                               ├─ count: Number
                                               └─ template [Attribute, one] ──→ OtnDeviceTemplate
                                                                                    ├─ name
                                                                                    ├─ platform
                                                                                    ├─ device_type
                                                                                    └─ role

OtnCampusSite    inherits OtnSiteDesign  (unchanged)
OtnDataCenterSite inherits OtnSiteDesign (unchanged)
```

---

## Schema YAML (target state for `schemas/otn.yml` additions)

```yaml
# New node — add to `nodes:` list
- name: DeviceTemplate
  namespace: Otn
  label: Device Template
  icon: mdi:content-copy
  include_in_menu: true
  generate_template: true
  human_friendly_id:
    - name__value
  display_label: name__value
  order_by:
    - name__value
  uniqueness_constraints:
    - [name__value]
  attributes:
    - name: name
      kind: Text
      unique: true
      order_weight: 1000
    - name: platform
      kind: Text
      order_weight: 1100
    - name: device_type
      kind: Text
      order_weight: 1200
    - name: role
      kind: Text
      optional: true
      order_weight: 1300
    - name: description
      kind: Text
      optional: true
      order_weight: 1400

# New node — add to `nodes:` list
- name: DesignDeviceEntry
  namespace: Otn
  label: Design Device Entry
  icon: mdi:counter
  include_in_menu: false
  human_friendly_id:
    - design__name__value
    - template__name__value
  display_label: "{{ template__name__value }} \xD7{{ count__value }}"
  order_by:
    - template__name__value
  attributes:
    - name: count
      kind: Number
      default_value: 1
      order_weight: 1000
  relationships:
    - name: design
      peer: OtnSiteDesign
      kind: Parent
      cardinality: one
      optional: false
      identifier: design__device_entries
      order_weight: 2000
    - name: template
      peer: OtnDeviceTemplate
      kind: Attribute
      cardinality: one
      optional: false
      on_delete: no-action
      identifier: device_template__entries
      order_weight: 2100

# Modification — add to `OtnSiteDesign` generic in `generics:` list
# (add inside its `relationships:` block, or create the block if absent)
- name: device_entries
  peer: OtnDesignDeviceEntry
  kind: Component
  cardinality: many
  optional: true
  on_delete: cascade
  identifier: design__device_entries
  order_weight: 2000
```

---

## Validation Steps

1. Run `uv run infrahubctl schema check schemas/` — must return zero errors.
2. Run `uv run infrahubctl schema load schemas/` — must apply cleanly.
3. Verify `OtnDeviceTemplate` and `OtnDesignDeviceEntry` appear in the Infrahub UI.
4. Create one `OtnDeviceTemplate` and one `OtnDesignDeviceEntry` via the UI; verify they link correctly.
5. Verify existing `OtnCampusSite` and `OtnDataCenterSite` objects are unaffected.
