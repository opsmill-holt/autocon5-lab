# Data Model: Site Resource Allocation

**Feature**: 004-site-resource-allocation  
**Date**: 2026-05-28

## Entity Changes

### DcimGenericDevice — new computed attribute

| Attribute | Kind | Constraints | Notes |
|-----------|------|-------------|-------|
| `fqdn` | `Text` | `read_only: true`, `optional: true`, `computed_attribute` | Jinja2: `{{ name__value }}.{{ location__shortname__value }}.otternet.net` |

**File**: `schemas/base/dcim.yml` (add to `DcimGenericDevice` generic attributes)

---

### OtnDesignDeviceEntry.count — parameter constraints added

| Attribute | Kind | Constraints | Notes |
|-----------|------|-------------|-------|
| `count` | `Number` | `default_value: 1`, `min_value: 1` (via `parameters`), `max_value: 8` (via `parameters`) | Schema enforcement replaces Python validation |

**File**: `schemas/extensions/designs/design.yml` (modify existing attribute)

---

### OtnSiteDesign — bgp_asn removed

| Attribute | Kind | State | Notes |
|-----------|------|-------|-------|
| `bgp_asn` | `Number` | `state: absent` | Removed — allocation is Generator's responsibility |

**File**: `schemas/extensions/designs/design.yml` (add `state: absent`)

---

### LocationSite — new attribute and relationship

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `bgp_asn` (attribute) | `Number` | `optional: true` | Written by Generator from otn-asn-pool |
| `mgmt_pool` (relationship) | → `CoreIPAddressPool` | `cardinality: one`, `optional: true`, `kind: Attribute` | Set by seed data; read by Generator |

**File**: `schemas/extensions/designs/design.yml` (in `extensions.nodes` block for `LocationSite`)

**Relationship identifier**: `location_site__mgmt_pool`

---

## New Object Instances

### IpamPrefix hierarchy (objects/10_ipam_mgmt.yml)

| Prefix | Role | Parent | Notes |
|--------|------|--------|-------|
| `172.16.0.0/16` | management | — | OtterNet management supernet |
| `172.16.1.0/24` | management | `172.16.0.0/16` | LON site subnet |
| `172.16.2.0/24` | management | `172.16.0.0/16` | AMS site subnet |
| `172.16.3.0/24` | management | `172.16.0.0/16` | MUC site subnet |

---

### Resource Pools (objects/11_resource_pools.yml)

| Name | Kind | Parameters | Notes |
|------|------|------------|-------|
| `lon-mgmt-pool` | `CoreIPAddressPool` | resources: `172.16.1.0/24`, default_prefix_length: 32 | LON management IPs |
| `ams-mgmt-pool` | `CoreIPAddressPool` | resources: `172.16.2.0/24`, default_prefix_length: 32 | AMS management IPs |
| `muc-mgmt-pool` | `CoreIPAddressPool` | resources: `172.16.3.0/24`, default_prefix_length: 32 | MUC management IPs |
| `otn-asn-pool` | `CoreNumberPool` | start_range: 65000, end_range: 65534 | Private ASN range |

---

### LocationSite updates (objects/06c_locations.yml)

| Site | Field | Value |
|------|-------|-------|
| `lon-01` | `mgmt_pool` | `lon-mgmt-pool` |
| `ams-01` | `mgmt_pool` | `ams-mgmt-pool` |
| `muc-01` | `mgmt_pool` | `muc-mgmt-pool` |

*Note: `muc-01` is added to `06c_locations.yml` if not already present.*

---

## Generator Logic (campus_site_generator.py)

**Allocation order** (must be respected — idempotency depends on order):

1. Fetch `site_node` by `site_id` via `client.get(kind="LocationSite", id=site_id)`
2. Fetch `asn_pool` via `client.get(kind="CoreNumberPool", name__value="otn-asn-pool")`
3. Set `site_node.bgp_asn = asn_pool` and save — writes allocated ASN to site
4. Fetch `mgmt_pool` via `client.get(kind="CoreIPAddressPool", id=site["mgmt_pool"]["node"]["id"])`
5. For each device:
   - Create/upsert device (existing logic)
   - Call `allocate_next_ip_address(resource_pool=mgmt_pool, identifier=hostname)`
   - Set `device.primary_address = mgmt_ip` and save again

**Query changes** (`queries/campus_site.gql`):
- Remove `bgp_asn { value }` from `... on OtnCampusSite` fragment
- Add at site level (outside design fragment): `mgmt_pool { node { id } }`

---

## Transform Data Flow (router_config)

**Query additions** (`queries/router_config.gql`):

On the device node:
```graphql
fqdn { value }
primary_address {
  node {
    address { value }
  }
}
```

On `location.node` (inside `... on LocationSite`):
```graphql
bgp_asn { value }
```
*(Remove traversal through `design.node.bgp_asn`)*

**Template changes** (`transforms/router_config.j2`):

| Line | Old | New |
|------|-----|-----|
| FQDN stanza | Not present | `fqdn {{ device["fqdn"]["value"] }}` |
| Management IP | Not present | from `device["primary_address"]["node"]["address"]["value"]` |
| BGP ASN source | `design["bgp_asn"]["value"]` | `location["bgp_asn"]["value"]` |

---

## Proposed Change Scenario (scenarios/ch3_break_validation.yml)

Creates two objects on a branch:

| Object | Kind | Bad Field | Check triggered |
|--------|------|-----------|-----------------|
| `bad-metro` | `LocationMetro` | — | — |
| `my-router-01` | `DcimDevice` | name violates regex; location is metro not site | `CheckDeviceHostname`, `CheckDeviceSite` |

The scenario is loaded via `infrahubctl object load` on a feature branch, then a Proposed Change targeting `main` triggers both checks.
