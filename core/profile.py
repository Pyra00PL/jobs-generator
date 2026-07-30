import json
from pathlib import Path
from core.models import RestrictionRow


def save_profile(path: Path, rows: list[RestrictionRow]) -> None:
    payload = {"format": 2, "rows": [row.to_dict() for row in rows]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_profile(path: Path) -> list[RestrictionRow]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [RestrictionRow.from_dict(item) for item in payload.get("rows", [])]
