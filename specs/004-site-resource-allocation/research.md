# Research: Site Resource Allocation

**Feature**: 004-site-resource-allocation  
**Date**: 2026-05-28

## 1. CoreNumberPool Allocation Pattern

**Decision**: Assign the `CoreNumberPool` node object directly to a `Number` attribute on the target node. Infrahub resolves the pool reference into an allocated integer when `save()` is called.

**Rationale**: The Infrahub SDK has no `allocate_next_number()` method. `CoreNumberPool` uses a node-level assignment pattern — confirmed in production code: `device.internal_id = pool` followed by `await device.save(allow_upsert=True)`. Idempotency is intrinsic: the same node object always receives the same allocation from a given pool.

**Pattern**:
```python
asn_pool = await self.client.get(kind="CoreNumberPool", name__value="otn-asn-pool")
site_node.bgp_asn = asn_pool
await site_node.save(allow_upsert=True)
```

---

## 2. CoreIPAddressPool Allocation Pattern

**Decision**: Use `client.allocate_next_ip_address(resource_pool, identifier=hostname)`. The `identifier` string is the idempotency key — the same identifier always returns the same `IpamIPAddress` node.

**Rationale**: The SDK provides `allocate_next_ip_address()` (async, on `InfrahubClient`) with an `identifier` parameter documented as "value to perform idempotent allocation." Confirmed in SDK source at `infrahub_sdk/client.py`. This is the correct method for `CoreIPAddressPool` (distinct from `allocate_next_ip_prefix()` for `CoreIPPrefixPool`).

**Pattern**:
```python
mgmt_ip = await self.client.allocate_next_ip_address(
    resource_pool=mgmt_pool,
    identifier=hostname,          # idempotent: same hostname → same IP
    data={"description": f"Management IP for {hostname}"},
)
device.primary_address = mgmt_ip
await device.save(allow_upsert=True)
```

---

## 3. Computed Attribute Jinja2 Template Syntax

**Decision**: Use `{{ name__value }}.{{ location__shortname__value }}.otternet.net` with `computed_attribute.kind: Jinja2` and `read_only: true`.

**Rationale**: Infrahub computes Jinja2 attributes on every read. `read_only: true` is mandatory (the validator rejects computed attributes without it). The `__` separator pattern traverses one relationship hop. `location__shortname__value` is the correct path for `DcimGenericDevice.location → LocationGeneric.shortname`.

---

## 4. Schema Extension Order for Migration

**Decision**: Apply `state: absent` on `OtnSiteDesign.bgp_asn` in the same schema load as the new `LocationSite.bgp_asn` extension. Remove `bgp_asn` values from `objects/06_design_patterns.yml` before running `invoke load-objects` after the schema migration.

**Rationale**: If object files still contain `bgp_asn: 65001` for campus designs when the attribute has `state: absent`, the loader will raise a validation error. Schema migration must precede data reload.

---

## 5. Relationship Identifier Convention

**Decision**: `mgmt_pool` relationship uses `identifier: location_site__mgmt_pool` (snake_case, `__` separator, source\_destination pattern).

**Rationale**: Infrahub requires both sides of a bidirectional relationship to share the same `identifier`. `CoreIPAddressPool` has no back-reference to `LocationSite` in the base schema, so the `identifier` only appears on the extension side. The convention is `snake_case` with `__` separator per the Infrahub relationship identifiers rule.

---

## 6. GraphQL Traversal for Computed Attributes

**Decision**: Query `fqdn { value }` directly on the device node — same as any other Text attribute.

**Rationale**: Computed attributes are fully transparent to GraphQL consumers. Infrahub materialises the computed value before serving the response. No special query syntax is required.

---

## 7. primary_address GraphQL Pattern

**Decision**: Query `primary_address { node { address { value } } }` on the device node.

**Rationale**: `primary_address` is a `cardinality: one` relationship on `DcimGenericDevice`. Single relationships use `node` nesting in Infrahub's Relay-style schema. The `address` field on `IpamIPAddress` is an `IPHost` attribute accessed via `.value`.
