import ipaddress

from infrahub_sdk.generator import InfrahubGenerator

ROLE_CODE = {
    "edge": "RTR",
    "spine": "DSW",
    "leaf": "ASW",
}


class CampusSiteGenerator(InfrahubGenerator):
    """Provision a campus site's devices from its design.

    For each site in the target group, read its assigned design and, for every
    device entry, create the right number of devices from the entry's template,
    allocate a BGP ASN to the site from the shared pool, and assign each device a
    management IP carved from the site's management prefix. Idempotent: re-running
    upserts rather than duplicating.
    """

    async def generate(self, data: dict) -> None:
        site = data["LocationSite"]["edges"][0]["node"]
        site_id = site["id"]
        # Site code is the 3-letter prefix of the shortname (muc-01 -> MUC), so
        # device names follow OtterNet's XXX-ROLE-NN convention (e.g. MUC-RTR-01).
        site_code = site["shortname"]["value"].split("-")[0].upper()

        design = site["design"]["node"]
        if not design or "device_entries" not in design:
            # Sites without a design (e.g. lon-01/ams-01) are not generated.
            return

        # The site's management prefix must be set (done in the prep challenge).
        if not site.get("mgmt_prefix") or not site["mgmt_prefix"].get("node"):
            raise ValueError(
                f"Site {site_code!r} has no mgmt_prefix set. Assign a management "
                "prefix to the site before running the generator."
            )
        prefix_value = site["mgmt_prefix"]["node"]["prefix"]["value"]
        network = ipaddress.ip_network(prefix_value, strict=False)
        host_addresses = network.hosts()

        # Allocate a BGP ASN from the pool and write it to the site (idempotent).
        site_node = await self.client.get(kind="LocationSite", id=site_id)
        asn_pool = await self.client.get(kind="CoreNumberPool", name__value="otn-asn-pool")
        site_node.bgp_asn = asn_pool
        await site_node.save(allow_upsert=True)
        self.logger.info("Allocated BGP ASN for site %s", site_code)

        device_config_group = await self.client.get(
            kind="CoreStandardGroup", name__value="device_config"
        )

        role_counters: dict[str, int] = {}

        for entry in design["device_entries"]["edges"]:
            count = entry["node"]["count"]["value"]
            template = entry["node"]["template"]["node"]
            role = template.get("role", {}).get("value") if template else None
            template_id = template["id"]

            role_code = ROLE_CODE.get(role, role.upper() if role else "UNK")
            role_counters.setdefault(role_code, 0)

            for _ in range(count):
                role_counters[role_code] += 1
                hostname = f"{site_code}-{role_code}-{role_counters[role_code]:02d}"

                device = await self.client.create(
                    kind="DcimDevice",
                    data={
                        "name": hostname,
                        "status": "active",
                        "role": role,
                        "location": site_id,
                        "object_template": {"id": template_id},
                        "member_of_groups": [device_config_group],
                    },
                )
                await device.save(allow_upsert=True)

                # Assign a management IP carved from the site's prefix (idempotent).
                mgmt_ip_value = f"{next(host_addresses)}/{network.prefixlen}"
                mgmt_ip = await self.client.create(
                    kind="IpamIPAddress",
                    data={
                        "address": mgmt_ip_value,
                        "description": f"Management IP for {hostname}",
                    },
                )
                await mgmt_ip.save(allow_upsert=True)
                device.primary_address = mgmt_ip
                await device.save(allow_upsert=True)
                self.logger.info("Provisioned %s (%s)", hostname, mgmt_ip_value)
