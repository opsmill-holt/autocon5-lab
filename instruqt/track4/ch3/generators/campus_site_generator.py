from infrahub_sdk.generator import InfrahubGenerator


class CampusSiteGenerator(InfrahubGenerator):
    """Provision a campus site's devices from its assigned design.

    For each site in the target group: make sure the site has a management
    prefix (allocated from the shared pool if it doesn't have one) and a BGP
    ASN, then for every device entry in its design create `count` devices from
    the entry's template — named <SITE>-<PREFIX>-NN — each with a management IP
    from the site's pool. Idempotent: every allocation is keyed and every save
    uses allow_upsert, so re-running upserts instead of duplicating.
    """

    async def generate(self, data: dict) -> None:
        site = data["LocationSite"]["edges"][0]["node"]
        site_id = site["id"]
        # muc-01 -> MUC, so device names follow OtterNet's XXX-ROLE-NN convention.
        site_code = site["shortname"]["value"].split("-")[0].upper()

        design = site["design"]["node"]
        if not design or "device_entries" not in design:
            return  # sites without a design (e.g. lon-01/ams-01) are skipped

        site_node = await self.client.get(kind="LocationSite", id=site_id)

        # Management prefix: if the site doesn't have one, allocate a /24 from the
        # shared pool and assign it. Keyed by site code, so re-runs are idempotent.
        if site["mgmt_prefix"]["node"]:
            mgmt_prefix_id = site["mgmt_prefix"]["node"]["id"]
        else:
            prefix_pool = await self.client.get(
                kind="CoreIPPrefixPool", name__value="otn-mgmt-prefix-pool"
            )
            mgmt_prefix = await self.client.allocate_next_ip_prefix(
                resource_pool=prefix_pool, identifier=site_code
            )
            mgmt_prefix_id = mgmt_prefix.id
            site_node.mgmt_prefix = mgmt_prefix

        # BGP ASN from the shared number pool (keyed to the site).
        asn_pool = await self.client.get(kind="CoreNumberPool", name__value="otn-asn-pool")
        site_node.bgp_asn = asn_pool
        await site_node.save(allow_upsert=True)

        # A per-site /32 pool over the site's management prefix.
        mgmt_pool = await self.client.create(
            kind="CoreIPAddressPool",
            data={
                "name": f"{site['shortname']['value']}-mgmt-pool",
                "default_address_type": "IpamIPAddress",
                "default_prefix_length": 32,
                "ip_namespace": "default",
                "resources": [{"id": mgmt_prefix_id}],
            },
        )
        await mgmt_pool.save(allow_upsert=True)

        for device_entry in design["device_entries"]["edges"]:
            entry = device_entry["node"]
            prefix = entry["device_hostname_prefix"]["value"]
            template_id = entry["template"]["node"]["id"]

            for index in range(1, entry["count"]["value"] + 1):
                hostname = f"{site_code}-{prefix}-{index:02d}"
                # Allocate the management IP first so the device is saved only once.
                mgmt_ip = await self.client.allocate_next_ip_address(
                    resource_pool=mgmt_pool, identifier=hostname
                )
                device = await self.client.create(
                    kind="DcimDevice",
                    data={
                        "name": hostname,
                        "status": "active",
                        "location": site_id,
                        "object_template": {"id": template_id},
                        "primary_address": mgmt_ip,
                        "member_of_groups": ["device_config"],
                    },
                )
                await device.save(allow_upsert=True)
                self.logger.info("Provisioned %s", hostname)
