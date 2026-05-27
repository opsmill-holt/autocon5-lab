from infrahub_sdk.generator import InfrahubGenerator

ROLE_INTERFACES: dict[str, list[str]] = {
    "RTR": ["Loopback0", "GigabitEthernet0/0", "GigabitEthernet0/1"],
    "DSW": ["Loopback0", "GigabitEthernet1/0/1", "GigabitEthernet1/0/2", "GigabitEthernet1/0/3", "GigabitEthernet1/0/4"],
    "ASW": ["Loopback0", "GigabitEthernet0/1", "GigabitEthernet0/2", "GigabitEthernet0/3", "GigabitEthernet0/4"],
}

ROLE_DEVICE_TYPE: dict[str, str] = {
    "RTR": "ISR4451",
    "DSW": "C9300-48P",
    "ASW": "C9300-24P",
}

ROLE_PLATFORM: dict[str, str] = {
    "RTR": "IOS-XE",
    "DSW": "IOS",
    "ASW": "IOS",
}

ROLE_DEVICE_ROLE: dict[str, str | None] = {
    "RTR": "edge",
    "DSW": None,
    "ASW": None,
}


class CampusSiteGenerator(InfrahubGenerator):
    """Design-driven generator: reads a LocationSite's design and provisions devices."""

    async def generate(self, data: dict) -> None:
        edges = data["LocationSite"]["edges"]
        if not edges:
            return

        site_node = edges[0]["node"]
        site_id = site_node["id"]
        site_shortname = site_node["shortname"]["value"]
        site_code = site_shortname.split("-")[0].upper()

        design = site_node["design"]["node"]
        if design is None:
            return

        roles = [
            ("RTR", design["router_count"]["value"]),
            ("DSW", design["distribution_switch_count"]["value"]),
            ("ASW", design["access_switch_count"]["value"]),
        ]

        device_type_cache: dict[str, str] = {}
        platform_cache: dict[str, str] = {}

        for role, count in roles:
            if count == 0:
                continue

            for idx in range(1, count + 1):
                hostname = f"{site_code}-{role}-{idx:02d}"

                if role not in device_type_cache:
                    dt = await self.client.get(kind="DcimDeviceType", name__value=ROLE_DEVICE_TYPE[role])
                    device_type_cache[role] = dt.id

                if role not in platform_cache:
                    plat = await self.client.get(kind="DcimPlatform", name__value=ROLE_PLATFORM[role])
                    platform_cache[role] = plat.id

                device_data: dict = {
                    "name": hostname,
                    "status": "active",
                    "location": site_id,
                    "device_type": device_type_cache[role],
                    "platform": platform_cache[role],
                }
                if ROLE_DEVICE_ROLE[role]:
                    device_data["role"] = ROLE_DEVICE_ROLE[role]

                device = await self.client.create(kind="DcimDevice", data=device_data)
                await device.save(allow_upsert=True)

                for iface_name in ROLE_INTERFACES.get(role, []):
                    iface_kind = "InterfaceVirtual" if iface_name.startswith("Loopback") else "InterfacePhysical"
                    iface = await self.client.create(
                        kind=iface_kind,
                        data={
                            "name": iface_name,
                            "device": device.id,
                            "status": "active",
                        },
                    )
                    await iface.save(allow_upsert=True)
