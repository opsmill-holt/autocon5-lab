# Implementation Plan: OtterNet Infrahub Lab — Full Implementation

**Branch**: `001-otternet-infrahub-lab` | **Date**: 2026-05-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-otternet-infrahub-lab/spec.md`

## Summary

Build the complete OtterNet Infrahub lab for AutoCon 5 Munich. Starting from a blank Infrahub with schema library loaded, deliver: the `Otn` namespace schema (generics + nodes), seed data for two existing sites, Python enforcement checks, a design-driven Generator that deploys a new campus site in under 5 minutes, and a Jinja2 Transform that renders a deployable router config — all wired together in `.infrahub.yml`.

## Technical Context

**Language/Version**: Python 3.12, Infrahub 1.9.6, infrahub-sdk 1.20.1
**Primary Dependencies**: `infrahub-sdk`, `infrahubctl` CLI
**Storage**: Infrahub (PostgreSQL-backed, accessed via SDK)
**Testing**: pytest (pre-existing integration test harness in `tests/`)
**Target Platform**: Infrahub 1.9.6 running in Docker
**Project Type**: Infrahub repository (schema + objects + checks + generators + transforms)
**Performance Goals**: New site provisioned in < 5 minutes via Generator
**Constraints**: Must use schema library base nodes; OTN schema must not modify library nodes (extensions only if needed)
**Scale/Scope**: 5 artifact files, ~12 object YAML files, 3 GraphQL queries, 1 Generator class, 2 Check classes, 1 Jinja2 template

## Constitution Check

*No project constitution defined — template placeholder only. No gates to enforce.*

## Project Structure

### Documentation (this feature)

```text
specs/001-otternet-infrahub-lab/
├── plan.md              ← this file
├── spec.md              ← feature specification
├── research.md          ← Phase 0 decisions
├── data-model.md        ← entity definitions
├── quickstart.md        ← setup guide
└── tasks.md             ← Phase 2 output (created by /speckit-tasks)
```

### Source Code Layout

```text
schemas/
  base/                  # Schema library (auto-copied by invoke schema-library-get)
  location_minimal/      # Schema library location extension
  otn.yml                # OTN-specific schema (to be created)

objects/
  locations.yml          # Country → Metro → Site hierarchy for LON + AMS
  organizations.yml      # Manufacturer, DeviceType, Platform
  design_instances.yml   # 4 design instances (small/medium/large campus, DC)
  lon01_devices.yml      # 8 devices for lon-01 (large campus)
  ams01_devices.yml      # 4 devices for ams-01 (medium campus)

generators/
  __init__.py
  campus_site_generator.py   # CampusSiteGenerator class

checks/
  __init__.py
  device_checks.py           # CheckDeviceHostname, CheckDeviceSite

queries/
  campus_site.gql            # Generator query — OtnCampusSite by name
  all_devices.gql            # Check query — all DcimPhysicalDevice
  router_config.gql          # Transform query — device + interfaces + design

transforms/
  router_config.j2           # Jinja2 router config template

.infrahub.yml                # Updated to register all queries, generator, checks, transform, artifact
```

---

## Phase 1: Schema (`schemas/otn.yml`)

**Goal**: Define `OtnSiteDesign` generic and two concrete nodes.

### Schema YAML structure

```yaml
---
# yaml-language-server: $schema=https://schema.infrahub.app/infrahub/schema/latest.json
version: "1.0"

generics:
  - name: SiteDesign
    namespace: Otn
    description: Abstract site design blueprint shared by campus and DC tiers.
    label: Site Design
    icon: mdi:file-tree
    include_in_menu: true
    human_friendly_id:
      - name__value
    display_label: name__value
    order_by:
      - name__value
    attributes:
      - name: name
        kind: Text
        order_weight: 1000
      - name: description
        kind: Text
        optional: true
        order_weight: 1100
      - name: router_count
        kind: Number
        default_value: 1
        order_weight: 1200
      - name: bgp_asn
        kind: Number
        optional: true
        order_weight: 1300
    relationships:
      - name: site
        peer: LocationSite
        cardinality: one
        kind: Attribute
        optional: true
        identifier: site_design__site
        order_weight: 1400

nodes:
  - name: CampusSite
    namespace: Otn
    label: Campus Site Design
    icon: ri:building-line
    inherit_from:
      - OtnSiteDesign
      - CoreArtifactTarget
    menu_placement: OtnSiteDesign
    uniqueness_constraints:
      - [name__value]
    human_friendly_id:
      - name__value
    display_label: name__value
    attributes:
      - name: access_switch_count
        kind: Number
        default_value: 1
        order_weight: 1500
      - name: distribution_switch_count
        kind: Number
        default_value: 0
        order_weight: 1600

  - name: DataCenterSite
    namespace: Otn
    label: Data Center Site Design
    icon: mdi:server-network
    inherit_from:
      - OtnSiteDesign
      - CoreArtifactTarget
    menu_placement: OtnSiteDesign
    uniqueness_constraints:
      - [name__value]
    human_friendly_id:
      - name__value
    display_label: name__value
    attributes:
      - name: spine_count
        kind: Number
        default_value: 2
        order_weight: 1500
      - name: leaf_count
        kind: Number
        default_value: 4
        order_weight: 1600
      - name: border_leaf_count
        kind: Number
        default_value: 2
        order_weight: 1700
```

**Validation command**: `uv run infrahubctl schema check schemas/`

---

## Phase 2: Objects

**Goal**: Seed lon-01 (large campus) and ams-01 (medium campus) + 4 design instances.

### `objects/locations.yml`

Location hierarchy: Europe → Country → Metro → Site.

```yaml
---
apiVersion: infrahub.app/v1
kind: Object
spec:
  kind: LocationCountry
  data:
    - name: United Kingdom
      shortname: uk
      timezone: Europe/London
    - name: Netherlands
      shortname: nl
      timezone: Europe/Amsterdam
```

Then LocationMetro and LocationSite referencing parents via `shortname`.

### `objects/design_instances.yml`

Four design instance objects (small-campus, medium-campus, large-campus, dc-standard) with `bgp_asn` populated (65001–65003 for campus tiers).

### `objects/lon01_devices.yml` / `ams01_devices.yml`

One `DcimPhysicalDevice` object per device, each with:
- `name`: e.g., `LON-RTR-01`
- `device_type`: references DcimDeviceType by model name
- `platform`: references DcimPlatform by name
- `site`: references LocationSite shortname `lon-01`

---

## Phase 3: Checks (`checks/device_checks.py`)

**Goal**: Two Python checks registered in `.infrahub.yml`.

### Query (`queries/all_devices.gql`)

```graphql
query AllDevices {
  DcimPhysicalDevice(limit: -1) {
    edges {
      node {
        id
        name { value }
        site {
          node {
            id
            shortname { value }
          }
        }
      }
    }
  }
}
```

### Python check class

```python
import re
from infrahub_sdk.checks import InfrahubCheck

HOSTNAME_RE = re.compile(r"^[A-Z]{3}-[A-Z]{2,5}-\d{2}$")

class CheckDeviceHostname(InfrahubCheck):
    query = "all_devices"

    def validate(self, data: dict) -> None:
        for edge in data["DcimPhysicalDevice"]["edges"]:
            name = edge["node"]["name"]["value"]
            if not HOSTNAME_RE.match(name):
                self.log_error(
                    f"Hostname '{name}' does not match naming convention",
                    object_id=edge["node"]["id"],
                )

class CheckDeviceSite(InfrahubCheck):
    query = "all_devices"

    def validate(self, data: dict) -> None:
        for edge in data["DcimPhysicalDevice"]["edges"]:
            node = edge["node"]
            if node["site"]["node"] is None:
                self.log_error(
                    f"Device '{node['name']['value']}' has no site assigned",
                    object_id=node["id"],
                )
```

---

## Phase 4: Generator (`generators/campus_site_generator.py`)

**Goal**: Design-driven campus site provisioning.

### Query (`queries/campus_site.gql`)

```graphql
query CampusSite($name: String!) {
  OtnCampusSite(name__value: $name) {
    edges {
      node {
        id
        name { value }
        router_count { value }
        access_switch_count { value }
        distribution_switch_count { value }
        site {
          node {
            id
            shortname { value }
          }
        }
      }
    }
  }
}
```

### Generator class (outline)

```python
from infrahub_sdk.generator import InfrahubGenerator

ROLE_INTERFACES = {
    "RTR": ["Loopback0", "GigabitEthernet0/0", "GigabitEthernet0/1"],
    "DSW": ["Loopback0", "GigabitEthernet1/0/1", "GigabitEthernet1/0/2"],
    "ASW": ["Loopback0", "GigabitEthernet0/1", "GigabitEthernet0/2"],
}

class CampusSiteGenerator(InfrahubGenerator):
    async def generate(self, data: dict) -> None:
        campus = data["OtnCampusSite"]["edges"][0]["node"]
        site_node = campus["site"]["node"]
        site_code = campus["name"]["value"][:3].upper()
        site_id = site_node["id"]

        roles = (
            ("RTR", campus["router_count"]["value"]),
            ("DSW", campus["distribution_switch_count"]["value"]),
            ("ASW", campus["access_switch_count"]["value"]),
        )

        for role, count in roles:
            for i in range(1, count + 1):
                hostname = f"{site_code}-{role}-{i:02d}"
                device = await self.client.create(
                    kind="DcimPhysicalDevice",
                    data={"name": hostname, "site": site_id},
                )
                await device.save(allow_upsert=True)

                for iface_name in ROLE_INTERFACES.get(role, []):
                    iface = await self.client.create(
                        kind="DcimInterface",
                        data={"name": iface_name, "device": device.id},
                    )
                    await iface.save(allow_upsert=True)
```

---

## Phase 5: Transform (`transforms/router_config.j2`)

**Goal**: Jinja2 template rendering router config from SoT.

### Query (`queries/router_config.gql`)

```graphql
query RouterConfig($device_name: String!) {
  DcimPhysicalDevice(name__value: $device_name) {
    edges {
      node {
        name { value }
        interfaces(limit: -1) {
          edges {
            node {
              name { value }
              primary_address {
                node {
                  address { value }
                }
              }
            }
          }
        }
        site {
          node {
            shortname { value }
            design_campus {
              node {
                bgp_asn { value }
              }
            }
          }
        }
      }
    }
  }
}
```

### Template (outline)

```jinja2
! Managed by OtterNet SoT
! Generated: {{ now() }}
!
hostname {{ device.name.value }}
!
{% for iface in device.interfaces.edges %}
interface {{ iface.node.name.value }}
{% if iface.node.primary_address.node %}
 ip address {{ iface.node.primary_address.node.address.value | ipaddr('address') }} {{ iface.node.primary_address.node.address.value | ipaddr('netmask') }}
{% else %}
 no ip address
{% endif %}
 no shutdown
!
{% endfor %}
{% if device.site.node.design_campus.node %}
router bgp {{ device.site.node.design_campus.node.bgp_asn.value }}
 bgp router-id {{ device.name.value }}
!
{% endif %}
```

---

## Phase 6: Wire `.infrahub.yml`

Register all queries, generator_definitions, check_definitions, jinja2_transforms, and artifact_definitions.

---

## Complexity Tracking

*No constitution violations — no entries required.*
