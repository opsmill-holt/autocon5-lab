# OtterNet Infrahub project

This repository is the OtterNet network automation project for Infrahub: the schema, the seed data, a generator, a transform and checks. It is connected to the Infrahub instance at `http://localhost:8000` as the repository `autocon5-lab`. The Git remote `origin` is the local Gitea server. When a commit is pushed to a branch, Infrahub imports it into the Infrahub branch of the same name.

## Use the Infrahub skills

The Infrahub AI skills are installed in `~/.claude/skills`. Load the matching skill before you change anything, even when the request does not name it:

| Task | Skill |
|------|-------|
| Add or change a node, generic, attribute or relationship in `schemas/` | `infrahub-managing-schemas` |
| Create or change data in `objects/`, or object data in Infrahub | `infrahub-managing-objects` |
| Change `generators/` or a generator query | `infrahub-managing-generators` |
| Change `transforms/`, a transform query or an artifact definition | `infrahub-managing-transforms` |
| Change `checks/` | `infrahub-managing-checks` |
| Answer questions about live data through the Infrahub MCP server | `infrahub-analyzing-data` |

## Project layout

- `.infrahub.yml` registers every schema folder, object folder, GraphQL query, check, generator, transform and artifact definition. A new query, check, generator or transform only works in Infrahub after it is registered here.
- `schemas/base-schemas/`: the `dcim`, `ipam`, `location` and `organization` schemas from the Infrahub Marketplace, pinned to fixed versions. Do not edit them. Extend their nodes instead.
- `schemas/extensions/designs/design.yml`: the OtterNet schema.
  - The `OtnSiteDesign` generic, with `OtnCampusSite` and `OtnDataCenterSite` inheriting from it, and `OtnDesignDeviceEntry`, the devices a design calls for.
  - The `LocationSite` extension, which adds `bgp_asn`, `mgmt_domain`, `design` and `mgmt_prefix` to sites. Add new site attributes to this extension.
- `objects/`: seed data, loaded in file-name order.
  - Sites: `lon-01` and `ams-01` have no design; `muc-01` uses the `small-campus` design.
  - Designs: `small-campus`, `medium-campus`, `large-campus`.
  - Groups: `campus_sites` (the generator's targets) and `device_config` (the artifact's targets).
- `queries/`: GraphQL queries used by the generator, the transform and the checks.
- `generators/campus_site_generator.py`: provisions each site in `campus_sites` from its design: a management prefix, a BGP ASN and devices named `<SITE>-<ROLE>-NN`, such as `MUC-RTR-01`. It must stay idempotent: every allocation is keyed and every save uses `allow_upsert=True`, so it can run again without creating duplicates.
- `transforms/router_config.j2` with `queries/device_config.gql`: the `device_config` Jinja2 transform. The `startup-config` artifact definition renders it for every device in the `device_config` group.
- `checks/`: checks that run in proposed changes.

## Commands

The Python environment in `/playground/.venv` has `infrahubctl` and the Infrahub SDK. `INFRAHUB_ADDRESS` and `INFRAHUB_API_TOKEN` are set in the shell and in `infrahubctl.toml`.

- Create a branch in Infrahub and in Git: `infrahubctl branch create <name> --sync-with-git`. Infrahub creates the Git branch a few seconds later; run `git fetch` before you check it out.
- Validate the schema: `infrahubctl schema check schemas/ --branch <name>`
- Load the schema: `infrahubctl schema load schemas/ --branch <name>`
- Load object data: `infrahubctl object load objects/ --branch <name>`
- Run the generator with the local code: `infrahubctl generator campus_site_generator --branch <name> name=muc-01`
- Render the transform with the local code: `infrahubctl render device_config device=MUC-RTR-01 --branch <name>`

## Rules

- Work on a branch. Every command that changes schema or data takes `--branch <name>`. Never load to `main`: changes reach `main` only through a proposed change that a person reviews and merges.
- New attributes on existing nodes are `optional: true` or have a `default_value`, because existing nodes have no value for them.
- Show the diff before you commit. Commit only the files the task changed, then push to the branch of the same name on `origin`.
- Do not commit `.mcp.json`: it holds an API token.
