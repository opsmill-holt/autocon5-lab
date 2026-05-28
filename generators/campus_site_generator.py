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

        campus_routers_group = await self.client.get(kind="CoreStandardGroup", name__value="campus_routers")
        await campus_routers_group.members.fetch()

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
                    },
                )
                await device.save(allow_upsert=True)

                if role == "router":
                    campus_routers_group.members.add(device)

                self.logger.info("Created device: %s", hostname)

        await campus_routers_group.save()
