# Quickstart: Device Template Instantiation — Schema

## What this delivers

Two new schema nodes in `schemas/otn.yml`:

- **`OtnDeviceTemplate`** — a reusable device blueprint (platform, device_type, role)
- **`OtnDesignDeviceEntry`** — links a site design to a template with a count

After loading, engineers can define device templates and attach them to campus/DC designs with quantities (e.g. "2 × BorderRouter, 4 × AccessSwitch").

## Steps

### 1. Edit `schemas/otn.yml`

Add `OtnDeviceTemplate` and `OtnDesignDeviceEntry` to the `nodes:` list, and add the `device_entries` relationship to `OtnSiteDesign` in the `generics:` list. Full YAML is in `data-model.md`.

### 2. Validate

```bash
uv run infrahubctl schema check schemas/
```

Expect: zero errors.

### 3. Load

```bash
uv run infrahubctl schema load schemas/
```

### 4. Smoke test

1. Open the Infrahub UI → create an `OtnDeviceTemplate` named `border-router` with platform `IOS-XE` and device_type `ISR4451`.
2. Open an existing `OtnCampusSite` design → add a `Design Device Entry` → select `border-router` template, count `2`.
3. Verify the entry appears under the design's **Device Entries** panel.

### 5. Verify backward compatibility

Confirm all existing campus and DC designs still load without errors and their count attributes are unchanged.
