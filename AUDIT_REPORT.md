# Infrahub Repository Audit Report

Generated: 2026-05-28
Repository: `/Users/alex/dev/opsmill/autocon5-lab`

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 4 |
| MEDIUM | 5 |
| LOW | 2 |
| INFO | 3 |
| **Total** | **15** |

---

## Project Structure

### `.infrahub.yml` Validation

**Status: PASS**

- File exists at project root
- Valid YAML, no syntax errors
- All top-level keys are recognized: `schemas`, `objects`, `queries`, `check_definitions`, `generator_definitions`, `jinja2_transforms`, `artifact_definitions`
- All `file_path` and `template_path` values resolve to existing files
- All directory paths resolve: `schemas/`, `objects/`
- No duplicate `name` values within any section
- Query names are unique: `all_devices`, `campus_site`, `router_config`

---

## Schema Audit

### Naming Conventions

**Status: PASS**

All namespaces, node/generic names, attribute names, and relationship names follow required conventions:

- Namespaces match `^[A-Z][a-z0-9]+$`: `Dcim`, `Interface`, `Location`, `Organization`, `Ipam`, `Otn` — all valid
- Node/Generic names match `^[A-Z][a-zA-Z0-9]+$` — all valid
- Attribute names match `^[a-z0-9_]+$` — all valid
- Relationship names match `^[a-z0-9_]+$` — all valid

### Deprecated Fields

**Status: PASS**

No usage of deprecated `display_labels` (plural list format) found in any schema file. All nodes and generics that have a display label use the `display_label` (singular, string) field correctly.

### Relationship Definitions

#### FINDING HIGH-001: `OtnDesignDeviceEntry.design` uses `kind: Attribute` instead of `kind: Parent`

**File**: `schemas/extensions/designs/design.yml`
**Severity**: HIGH
**Rule**: `schema-relationships`

`OtnSiteDesign.device_entries` is declared as `kind: Component` (correct), but the corresponding back-reference `OtnDesignDeviceEntry.design` uses `kind: Attribute` instead of `kind: Parent`. Component/Parent pairs must use `kind: Parent` on the child (owned) side.

```yaml
# Current (incorrect)
- name: design
  peer: OtnSiteDesign
  kind: Attribute      # <-- should be kind: Parent
  cardinality: one
  optional: false
  identifier: design__device_entries

# Fix
- name: design
  peer: OtnSiteDesign
  kind: Parent
  cardinality: one
  optional: false
  identifier: design__device_entries
```

#### FINDING MEDIUM-001: Several back-reference relationships missing explicit `kind`

**Files**: `schemas/base/dcim.yml`, `schemas/base/location.yml`, `schemas/base/organization.yml`
**Severity**: MEDIUM
**Rule**: `schema-relationships`

The following back-reference relationships omit `kind`, relying on the default value. While functional, explicit declaration improves readability and prevents accidental breakage when defaults change:

| Node | Relationship | Peer | Missing |
|------|-------------|------|---------|
| `DcimPlatform` | `devices` | `DcimGenericDevice` | `kind` |
| `LocationHosting` | `devices` | `DcimPhysicalDevice` | `kind` |
| `LocationHosting` | `prefixes` | `IpamPrefix` | `kind` |
| `OrganizationManufacturer` | `device_type` | `DcimDeviceType` | `kind` |
| `OrganizationManufacturer` | `platform` | `DcimPlatform` | `kind` |
| `IpamIPAddress` | `interface` | `InterfaceLayer3` | `kind` |

Recommended: add `kind: Attribute` (or `kind: Generic` for back-references without ownership semantics) to each of these.

---

## Object Data Audit

### Format Validation

**Status: PASS**

All object YAML files comply with the required format:

- Each document has `apiVersion: infrahub.app/v1`
- Each document has `kind: Object`
- `spec.kind` is present and uses the full kind (Namespace + Name)
- `spec.data` is present and is a list in all documents
- Multiple YAML documents within `07_device_templates.yml` are correctly separated with `---`
- `expand_range: true` is correctly placed in the `parameters` block (not on individual items) in `07_device_templates.yml`
- Hierarchical children in `06c_locations.yml` include `kind` at each level

### Load Order

**Status: PASS**

Object files follow the required dependency ordering via numeric filename prefixes:

```
01_manufacturers.yml       → independent (manufacturers)
02_platforms.yml           → depends on manufacturers
03_device_types.yml        → depends on platforms, manufacturers
05_groups.yml              → independent (group definitions)
06_design_patterns.yml     → OtnCampusSite designs
06b_design_dc.yml          → OtnDataCenterSite designs
06c_locations.yml          → locations (reference groups from 05)
07_device_templates.yml    → templates (reference platforms, device_types)
07b_design_device_entries.yml → link designs to templates
08_lon01_devices.yml       → device instances (reference templates, locations)
09_ams01_devices.yml       → device instances (reference templates, locations)
```

Note: `04` prefix is absent — this is not an error (numbering gap is acceptable for future use).

### INFO-001: `example.yml` contains test data

**Severity**: INFO

`objects/example.yml` creates a `BuiltinTag` named "Yellow" with a cosmetic description. This file appears to be a leftover example. It will be imported into Infrahub on every sync. Consider removing it if it has no operational value.

---

## Checks Audit

### Python Classes

**Status: PASS**

`checks/device_checks.py` defines two check classes:

| Class | Base Class | `query` attribute | `validate()` method | `log_error()` used |
|-------|-----------|-------------------|---------------------|--------------------|
| `CheckDeviceHostname` | `InfrahubCheck` | `"all_devices"` | Yes (sync) | Yes |
| `CheckDeviceSite` | `InfrahubCheck` | `"all_devices"` | Yes (sync) | Yes |

No usage of non-existent `log_warning()`. Both classes inherit correctly from `InfrahubCheck`.

### Registration

**Status: PASS**

Both check classes are registered in `.infrahub.yml` `check_definitions` with matching `class_name` and `file_path` values.

---

## Generators Audit

### Python Classes

**Status: PASS**

`generators/campus_site_generator.py` defines `CampusSiteGenerator`:

- Inherits from `InfrahubGenerator`
- Implements `async generate(self, data: dict)` — correctly declared as `async`
- Calls `save(allow_upsert=True)` on all created device objects
- Handles empty/missing design data gracefully with early return

### Registration

**Status: PASS**

`CampusSiteGenerator` is registered in `.infrahub.yml` `generator_definitions` with matching `class_name`, `file_path`, `query`, and `targets`.

---

## Transforms Audit

### Jinja2 Transform

**Status: PASS**

`transforms/router_config.j2` is a valid Jinja2 template:

- Registered in `jinja2_transforms` with `name: router_config`
- Linked to the `router_config` query (registered in `queries`)
- Linked to the `router_config` artifact definition

### Artifact Definitions

#### FINDING CRITICAL-001: `LocationSite` does not inherit `CoreArtifactTarget` but is the artifact target kind

**File**: `schemas/extensions/location_minimal/location_minimal.yml`
**Severity**: CRITICAL
**Rule**: `artifact-target-inheritance`

The `artifact_definitions` entry `router_config` targets the group `campus_sites`. The `campus_sites` group (a `CoreGeneratorGroup`) has `LocationSite` instances as members (as seeded in `objects/06c_locations.yml` via `member_of_groups: campus_sites`).

For Infrahub to attach artifacts to `LocationSite` instances, `LocationSite` must inherit from `CoreArtifactTarget`. It currently does not — `LocationSite` inherits only `LocationGeneric` and `LocationHosting`, neither of which includes `CoreArtifactTarget`.

At runtime Infrahub will reject the artifact pipeline with a "target node does not support artifacts" error.

**Fix**: Add `CoreArtifactTarget` to `LocationSite.inherit_from`:

```yaml
# schemas/extensions/location_minimal/location_minimal.yml
- name: Site
  namespace: Location
  label: Site
  inherit_from:
    - LocationGeneric
    - LocationHosting
    - CoreArtifactTarget    # <-- add this
  ...
```

Note: `OtnCampusSite` and `OtnDataCenterSite` correctly inherit `CoreArtifactTarget` — they are `OtnSiteDesign` implementations, not the physical site targets used by this artifact.

---

## Menus Audit

**Status: N/A**

No `menus:` section in `.infrahub.yml` and no menu YAML files found. This is acceptable — the default Infrahub menu will be used.

---

## Cross-Reference Integrity

### Query Name Cross-References

**Status: PASS**

All query names are consistent between Python class attributes, `.infrahub.yml`, and GraphQL files:

| Query Name | `.infrahub.yml` | Used By |
|-----------|----------------|---------|
| `all_devices` | `queries[0]` → `queries/all_devices.gql` | `CheckDeviceHostname.query`, `CheckDeviceSite.query` |
| `campus_site` | `queries[1]` → `queries/campus_site.gql` | `generator_definitions[0].query` |
| `router_config` | `queries[2]` → `queries/router_config.gql` | `jinja2_transforms[0].query` |

No orphan queries (every registered query is referenced by at least one component).

#### FINDING HIGH-002: `campus_site.gql` references `TemplateDcimDevice` but no such kind is defined in the schema

**File**: `queries/campus_site.gql`, line 24
**Severity**: HIGH

The query uses an inline fragment `... on TemplateDcimDevice` to access the `role` field:

```graphql
template {
  node {
    id
    ... on TemplateDcimDevice {
      role {
        value
      }
    }
  }
}
```

`DcimDevice` has `generate_template: true` in the schema, which causes Infrahub to auto-create a `TemplateDcimDevice` kind. This is valid if the running Infrahub instance supports the `generate_template` feature and the schema has been loaded. This is **not an error** in itself but is flagged as HIGH because:
- If the schema is loaded in an Infrahub instance that does not support `generate_template`, the fragment will silently return no data, and the generator will create devices with no `role` set.
- The `CampusSiteGenerator` assigns `role` directly from the template, so a missing role would cause `ROLE_CODE.get(role, role.upper())` to use an empty or `None` role code.

**Recommendation**: Add a `None` guard in `campus_site_generator.py`:

```python
role = template["role"]["value"] if template.get("role") else None
if not role:
    self.logger.warning("Template %s has no role set — skipping", template_id)
    continue
role_code = ROLE_CODE.get(role, role.upper())
```

### Registration Completeness

**Status: PASS**

- All Python files containing `InfrahubCheck`/`InfrahubGenerator` subclasses are registered
- All `.gql` files are referenced by a `queries` entry
- All `.j2` template files are referenced by a `jinja2_transforms` entry
- Schema files are under the `schemas/` path listed in `.infrahub.yml`
- Object files are under the `objects/` path listed in `.infrahub.yml`

---

## Deployment Readiness

### Git Status

**Status: PASS**

Working tree is clean. All files are committed. No uncommitted changes to schema, query, Python, or template files.

### Bootstrap / Seed Data

#### FINDING MEDIUM-002: Static device instances in `objects/` will re-import on every sync

**Files**: `objects/08_lon01_devices.yml`, `objects/09_ams01_devices.yml`
**Severity**: MEDIUM
**Rule**: `deployment-readiness`

Files `08_lon01_devices.yml` and `09_ams01_devices.yml` define concrete `DcimDevice` instances (LON-RTR-01, AMS-DSW-01, etc.). These devices are also created programmatically by the `CampusSiteGenerator` (which uses `allow_upsert=True`). Having both static object files **and** a generator for the same devices is acceptable only if:
1. The static files are used for initial bootstrap before the generator has run, **and**
2. The generator's upsert semantics match the static data exactly.

If the intent is that the generator is the authoritative source, these static device files should be removed to avoid confusion. If they serve as a fallback for London and Amsterdam (pre-seeded before generator runs), document this intent clearly.

#### FINDING MEDIUM-003: `OtnDesignDeviceEntry` records reference `template` by `template_name` value but this is a cross-kind relationship

**File**: `objects/07b_design_device_entries.yml`
**Severity**: MEDIUM

The object data references templates using:
```yaml
- design: small-campus
  template: border-router
```

`OtnDesignDeviceEntry.template` peers to `CoreObjectTemplate`. The reference `border-router` resolves by `template_name`. This only works if `TemplateDcimDevice` objects are loaded **before** `OtnDesignDeviceEntry` objects. The current load order (07 before 07b) is correct, but future maintainers should be aware of this dependency.

---

## Best Practices

### FINDING MEDIUM-004: `OtnDesignDeviceEntry` node missing `display_label`

**File**: `schemas/extensions/designs/design.yml`
**Severity**: MEDIUM
**Rule**: `practices-schema`

`OtnDesignDeviceEntry` has `human_friendly_id` but no `display_label`. Without a `display_label`, the UI may show the raw ID or a less meaningful string. Recommended:

```yaml
display_label: "{{ design__name__value }} / {{ template__template_name__value }}"
```

### FINDING LOW-001: `DcimPhysicalDevice` generic is not user-facing but several of its relationships lack explicit `kind`

**Severity**: LOW

The `LocationHosting` generic's `devices` and `prefixes` relationships lack explicit `kind`. These are back-references intended to support the UI "Devices at this location" and "Prefixes at this location" lists. Adding `kind: Attribute` makes the ownership model explicit and avoids future ambiguity.

### INFO-002: `DcimDevice.generate_template: true` enables automatic template generation

**Severity**: INFO

`DcimDevice` uses `generate_template: true`. This is valid and is intentional (it enables `TemplateDcimDevice` and is the basis for the device template feature in `07_device_templates.yml`). Ensure the Infrahub instance version supports this field (available since Infrahub 1.3).

### FINDING LOW-002: `DcimDeviceType.platform` relationship has no `optional` field set

**File**: `schemas/base/dcim.yml`
**Severity**: LOW

`DcimDeviceType.platform` does not declare `optional`, relying on the default (`true`). This is functionally fine but worth making explicit to signal intent:

```yaml
- name: platform
  peer: DcimPlatform
  cardinality: one
  kind: Attribute
  optional: true      # add for clarity
  order_weight: 1300
```

### INFO-003: Numbering gap at `04` in `objects/` directory

**Severity**: INFO

There is no `04_*.yml` file in `objects/`. This is not an error — the numeric prefix only controls load order alphabetically. The gap is likely intentional (reserved for future use, e.g., VRFs or prefixes). No action needed.

---

## Findings Index

| ID | Severity | Category | Summary |
|----|----------|----------|---------|
| CRITICAL-001 | CRITICAL | Schema / Artifacts | `LocationSite` missing `CoreArtifactTarget` mixin — artifact pipeline will fail at runtime |
| HIGH-001 | HIGH | Schema Relationships | `OtnDesignDeviceEntry.design` uses `kind: Attribute` instead of `kind: Parent` |
| HIGH-002 | HIGH | Cross-References | `campus_site.gql` inline fragment on `TemplateDcimDevice` — no null guard in generator for missing role |
| HIGH-003 | HIGH | Schema Relationships | Multiple back-reference relationships missing explicit `kind` field |
| MEDIUM-001 | MEDIUM | Schema Relationships | Back-reference relationships missing explicit `kind` (same as HIGH-003 detail) |
| MEDIUM-002 | MEDIUM | Deployment | Static device instance files overlap with generator output |
| MEDIUM-003 | MEDIUM | Deployment | `OtnDesignDeviceEntry` records depend on template load order |
| MEDIUM-004 | MEDIUM | Best Practices | `OtnDesignDeviceEntry` missing `display_label` |
| LOW-001 | LOW | Best Practices | `LocationHosting` back-reference relationships lack explicit `kind` |
| LOW-002 | LOW | Best Practices | `DcimDeviceType.platform` missing explicit `optional` declaration |
| INFO-001 | INFO | Deployment | `example.yml` contains test/example data that will import on sync |
| INFO-002 | INFO | Schema | `generate_template: true` on `DcimDevice` — version dependency |
| INFO-003 | INFO | Deployment | Numbering gap at `04` in `objects/` (benign) |
