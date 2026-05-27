# Feature Specification: Device Template Instantiation — Schema

**Feature Branch**: `002-device-template-instantiation`  
**Created**: 2026-05-27  
**Status**: Draft  
**Artifact Cycle**: 1 of 2 — Schema (Generator spec follows in next cycle)

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define a Device Template (Priority: P1)

A network engineer creates a reusable device template that captures the platform, role, and key configuration defaults for a class of device (e.g., "OtterNet Border Router" with platform IOS-XR, role edge-router). Once created, this template can be referenced across any number of site designs without re-entering the same details.

**Why this priority**: Everything downstream depends on templates existing. No templates means no instantiation.

**Independent Test**: Create a device template, retrieve it by name, and confirm all attributes are persisted correctly.

**Acceptance Scenarios**:

1. **Given** no device templates exist, **When** a user creates a template with a name, platform, and role, **Then** the template is saved and retrievable by name.
2. **Given** a device template exists, **When** a user views it, **Then** all defined attributes (platform, role, description) are visible.
3. **Given** two templates with different names, **When** a user lists all templates, **Then** both appear in the list.

---

### User Story 2 - Reference Templates in a Site Design (Priority: P1)

A network engineer building a campus or data-centre site design selects one or more device templates and specifies how many devices of each type to instantiate (e.g., "2 routers using the Border Router template, 4 access switches using the Access Switch template"). The design stores these template references so the generator knows exactly what to create.

**Why this priority**: The design-to-template linkage is the core of the feature — without it, templates are inert objects with no downstream effect.

**Independent Test**: Create a design, attach two template references with counts, and verify both references are retrievable from the design.

**Acceptance Scenarios**:

1. **Given** a site design and a device template, **When** a user adds a template reference with a count of 2, **Then** the design records that 2 devices of that template are required.
2. **Given** a design with multiple template references, **When** a user views the design, **Then** all template references and their counts are visible.
3. **Given** a design with a template reference, **When** a user updates the count from 2 to 3, **Then** the design reflects the updated count.
4. **Given** a design with a template reference, **When** a user removes the reference, **Then** the design no longer lists that template.

---

### User Story 3 - Validate Template References on Save (Priority: P2)

When a user saves a site design that references a device template, the system confirms the referenced template exists. If a referenced template has been deleted or renamed, the user receives a clear error rather than a silent broken reference.

**Why this priority**: Data integrity guard — prevents orphaned references that would silently produce wrong generator output.

**Independent Test**: Attempt to create a template reference pointing to a non-existent template and confirm an error is returned.

**Acceptance Scenarios**:

1. **Given** a template reference pointing to a deleted template, **When** the design is validated, **Then** an error clearly identifies the missing template.
2. **Given** a valid template reference, **When** the design is saved, **Then** no errors are raised.

---

### Edge Cases

- What happens when a count of 0 is specified in a template reference?
- What happens when the same template is referenced twice in the same design?
- What happens when a template is deleted while a design still references it?
- What happens when a design has no template references at all (generator should produce zero devices)?

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a `DeviceTemplate` entity with at minimum: name (unique), platform, role, and optional description.
- **FR-002**: The system MUST allow a `DeviceTemplate` to be marked as a template so it can be cloned as a starting point for new templates of the same class.
- **FR-003**: The system MUST provide a `DesignDeviceEntry` entity that links a site design to a device template and stores the desired instance count (minimum 1).
- **FR-004**: A site design MUST be able to hold zero or more `DesignDeviceEntry` records.
- **FR-005**: The `DesignDeviceEntry` count MUST be a positive integer; zero and negative values MUST be rejected.
- **FR-006**: Deleting a `DeviceTemplate` that is still referenced by one or more `DesignDeviceEntry` records MUST either be blocked or cascade-delete the referencing entries (behaviour to be determined during planning).
- **FR-007**: The `DeviceTemplate` name MUST be unique across all templates.
- **FR-008**: The schema MUST remain within the existing `Otn` namespace for consistency with the current project.

### Key Entities *(include if feature involves data)*

- **DeviceTemplate**: A reusable blueprint for a class of device. Attributes: name (unique), platform, role, description (optional). Supports clone-from-template UX so common device types (border router, access switch) can be duplicated quickly. Lives in the `Otn` namespace.
- **DesignDeviceEntry**: A junction record that associates a site design with a device template and records how many instances to create. Attributes: count. Relationships: design (OtnSiteDesign), template (OtnDeviceTemplate). Lives in the `Otn` namespace.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A network engineer can create a device template and attach it to a site design with a count in under 2 minutes.
- **SC-002**: All existing site designs continue to load and validate without errors after the schema change is applied.
- **SC-003**: A site design with 5 distinct template references (different templates and counts) is fully retrievable with a single query.
- **SC-004**: Schema validation (`infrahubctl schema check`) passes with zero errors on the updated schema file.
- **SC-005**: Referencing a non-existent template in a design produces a validation error visible to the user.

---

## Assumptions

- The `Otn` namespace is the correct home for both new nodes; no new namespace is introduced.
- `platform` and `role` on `DeviceTemplate` are free-text strings in v1; dropdown/enum constraints are deferred to a later iteration.
- The existing `OtnSiteDesign` generic (and its concrete subtypes `OtnCampusSite`, `OtnDataCenterSite`) will be extended via the `extensions` block rather than modified directly, to preserve backward compatibility.
- The existing numeric count attributes on the design (`router_count`, `access_switch_count`, etc.) may be deprecated or hidden once the template-based approach is validated, but removing them is out of scope for this schema cycle.
- The Generator that reads these template references and creates actual device objects is specified and implemented in a separate feature cycle.
- `DesignDeviceEntry` records are branch-aware (default Infrahub behaviour) so designs can be proposed and reviewed before merging.
