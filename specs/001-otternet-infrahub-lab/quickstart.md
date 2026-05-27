# Quickstart: OtterNet Lab Setup

## Prerequisites

- Infrahub running (`invoke start` or pre-started in Instruqt)
- `uv sync` run (dependencies installed)
- Python env activated: `source .venv/bin/activate`

## Step-by-step

```bash
# 1. Get the schema library
uv run invoke schema-library-get

# 2. Load all schemas (library + OTN)
uv run invoke load-schema

# 3. Load seed data (locations, orgs, design instances, lon-01, ams-01)
uv run invoke load-objects

# 4. Verify
uv run infrahubctl schema list | grep Otn
```

## Verify Generator (Challenge 4)

```bash
# After muc-01 site + CampusSite design exist:
uv run infrahubctl generator run --name campus_site_generator --identifier "small-campus"
```

## Verify Transform (Challenge 5)

```bash
uv run infrahubctl transform run --name router_config --identifier "MUC-RTR-01"
```

## Run Checks

```bash
uv run infrahubctl check run --name check_device_hostname
uv run infrahubctl check run --name check_device_site
```
