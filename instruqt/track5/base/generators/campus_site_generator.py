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
    allocate a BGP ASN to the site from the shared pool, and allocate each device
    a management IP from the site's IP pool. Idempotent: ASN/IP allocation is
    keyed (pool + identifier=hostname) and every save uses allow_upsert, so
    re-running upserts rather than duplicating.
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
        self.logger.info(
            "Generating %s — %d device entries",
            site_code,
            len(design["device_entries"]["edges"]),
        )

        # Allocate a BGP ASN from the pool and write it to the site (idempotent).
        site_node = await self.client.get(kind="LocationSite", id=site_id)
        asn_pool = await self.client.get(kind="CoreNumberPool", name__value="otn-asn-pool")
        site_node.bgp_asn = asn_pool
        await site_node.save(allow_upsert=True)
        self.logger.info("Allocated BGP ASN for site %s", site_code)

        # Find or create a per-site management IP pool over the site's prefix.
        # allocate_next_ip_address draws /32s from it, keyed by identifier below.
        mgmt_prefix_value = site["mgmt_prefix"]["node"]["prefix"]["value"]
        mgmt_pools = await self.client.filters(
            kind="CoreIPAddressPool",
            resources__prefix__value=mgmt_prefix_value,
        )
        if mgmt_pools:
            mgmt_pool = mgmt_pools[0]
        else:
            site_shortname = site["shortname"]["value"]
            mgmt_prefix_id = site["mgmt_prefix"]["node"]["id"]
            mgmt_pool = await self.client.create(
                kind="CoreIPAddressPool",
                data={
                    "name": f"{site_shortname}-mgmt-pool",
                    "description": f"Management IP pool for {site_shortname.upper()} site",
                    "default_address_type": "IpamIPAddress",
                    "default_prefix_length": 32,
                    "ip_namespace": "default",
                    "resources": [{"id": mgmt_prefix_id}],
                },
            )
            await mgmt_pool.save(allow_upsert=True)
            self.logger.info("Created management IP pool for site %s", site_code)

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
                # Idempotent: the same identifier (hostname) always resolves to the
                # same allocated IP, regardless of run order.
                mgmt_ip = await self.client.allocate_next_ip_address(
                    resource_pool=mgmt_pool,
                    identifier=hostname,
                    data={"description": f"Management IP for {hostname}"},
                )
                device.primary_address = mgmt_ip
                await device.save(allow_upsert=True)
                self.logger.info("Provisioned %s", hostname)
