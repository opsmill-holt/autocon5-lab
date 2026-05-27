# Research: Device Template Instantiation — Schema

**Branch**: `002-device-template-instantiation` | **Date**: 2026-05-27

---

## Decision 1: Junction Node vs Attributed Relationship

**Decision**: Use a concrete `OtnDesignDeviceEntry` junction node to hold the (design, template, count) triple.

**Rationale**: Infrahub relationships cannot carry attributes (e.g., a `count` field directly on the edge). The only way to record how many instances of a template a design requires is a separate node. This is the standard pattern in schema-library and infrahub-demo-dc for "quantity on a relationship" scenarios.

**Alternatives considered**:
- A direct cardinality-many relationship from `OtnSiteDesign` → `OtnDeviceTemplate` without count — rejected because a design needs to specify counts (2 routers, 4 switches). Counting the number of relationship edges would mean duplicating the same template edge twice, which is semantically wrong and would violate uniqueness.
- Adding count attributes directly on `OtnDeviceTemplate` — rejected because count is per-design, not per-template; a template can be used in many designs with different counts.

---

## Decision 2: Component/Parent vs Attribute Relationship for design→entries

**Decision**: `OtnSiteDesign.device_entries` uses `kind: Component` (cardinality many); `OtnDesignDeviceEntry.design` uses `kind: Parent` (cardinality one, required). Deleting a design cascades to delete all its entries.

**Rationale**: An `OtnDesignDeviceEntry` has no meaning without a parent design — it exists solely as a child of the design. The Component/Parent pattern models this ownership correctly and the cascade-on-delete behaviour matches the expected lifecycle. This matches the existing `on_delete: cascade` pattern used in the reference schemas.

**Alternatives considered**:
- `kind: Attribute` (no cascade) — rejected because orphaned entries with no parent design would silently produce wrong generator output.
- Block-delete (no-action on design) — rejected as too restrictive; users should be able to delete a design and have all its device entries cleaned up automatically.

---

## Decision 3: Template deletion behaviour

**Decision**: `OtnDesignDeviceEntry.template` uses `kind: Attribute`, `on_delete: no-action`. Deleting a template that is still referenced leaves entries pointing to a null template; a validation check (separate feature cycle) will surface these orphans.

**Rationale**: A `DcimDeviceTemplate`-style node is a reference catalog item shared across many designs. Auto-cascade-deleting all referencing entries when a template is removed would be too destructive (silently modify multiple designs). Instead, block or warn via a check. The `no-action` default is the safer choice here.

**Alternatives considered**:
- `on_delete: cascade` on the template side — rejected because it silently removes device entries across all designs that reference that template.
- Enforcing referential integrity at the schema level — Infrahub does not support FK-constraint-style blocking at schema definition time; this must be enforced by a check.

---

## Decision 4: OtnDeviceTemplate — generate_template flag

**Decision**: Set `generate_template: true` on `OtnDeviceTemplate`.

**Rationale**: Users will create a handful of "golden" templates (BorderRouter, AccessSwitch, SpineSwitch) and reuse them. The clone-from-template UX lets engineers duplicate an existing template when onboarding a new device model rather than re-entering all fields. This is exactly the use-case the flag is designed for.

**Alternatives considered**:
- Not setting it — the create-from-scratch flow is fine for the first few templates, but as the template library grows, cloning becomes a clear time-saver. No cost to enabling it.

---

## Decision 5: human_friendly_id for OtnDesignDeviceEntry

**Decision**: Composite `human_friendly_id` using `[design__name__value, template__name__value]`. Reference style: `["campus-design-1", "border-router"]`.

**Rationale**: Neither field alone is unique across all entries (many designs can reference the same template; a design can reference many templates). The composite makes the entry uniquely addressable in GraphQL queries and object data files.

**Alternatives considered**:
- UUID-only reference — valid but opaque; harder to use in object YAML files and queries.
- `design__name__value` only — not unique within a design.

---

## Decision 6: Schema file placement

**Decision**: Add both new nodes and the new relationship to the existing `schemas/otn.yml`. No new schema file.

**Rationale**: Both nodes live in the `Otn` namespace and are tightly coupled to the existing `OtnSiteDesign` generic. Splitting into a separate file would require a cross-file `extensions` block and adds indirection with no benefit at this project scale.

**Alternatives considered**:
- New `schemas/otn-templates.yml` — rejected; the project has a single namespace and a single schema file today. Adding a second file for two nodes would be premature fragmentation.

---

## Decision 7: Backward compatibility with existing count attributes

**Decision**: Keep `router_count`, `access_switch_count`, `distribution_switch_count`, `spine_count`, `leaf_count`, `border_leaf_count` on the design nodes unchanged. Do not deprecate them in this schema cycle.

**Rationale**: The existing `CampusSiteGenerator` reads these counts directly. Removing them would break the generator. The migration to template-driven counts is a Generator-cycle concern, not a Schema-cycle concern. Deprecation markers can be added once the Generator is updated.

**Alternatives considered**:
- Mark as `state: deprecated` now — rejected; the generator still uses them and deprecation creates noise in the UI without removing the dependency.
