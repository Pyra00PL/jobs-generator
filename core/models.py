from dataclasses import asdict, dataclass

@dataclass
class RestrictionRow:
    item_id: str
    use_job: str
    use_level: int
    smith_level: int
    use_types: str
    smith_job: str = "smith"
    enchant_job: str = "enchanter"
    enchant_level: int = 0
    repair_job: str = "smith"
    repair_level: int = 0
    enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RestrictionRow":
        use_level = int(data.get("use_level", 0))
        raw_types = [
            entry.strip()
            for entry in str(
                data.get(
                    "use_types",
                    "use_item,hurt_entity",
                )
            ).split(",")
            if entry.strip()
        ]
        legacy_enchant = "enchant" in raw_types
        legacy_repair = "repair" in raw_types
        use_types = ",".join(
            entry
            for entry in raw_types
            if entry not in {"enchant", "repair"}
        )
        return cls(
            item_id=str(data["item_id"]),
            use_job=str(data.get("use_job", "warrior")),
            use_level=use_level,
            smith_level=int(data.get("smith_level", 0)),
            use_types=use_types,
            smith_job=str(data.get("smith_job", "smith")),
            enchant_job=str(
                data.get("enchant_job", "enchanter")
            ),
            enchant_level=int(
                data.get(
                    "enchant_level",
                    use_level if legacy_enchant else 0,
                )
            ),
            repair_job=str(
                data.get("repair_job", "smith")
            ),
            repair_level=int(
                data.get(
                    "repair_level",
                    use_level if legacy_repair else 0,
                )
            ),
            enabled=bool(data.get("enabled", True)),
        )
