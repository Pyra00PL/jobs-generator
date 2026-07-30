import json
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass
class ModFile:
    file_name: str
    file_path: Path
    file_size_mb: float
    display_name: str
    mod_id: str
    version: str
    authors: str
    loader: str
    read_status: str


def _text(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def scan_mods_folder(folder: Path) -> list[ModFile]:
    if not folder.exists():
        raise FileNotFoundError("Wybrany folder nie istnieje.")
    if not folder.is_dir():
        raise NotADirectoryError("Wybrana ścieżka nie jest folderem.")
    return [read_mod_file(p) for p in sorted(folder.glob("*.jar"), key=lambda x: x.name.lower())]


def read_mod_file(jar_file: Path) -> ModFile:
    size_mb = round(jar_file.stat().st_size / 1048576, 2)
    fallback = ModFile(jar_file.name, jar_file, size_mb, jar_file.stem, "Nieznany", "Nieznana", "Nieznany", "Nieznany", "Nie rozpoznano")
    try:
        with zipfile.ZipFile(jar_file) as zf:
            names = set(zf.namelist())
            for metadata_path, loader in (("META-INF/neoforge.mods.toml", "NeoForge"), ("META-INF/mods.toml", "Forge")):
                if metadata_path in names:
                    data = tomllib.loads(zf.read(metadata_path).decode("utf-8-sig"))
                    mods = data.get("mods", [])
                    if not mods:
                        return fallback
                    mod = mods[0]
                    mod_id = _text(mod.get("modId"), "Nieznany")
                    return ModFile(jar_file.name, jar_file, size_mb, _text(mod.get("displayName"), mod_id), mod_id, _text(mod.get("version"), "Nieznana"), _text(mod.get("authors"), "Nieznany"), loader, "Odczytano")
            if "fabric.mod.json" in names:
                mod = json.loads(zf.read("fabric.mod.json").decode("utf-8-sig"))
                authors_raw = mod.get("authors", [])
                authors = ", ".join(a if isinstance(a, str) else str(a.get("name", "")) for a in authors_raw).strip(", ") or "Nieznany"
                mod_id = _text(mod.get("id"), "Nieznany")
                return ModFile(jar_file.name, jar_file, size_mb, _text(mod.get("name"), mod_id), mod_id, _text(mod.get("version"), "Nieznana"), authors, "Fabric", "Odczytano")
            return fallback
    except (zipfile.BadZipFile, OSError, ValueError, json.JSONDecodeError, tomllib.TOMLDecodeError):
        fallback.read_status = "Błąd odczytu"
        return fallback
