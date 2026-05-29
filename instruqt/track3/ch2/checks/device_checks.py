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
