from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MinecraftProfile:
    key: str
    label: str
    minecraft_versions: tuple[str, ...]
    data_pack_format: int | tuple[int, int]

    def pack_metadata(self, description: str) -> dict[str, Any]:
        if isinstance(self.data_pack_format, int):
            return {
                "pack": {
                    "pack_format": self.data_pack_format,
                    "description": description,
                }
            }
        version = list(self.data_pack_format)
        return {
            "pack": {
                "description": description,
                "min_format": version,
                "max_format": version,
            }
        }


MINECRAFT_PROFILES: tuple[MinecraftProfile, ...] = (
    MinecraftProfile(
        "1.21.1",
        "Minecraft 1.21.1 (Jobs+ / Item Restrictions 9.x)",
        ("1.21", "1.21.1"),
        48,
    ),
    MinecraftProfile(
        "1.21.2",
        "Minecraft 1.21.2–1.21.3",
        ("1.21.2", "1.21.3"),
        57,
    ),
    MinecraftProfile(
        "1.21.4",
        "Minecraft 1.21.4",
        ("1.21.4",),
        61,
    ),
    MinecraftProfile(
        "1.21.5",
        "Minecraft 1.21.5",
        ("1.21.5",),
        71,
    ),
    MinecraftProfile(
        "1.21.6",
        "Minecraft 1.21.6",
        ("1.21.6",),
        80,
    ),
    MinecraftProfile(
        "1.21.7",
        "Minecraft 1.21.7–1.21.8",
        ("1.21.7", "1.21.8"),
        81,
    ),
    MinecraftProfile(
        "1.21.9",
        "Minecraft 1.21.9–1.21.10",
        ("1.21.9", "1.21.10"),
        (88, 0),
    ),
    MinecraftProfile(
        "1.21.11",
        "Minecraft 1.21.11 (Jobs+ / Item Restrictions 19.x)",
        ("1.21.11",),
        (94, 1),
    ),
    MinecraftProfile(
        "26.1",
        "Minecraft 26.1 (Jobs+ / Item Restrictions 20.x)",
        ("26.1", "26.1.1", "26.1.2"),
        (101, 1),
    ),
    MinecraftProfile(
        "26.2",
        "Minecraft 26.2 (Jobs+ / Item Restrictions 20.x)",
        ("26.2",),
        (107, 1),
    ),
)

DEFAULT_PROFILE_KEY = "1.21.1"


def get_profile(key: str) -> MinecraftProfile:
    for profile in MINECRAFT_PROFILES:
        if profile.key == key:
            return profile
    raise ValueError(
        f"Unsupported Minecraft compatibility profile: {key}"
    )
