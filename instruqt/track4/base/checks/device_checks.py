from infrahub_sdk.checks import InfrahubCheck


class CheckDeviceManagementIP(InfrahubCheck):
    """Every active device must have a primary management address assigned.

    `primary_address` is optional in the schema, so a device can be created
    without one — exactly the kind of semantic rule a Python check enforces
    that a schema constraint cannot.
    """

    query = "all_devices"

    def validate(self, data: dict) -> None:
        for edge in data["DcimDevice"]["edges"]:
            node = edge["node"]
            name = node["name"]["value"]
            status = node["status"]["value"]
            primary = node["primary_address"]["node"]

            if status == "active" and primary is None:
                self.log_error(
                    f"Device '{name}' is active but has no primary management "
                    f"address assigned. Assign a management IP before merging.",
                    object_id=node["id"],
                )


class CheckSiteHasBorderRouter(InfrahubCheck):
    """Every provisioned site must have at least one active edge (border) router.

    A schema can't express "this relationship must contain a member whose role
    is edge" — it's an aggregate rule across a site's devices, so it's a Python
    check. Sites with no devices yet (e.g. a freshly created site awaiting the
    generator) are skipped so unprovisioned sites aren't falsely flagged.
    """

    query = "sites_with_devices"

    def validate(self, data: dict) -> None:
        for edge in data["LocationSite"]["edges"]:
            site = edge["node"]
            shortname = site["shortname"]["value"]
            devices = site["devices"]["edges"]
            if not devices:
                continue  # site not provisioned yet — nothing to enforce

            has_border = any(
                dev["node"].get("role", {}).get("value") == "edge"
                and dev["node"].get("status", {}).get("value") == "active"
                for dev in devices
            )
            if not has_border:
                self.log_error(
                    f"Site '{shortname}' has devices but no active edge "
                    f"(border) router. Every provisioned site must have one "
                    f"before merging.",
                    object_id=site["id"],
                )
