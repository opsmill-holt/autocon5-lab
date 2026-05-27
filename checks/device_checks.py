import re

from infrahub_sdk.checks import InfrahubCheck

HOSTNAME_RE = re.compile(r"^[A-Z]{3}-[A-Z]{2,5}-\d{2}$")


class CheckDeviceHostname(InfrahubCheck):
    """Validate that every device hostname matches OtterNet naming convention."""

    query = "all_devices"

    def validate(self, data: dict) -> None:
        for edge in data["DcimDevice"]["edges"]:
            node = edge["node"]
            name = node["name"]["value"]
            if not HOSTNAME_RE.match(name):
                self.log_error(
                    f"Hostname '{name}' does not match OtterNet naming convention "
                    f"(expected ^[A-Z]{{3}}-[A-Z]{{2,5}}-\\d{{2}}$)",
                    object_id=node["id"],
                )


class CheckDeviceSite(InfrahubCheck):
    """Validate that every device is assigned to a LocationSite (not a rack or other location type)."""

    query = "all_devices"

    def validate(self, data: dict) -> None:
        for edge in data["DcimDevice"]["edges"]:
            node = edge["node"]
            name = node["name"]["value"]
            location = node["location"]["node"]

            if location is None:
                self.log_error(
                    f"Device '{name}' has no location assigned",
                    object_id=node["id"],
                )
            elif location["__typename"] != "LocationSite":
                self.log_error(
                    f"Device '{name}' is assigned to a {location['__typename']} "
                    f"(shortname: {location['shortname']['value']}), "
                    f"but must be assigned directly to a LocationSite",
                    object_id=node["id"],
                )
