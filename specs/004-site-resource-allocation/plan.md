# Implementation Plan: Site Resource Allocation

**Branch**: `004-site-resource-allocation` | **Date**: 2026-05-28 | **Spec**: [spec.md](./spec.md)

## Summary

Move BGP ASN ownership from the design blueprint (`OtnSiteDesign`) to the physical site (`LocationSite`), introduce management IPAM prefixes and resource pools as seed data, extend the Generator to allocate ASNs and management IPs idempotently at deploy time, and update the router config query and Jinja2 transform to source all values from the site rather than the design. Also author the Challenge 3 proposed-change scenario file.

## Technical Context

**Language/Version**: Python 3.12, YAML 1.1  
**Primary Dependencies**: Infrahub SDK 1.20.1, infrahubctl 1.20.1  
**Storage**: Infrahub 1.9.6 (local instance at http://localhost:8000)  
**Testing**: `uv run infrahubctl schema check`, `uv run infrahubctl generator run`, `uv run infrahubctl render`  
**Target Platform**: Infrahub repository — schemas, objects, generators, transforms  
**Project Type**: Infrahub lab repository  
**Performance Goals**: Generator run ≤ 30 seconds for a small-campus site  
**Constraints**: Allocation must be idempotent — re-running Generator must not create new ASNs or IPs  
**Scale/Scope**: 3 sites (LON, AMS, MUC) × up to 8 devices each

## Constitution Check

Constitution file contains only the default template (uninitialized). No gates to enforce.

## Project Structure

### Documentation (this feature)

```text
specs/004-site-resource-allocation/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
schemas/
├── base/
│   └── dcim.yml                    # ADD: fqdn computed attr on DcimGenericDevice
└── extensions/designs/
    └── design.yml                  # MODIFY: remove bgp_asn from OtnSiteDesign,
                                    #   add parameters to count, extend LocationSite

objects/
├── 06_design_patterns.yml          # MODIFY: remove bgp_asn values
├── 06c_locations.yml               # MODIFY: add mgmt_pool links to lon-01, ams-01
├── 10_ipam_mgmt.yml                # NEW: 172.16.0.0/16 + per-site /24 prefixes
└── 11_resource_pools.yml           # NEW: CoreIPAddressPool ×3 + CoreNumberPool ×1

generators/
└── campus_site_generator.py        # MODIFY: add ASN + mgmt IP allocation

queries/
├── campus_site.gql                 # MODIFY: replace design.bgp_asn with site.mgmt_pool
└── router_config.gql               # MODIFY: add fqdn, primary_address, site.bgp_asn

transforms/
└── router_config.j2                # MODIFY: use fqdn, primary_address, site.bgp_asn

scenarios/
└── ch3_break_validation.yml        # NEW: bad device for proposed-change demo
```

**Structure Decision**: Flat repository following existing Infrahub lab conventions. All artifact files live at project root level in their respective directories.

---

## Phase 0: Research

### Decision: Number pool allocation pattern

**Decision**: Assign the `CoreNumberPool` node object directly to the Number attribute on the target node, then call `save(allow_upsert=True)`. Infrahub resolves the pool reference into an allocated integer on write. The same allocation is returned for subsequent saves of the same object.

**Rationale**: The SDK has no `allocate_next_number()` method. The `CoreNumberPool` uses Infrahub's node-level pool assignment pattern — confirmed in production code (`device.internal_id = pool`). Idempotency is built into the pool: allocating again for an object that already has an allocation returns the same value.

**Alternatives considered**: Raw `execute_graphql()` against `CoreNumberPoolCreate` mutation — rejected because it bypasses the SDK tracking context and requires manual mutation construction.

---

### Decision: IP address allocation pattern

**Decision**: Use `self.client.allocate_next_ip_address(resource_pool, identifier=hostname)` with the device hostname as the `identifier`. This is the explicit SDK method that returns an `IpamIPAddress` node. The `identifier` parameter makes allocation idempotent — same hostname always returns the same IP.

**Rationale**: The SDK provides `allocate_next_ip_address()` with an `identifier` parameter documented as "value to perform idempotent allocation." This is the correct path for `CoreIPAddressPool` (as opposed to `CoreIPPrefixPool` which uses `allocate_next_ip_prefix()`).

**Alternatives considered**: Creating `IpamIPAddress` nodes manually from a prefix — rejected because it requires tracking used addresses manually and doesn't use Infrahub's pool machinery.

---

### Decision: Write bgp_asn to LocationSite from Generator

**Decision**: The Generator fetches the site object by its ID (already in `data["LocationSite"]["edges"][0]["node"]["id"]`), retrieves it as an SDK node via `self.client.get(kind="LocationSite", id=site_id)`, assigns the pool node to `site.bgp_asn`, then calls `await site.save(allow_upsert=True)`.

**Rationale**: The Generator already has `site_id` from the GraphQL response. `client.get()` by ID is the most direct fetch. Setting `site.bgp_asn = asn_pool` follows the pool assignment pattern above.

**Alternatives considered**: Fetching site via `shortname__value` — equivalent but adds an extra filter; ID is already available and unambiguous.

---

### Decision: Remove bgp_asn from OtnSiteDesign

**Decision**: Use `state: absent` on the `bgp_asn` attribute in the `OtnSiteDesign` generic. Apply schema migration before loading updated object files (which remove `bgp_asn` values). Order matters: schema first, then objects.

**Rationale**: `state: absent` is the Infrahub schema migration pattern for removing attributes. The schema must be updated before object files that no longer include the field, otherwise the loader will try to clear an attribute that still has `optional: false` semantics on the old schema.

**Alternatives considered**: Deleting the attribute definition entirely — not safe with loaded data; `state: absent` is the correct migration path.

---

### Decision: IPAM prefix hierarchy and pool configuration

**Decision**:
- `172.16.0.0/16` as top-level supernet (`is_pool: false`, role management)
- Three `/24` children as site prefixes (`172.16.1.0/24` LON, `172.16.2.0/24` AMS, `172.16.3.0/24` MUC)
- Each `CoreIPAddressPool` references its site `/24` as `resources`, with `default_prefix_length: 32`

**Rationale**: Matches the LAB_DESIGN specification. `/32` host addresses are the correct allocation unit for management IPs on loopback/management interfaces.

**Alternatives considered**: Using `CoreIPPrefixPool` and allocating `/32` prefixes — valid but more complex; `CoreIPAddressPool` is simpler for host address allocation.

---

### Decision: Existing lon-01 and ams-01 device handling

**Decision**: Seed data files (`objects/08_lon01_devices.yml`, `objects/09_ams01_devices.yml`) are not changed in this feature. Existing devices for LON and AMS do not get management IPs assigned — that is the Generator's job and is only invoked for MUC in the lab. The `mgmt_pool` relationship on `lon-01` and `ams-01` is set in `objects/06c_locations.yml` so it's available if students later run the Generator against those sites.

**Alternatives considered**: Pre-running the Generator against all three sites in seed data — rejected; the Generator run is a student activity (Challenge 4), not seed data setup.

---

## Phase 1: Design

### data-model.md

#### DcimGenericDevice (modified)

**File**: `schemas/base/dcim.yml`

New attribute added to the `DcimGenericDevice` generic:

```yaml
- name: fqdn
  kind: Text
  computed_attribute:
    kind: Jinja2
    jinja2_template: "{{ name__value }}.{{ location__shortname__value }}.otternet.net"
  read_only: true
  optional: true
  order_weight: 1050
```

Key rules:
- `read_only: true` is mandatory with `computed_attribute` (Infrahub rejects computed attrs without it)
- `optional: true` because `location` is itself optional on the generic; the derivation is best-effort
- Template traverses `location → shortname` via `location__shortname__value`; this is a one-hop relationship traversal — valid per schema rules

---

#### OtnDesignDeviceEntry.count (modified)

**File**: `schemas/extensions/designs/design.yml`

Change `count` attribute on the `OtnDesignDeviceEntry` node:

```yaml
- name: count
  kind: Number
  default_value: 1
  order_weight: 1000
  parameters:
    min_value: 1
    max_value: 8
```

Key rules:
- Constraints go in `parameters` block, not top-level (`min_value`/`max_value` are deprecated at top level)
- `default_value: 1` is preserved

---

#### OtnSiteDesign (modified — bgp_asn removed)

**File**: `schemas/extensions/designs/design.yml`

Migration step — mark `bgp_asn` absent on the generic:

```yaml
generics:
  - name: SiteDesign
    namespace: Otn
    # ... existing fields unchanged ...
    attributes:
      - name: bgp_asn
        kind: Number
        state: absent          # Removes this attribute on schema load
```

After migration is applied and verified, the `state: absent` entry can be removed from the file in a follow-up cleanup (or left as a permanent record). For the lab, the `state: absent` entry stays.

---

#### LocationSite (extended)

**File**: `schemas/extensions/designs/design.yml` — `extensions.nodes` block

```yaml
extensions:
  nodes:
    - kind: LocationSite
      attributes:
        - name: bgp_asn
          kind: Number
          optional: true
          order_weight: 2050
      relationships:
        - name: design
          # ... existing design relationship unchanged ...
        - name: mgmt_pool
          label: Management IP Pool
          peer: CoreIPAddressPool
          cardinality: one
          kind: Attribute
          optional: true
          identifier: location_site__mgmt_pool
          order_weight: 2100
```

Key rules:
- `bgp_asn` is `optional: true` — adding a mandatory attribute to an existing node with data would break validation
- `mgmt_pool` uses `kind: Attribute` (belongs-to style), `cardinality: one`, `optional: true`
- `identifier` uses snake_case with `__` separator convention

---

#### IPAM Object Model (new seed data)

**File**: `objects/10_ipam_mgmt.yml`

```yaml
# IpamPrefix objects:
# 172.16.0.0/16 — supernet, role: management
# 172.16.1.0/24 — LON management subnet (child of supernet)
# 172.16.2.0/24 — AMS management subnet (child of supernet)
# 172.16.3.0/24 — MUC management subnet (child of supernet)
```

**File**: `objects/11_resource_pools.yml`

```yaml
# CoreIPAddressPool objects:
#   lon-mgmt-pool → resources: [172.16.1.0/24], default_prefix_length: 32
#   ams-mgmt-pool → resources: [172.16.2.0/24], default_prefix_length: 32
#   muc-mgmt-pool → resources: [172.16.3.0/24], default_prefix_length: 32
#
# CoreNumberPool object:
#   otn-asn-pool, start_range: 65000, end_range: 65534
```

---

#### Generator Data Flow (modified)

**File**: `generators/campus_site_generator.py`

New allocation steps inserted at the top of `generate()`, before device creation:

```python
# 1. Fetch site as SDK node to write bgp_asn back
site_node = await self.client.get(kind="LocationSite", id=site_id)

# 2. Get ASN pool and assign (idempotent — same node always gets same allocation)
asn_pool = await self.client.get(kind="CoreNumberPool", name__value="otn-asn-pool")
site_node.bgp_asn = asn_pool
await site_node.save(allow_upsert=True)

# 3. Get management IP pool from site
mgmt_pool_id = site["mgmt_pool"]["node"]["id"]
mgmt_pool = await self.client.get(kind="CoreIPAddressPool", id=mgmt_pool_id)
```

Then, inside the device creation loop, after `device.save(allow_upsert=True)`:

```python
# 4. Allocate management IP (idempotent — hostname is the identifier)
mgmt_ip = await self.client.allocate_next_ip_address(
    resource_pool=mgmt_pool,
    identifier=hostname,
    data={"description": f"Management IP for {hostname}"},
)

# 5. Set primary_address on device
device.primary_address = mgmt_ip
await device.save(allow_upsert=True)
```

**Query update** — `queries/campus_site.gql`:
- Remove `bgp_asn { value }` from the `... on OtnCampusSite` fragment
- Add `mgmt_pool { node { id } }` at the site level (outside the design fragment)

---

#### Transform Data Flow (modified)

**File**: `queries/router_config.gql`

Add to the device node:
```graphql
fqdn { value }
primary_address {
  node {
    address { value }
  }
}
```

Change `location` traversal — replace `design.node.bgp_asn` with site-level `bgp_asn`:
```graphql
location {
  node {
    ... on LocationSite {
      shortname { value }
      bgp_asn { value }
    }
  }
}
```

**File**: `transforms/router_config.j2`

Key changes:
- Replace `hostname {{ device["name"]["value"] }}` with same (name is fine)
- Add `fqdn {{ device["fqdn"]["value"] }}` stanza  
- Read management IP from `device["primary_address"]["node"]["address"]["value"]` (split on `/` for host-only)
- Read BGP ASN from `location["bgp_asn"]["value"]` instead of `location["design"]["node"]["bgp_asn"]["value"]`

---

#### Proposed Change Scenario

**File**: `scenarios/ch3_break_validation.yml`

Creates:
- A `LocationMetro` node (wrong type — CheckDeviceSite expects LocationSite)
- A `DcimDevice` named `my-router-01` (wrong format — CheckDeviceHostname regex `^[A-Z]{3}-[A-Z]{2,5}-\d{2}$` rejects it) linked to the metro location

This file is loaded on a branch; when a Proposed Change to main is opened, both Python checks fire.

---

### quickstart.md

**Test sequence for this feature:**

```bash
# 1. Load updated schema (schema migration runs automatically)
uv run infrahubctl schema load schemas/ --wait 30

# 2. Verify schema — no errors expected
uv run infrahubctl schema check schemas/

# 3. Load seed objects (IPAM, pools, updated designs, updated locations)
uv run invoke load-objects

# 4. Verify muc-mgmt-pool exists
uv run infrahubctl object get --kind CoreIPAddressPool --filter name__value=muc-mgmt-pool

# 5. Set up muc-01 with small-campus design and muc-mgmt-pool (if not in seed data)
# (done via UI or invoke load-objects — muc-01 must have design and mgmt_pool set)

# 6. Run Generator against muc-01
uv run infrahubctl generator run campus_site_generator --identifier muc-01

# 7. Verify bgp_asn written to muc-01
uv run infrahubctl object get --kind LocationSite --filter shortname__value=muc-01

# 8. Verify device primary_address allocated
uv run infrahubctl object get --kind DcimDevice --filter name__value=MUC-RTR-01

# 9. Render router config artifact
uv run infrahubctl render router_config --variables '{"device_name": "MUC-RTR-01"}'

# 10. Test proposed change scenario (on a branch)
git checkout -b ch3-break-validation
uv run infrahubctl object load scenarios/ch3_break_validation.yml
# Then open Proposed Change in UI targeting main
```
