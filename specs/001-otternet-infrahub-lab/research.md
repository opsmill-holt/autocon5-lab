# Research: OtterNet Infrahub Lab

**Phase 0 Findings** — all decisions resolved, no clarifications outstanding.

---

## Schema Design

**Decision**: Use namespace `Otn` (matches `^[A-Z][a-z0-9]+$`), giving kinds `OtnSiteDesign`, `OtnCampusSite`, `OtnDataCenterSite`.

**Rationale**: Keeps OtterNet-specific nodes cleanly separated from schema library nodes (`Dcim`, `Location`, `Ipam`, `Organization`). Short namespace reduces verbosity in GraphQL queries.

**`OtnSiteDesign` generic attributes**:
- `name` — Text, unique (uniqueness_constraints: `[name__value]`)
- `description` — Text, optional
- `router_count` — Number, default 1
- `bgp_asn` — Number, optional (needed by the Jinja2 Transform to render BGP stanzas without a separate lookup)

**Rationale for `bgp_asn` on the generic**: The Transform renders per-device configs. The BGP ASN is a site-design-level property (each design tier has its own ASN in the lab). Storing it on the generic avoids a separate relationship to an ASN registry, which is not in scope.

**`CoreArtifactTarget` placement**: Applied to `OtnCampusSite` and `OtnDataCenterSite` (concrete nodes), NOT the `OtnSiteDesign` generic. Per rules: artifacts attach to instances, not generics. This lets the Generator and Transform definitions target these nodes via `CoreGeneratorGroup`/`CoreArtifactTarget`.

**Relationship `OtnSiteDesign` → `LocationSite`**: `kind: Attribute`, cardinality one, optional. Stores which physical site this design is applied to. Identifier: `site_design__site`.

---

## Schema Library Integration

**Decision**: Load schema library in order:
1. `schemas/base/` (organization, location, dcim, ipam)
2. `schemas/location_minimal/` (Country → Metro → Site hierarchy)
3. `schemas/otn.yml` (OTN-specific generics and nodes)

**Base node kinds used**:
- `LocationSite` — physical site (has `name`, `shortname`, hierarchical under Metro)
- `DcimGenericDevice` — base device generic (has `name`, `interfaces`, `primary_address`)
- `DcimPhysicalDevice` — physical device inheritor (has `serial`, `position`)
- `DcimInterface` — interface node (linked to device via `device__interface` identifier)
- `DcimPlatform` — OS platform
- `DcimDeviceType` — hardware model

**Device node used for Generator output**: The schema library's `DcimPhysicalDevice` is the concrete device node. Generator creates instances of `DcimPhysicalDevice`.

---

## Device Naming Convention

**Decision**: `{SITE_CODE}-{ROLE}-{INDEX:02d}`

| Design Tier    | Devices created                                                      |
|----------------|----------------------------------------------------------------------|
| Small campus   | RTR-01, ASW-01                                                       |
| Medium campus  | RTR-01, DSW-01, ASW-01, ASW-02                                       |
| Large campus   | RTR-01, RTR-02, DSW-01, DSW-02, ASW-01, ASW-02, ASW-03, ASW-04     |
| DC (stretch)   | SPINE-01, SPINE-02, LEAF-01..04, BLEAF-01, BLEAF-02                 |

Site code extracted from the site's `shortname` (first 3 chars uppercased): `lon-01` → `LON`, `muc-01` → `MUC`.

**Hostname regex for Check**: `^[A-Z]{3}-[A-Z]{2,5}-\d{2}$`
- Covers RTR (3), ASW (3), DSW (3), SPINE (5), LEAF (4), BLEAF (5)

---

## Seed Data Structure

**Decision**: One YAML file per logical group, loaded together via `infrahubctl object load objects/`.

| File | Contents |
|------|----------|
| `objects/locations.yml` | LocationCountry, LocationMetro, LocationSite for UK/London and NL/Amsterdam |
| `objects/organizations.yml` | Manufacturer (Generic), Platform, DeviceType entries |
| `objects/design_instances.yml` | 4 OtnCampusSite/OtnDataCenterSite instances (small, medium, large, DC) |
| `objects/lon01_devices.yml` | 8 devices + interfaces for lon-01 (large campus) |
| `objects/ams01_devices.yml` | 4 devices + interfaces for ams-01 (medium campus) |

**Rationale**: Separating by logical group allows individual file reload during dev; `infrahubctl object load objects/` loads the entire directory in one pass.

---

## Generator Architecture

**Decision**: Single Python class `CampusSiteGenerator` targeting `OtnCampusSite` instances via a `CoreGeneratorGroup` named `campus_sites`.

**GraphQL query** (`queries/campus_site.gql`): Fetches `OtnCampusSite` by `name__value`, returns `router_count`, `access_switch_count`, `distribution_switch_count`, and the linked `LocationSite.shortname` (for site code derivation).

**Idempotency**: Uses `allow_upsert=True` on every `save()`. The SDK tracking system (`delete_unused_nodes=True` in `run()`) automatically removes stale objects on re-run.

**Interface creation**: Each device gets a standard set of interfaces based on role:
- RTR: `Loopback0`, `GigabitEthernet0/0`, `GigabitEthernet0/1`
- DSW: `Loopback0`, `GigabitEthernet1/0/1`..`/4`
- ASW: `Loopback0`, `GigabitEthernet0/1`..`/24`

---

## Python Check Architecture

**Decision**: Two checks in one file `checks/device_checks.py`, each as a separate class.

1. `CheckDeviceHostname` — validates every device `name` matches `^[A-Z]{3}-[A-Z]{2,5}-\d{2}$`
2. `CheckDeviceSite` — validates every device has a non-null site relationship

**Query** (`queries/all_devices.gql`): Fetches all `DcimPhysicalDevice` instances with `name` and `site` relationship.

**Registration**: Two `check_definitions` entries in `.infrahub.yml`, both using the same query (no `query:` field in check_definition — binding is via class attribute only).

---

## Transform Architecture

**Decision**: Jinja2 Transform rendering router configs.

**Query** (`queries/router_config.gql`): Fetches `DcimPhysicalDevice` by name, returns:
- `name.value`
- `interfaces.edges[].node.{name.value, ip_addresses}`
- `site.node.{shortname.value, design.node.{bgp_asn.value}}`

**Template** (`transforms/router_config.j2`): Renders:
- `hostname <name>`
- Interface stanzas with IP if assigned
- `router bgp <bgp_asn>` stanza
- `! Managed by OtterNet SoT` banner

**Registration**: One `artifact_definition` in `.infrahub.yml` targeting `campus_sites` group, content type `text/plain`.

---

## `.infrahub.yml` Final Structure

```yaml
schemas:
  - schemas

queries:
  - name: campus_site
    file_path: queries/campus_site.gql
  - name: all_devices
    file_path: queries/all_devices.gql
  - name: router_config
    file_path: queries/router_config.gql

generator_definitions:
  - name: campus_site_generator
    file_path: generators/campus_site_generator.py
    query: campus_site
    targets: campus_sites
    class_name: CampusSiteGenerator
    parameters:
      name: name__value

check_definitions:
  - name: check_device_hostname
    file_path: checks/device_checks.py
    class_name: CheckDeviceHostname
  - name: check_device_site
    file_path: checks/device_checks.py
    class_name: CheckDeviceSite

jinja2_transforms:
  - name: router_config
    query: router_config
    template_path: transforms/router_config.j2

artifact_definitions:
  - name: router_config
    artifact_name: router-config
    content_type: text/plain
    targets: campus_sites
    transformation: router_config
    parameters:
      device_name: name__value
```

---

## File / Directory Layout

```text
schemas/
  base/            # Schema library (auto-copied by invoke schema-library-get)
  location_minimal/ # Schema library extension
  otn.yml          # OTN-specific schema

objects/
  locations.yml
  organizations.yml
  design_instances.yml
  lon01_devices.yml
  ams01_devices.yml

generators/
  __init__.py
  campus_site_generator.py

checks/
  __init__.py
  device_checks.py

queries/
  campus_site.gql
  all_devices.gql
  router_config.gql

transforms/
  router_config.j2

tests/
  integration/
    test_schema.py     # (pre-existing, extended)
```
