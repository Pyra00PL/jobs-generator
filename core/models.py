from dataclasses import asdict, dataclass

@dataclass
class RestrictionRow:
    item_id: str
    use_job: str
    use_level: int
    smith_level: int
    use_types: str
    enabled: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RestrictionRow":
        return cls(
            item_id=str(data["item_id"]),
            use_job=str(data.get("use_job", "warrior")),
            use_level=int(data.get("use_level", 0)),
            smith_level=int(data.get("smith_level", 0)),
            use_types=str(data.get("use_types", "use_item,hurt_entity")),
            enabled=bool(data.get("enabled", True)),
        )
