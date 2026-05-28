from infrahub_sdk.generator import InfrahubGenerator

ROLE_CODE = {
    "router": "RTR",
    "distribution": "DSW",
    "access": "ASW",
}


class CampusSiteGenerator(InfrahubGenerator):

    async def generate(self, data: dict) -> None:
        site = data["LocationSite"]["edges"][0]["node"]
        site_id = site["id"]
        site_code = site["shortname"]["value"].upper()

        design = site["design"]["node"]
        if not design or "device_entries" not in design:
            return

        # Allocate BGP ASN from pool and write to site (idempotent)
        site_node = await self.client.get(kind="LocationSite", id=site_id)
        asn_pool = await self.client.get(kind="CoreNumberPool", name__value="otn-asn-pool")
        site_node.bgp_asn = asn_pool
        await site_node.save(allow_upsert=True)
        self.logger.info("Allocated BGP ASN for site: %s", site_code)

        # Get management IP pool for this site
        mgmt_pool_id = site["mgmt_pool"]["node"]["id"]
        mgmt_pool = await self.client.get(kind="CoreIPAddressPool", id=mgmt_pool_id)

        device_config_group = await self.client.get(kind="CoreStandardGroup", name__value="device_config")

        role_counters = {}

        for entry in design["device_entries"]["edges"]:
            count = entry["node"]["count"]["value"]
            template = entry["node"]["template"]["node"]
            role = template.get("role", {}).get("value") if template else None
            template_id = template["id"]

            role_code = ROLE_CODE.get(role, role.upper() if role else "UNK")
            role_counters[role_code] = role_counters.get(role_code, 0)

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
                self.logger.info("Created device: %s", hostname)

                # Allocate management IP (idempotent via hostname identifier)
                mgmt_ip = await self.client.allocate_next_ip_address(
                    resource_pool=mgmt_pool,
                    identifier=hostname,
                    data={"description": f"Management IP for {hostname}"},
                )
                device.primary_address = mgmt_ip
                await device.save(allow_upsert=True)
                self.logger.info("Allocated management IP for: %s", hostname)
