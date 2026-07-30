from __future__ import annotations

import json
import math
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw
except ImportError:  # Program nadal działa bez Pillow, ale używa surowych PNG.
    Image = None
    ImageDraw = None


def read_item_icons(jar_file: Path, item_ids: set[str]) -> dict[str, bytes]:
    """Odczytuje możliwie najlepszą teksturę PNG dla podanych Item ID."""

    icons: dict[str, bytes] = {}
    if not item_ids:
        return icons

    try:
        with zipfile.ZipFile(jar_file) as archive:
            entries = {
                entry.replace("\\", "/").lower(): entry
                for entry in archive.namelist()
            }
            png_by_name: dict[str, list[str]] = {}
            for normalized, original in entries.items():
                if not normalized.endswith(".png"):
                    continue
                png_by_name.setdefault(Path(normalized).name, []).append(original)

            for item_id in item_ids:
                normalized_id = item_id.strip().lower()
                if ":" not in normalized_id:
                    continue
                namespace, item_path = normalized_id.split(":", 1)
                try:
                    rendered = render_inventory_icon(
                        archive,
                        entries,
                        png_by_name,
                        namespace,
                        item_path,
                    )
                except (KeyError, OSError, TypeError, ValueError):
                    rendered = None
                if rendered:
                    icons[normalized_id] = rendered
                    continue
                texture_entry = resolve_item_texture(
                    archive,
                    entries,
                    png_by_name,
                    namespace,
                    item_path,
                )
                if not texture_entry:
                    continue
                try:
                    raw_texture = archive.read(texture_entry)
                    icons[normalized_id] = (
                        normalize_sprite(raw_texture)
                        or raw_texture
                    )
                except (KeyError, OSError):
                    continue
    except (OSError, zipfile.BadZipFile):
        return {}

    return icons


def render_inventory_icon(
    archive: zipfile.ZipFile,
    entries: dict[str, str],
    png_by_name: dict[str, list[str]],
    namespace: str,
    item_path: str,
) -> bytes | None:
    if Image is None:
        return None

    model = load_model_definition(
        archive,
        entries,
        namespace,
        f"item/{item_path}",
    )
    elements = model.get("elements") if isinstance(model, dict) else None
    if isinstance(elements, list) and elements:
        rendered = render_element_model(
            archive,
            entries,
            namespace,
            model,
        )
        if rendered:
            return rendered

    texture_entry = resolve_item_texture(
        archive,
        entries,
        png_by_name,
        namespace,
        item_path,
    )
    if not texture_entry:
        return None
    try:
        texture = archive.read(texture_entry)
    except (KeyError, OSError):
        return None

    is_entity_atlas = "/textures/entity/" in texture_entry.replace(
        "\\",
        "/",
    ).lower()
    if is_entity_atlas and "buckler" in item_path.lower():
        buckler = render_round_shield_sprite(texture)
        if buckler:
            return buckler
    return normalize_sprite(texture, largest_component=is_entity_atlas)


def load_model_definition(
    archive: zipfile.ZipFile,
    entries: dict[str, str],
    namespace: str,
    model_path: str,
    visited: set[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    if visited is None:
        visited = set()
    key = (namespace, model_path)
    if key in visited or len(visited) >= 16:
        return {}
    visited.add(key)

    entry_path = f"assets/{namespace}/models/{model_path}.json".lower()
    original_path = entries.get(entry_path)
    if not original_path:
        return {}
    try:
        payload = json.loads(archive.read(original_path).decode("utf-8-sig"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}

    merged: dict[str, Any] = {}
    parent = payload.get("parent")
    if isinstance(parent, str) and parent not in {
        "builtin/entity",
        "builtin/generated",
    }:
        parent_namespace, parent_path = split_resource_location(
            parent,
            namespace,
        )
        merged.update(
            load_model_definition(
                archive,
                entries,
                parent_namespace,
                parent_path,
                visited,
            )
        )

    for key_name, value in payload.items():
        if key_name in {"textures", "display"} and isinstance(value, dict):
            inherited = merged.get(key_name, {})
            combined = dict(inherited) if isinstance(inherited, dict) else {}
            combined.update(value)
            merged[key_name] = combined
        else:
            merged[key_name] = value
    return merged


def normalize_sprite(
    texture_bytes: bytes,
    largest_component: bool = False,
    output_size: int = 64,
) -> bytes | None:
    if Image is None:
        return None
    try:
        image = Image.open(BytesIO(texture_bytes)).convert("RGBA")
    except (OSError, ValueError):
        return None

    if largest_component:
        component_box = largest_alpha_component_box(image)
        if component_box:
            image = image.crop(component_box)
    else:
        alpha_box = image.getchannel("A").getbbox()
        if alpha_box:
            image = image.crop(alpha_box)

    if image.width <= 0 or image.height <= 0:
        return None
    available = max(1, output_size - 8)
    scale = min(available / image.width, available / image.height)
    new_size = (
        max(1, round(image.width * scale)),
        max(1, round(image.height * scale)),
    )
    resampling = (
        Image.Resampling.NEAREST
        if max(image.width, image.height) <= 128
        else Image.Resampling.LANCZOS
    )
    image = image.resize(new_size, resampling)
    canvas = Image.new("RGBA", (output_size, output_size), (0, 0, 0, 0))
    canvas.alpha_composite(
        image,
        (
            (output_size - image.width) // 2,
            (output_size - image.height) // 2,
        ),
    )
    return image_to_png(canvas)


def render_round_shield_sprite(
    texture_bytes: bytes,
    output_size: int = 64,
) -> bytes | None:
    if Image is None or ImageDraw is None:
        return None
    try:
        source = Image.open(BytesIO(texture_bytes)).convert("RGBA")
    except (OSError, ValueError):
        return None

    colors = [
        pixel
        for pixel in source.getdata()
        if pixel[3] > 16
    ]
    if not colors:
        return None
    red = round(sum(color[0] for color in colors) / len(colors))
    green = round(sum(color[1] for color in colors) / len(colors))
    blue = round(sum(color[2] for color in colors) / len(colors))
    base = (red, green, blue, 255)
    dark = (
        max(0, round(red * 0.38)),
        max(0, round(green * 0.38)),
        max(0, round(blue * 0.38)),
        255,
    )
    light = (
        min(255, round(red * 1.35 + 18)),
        min(255, round(green * 1.35 + 18)),
        min(255, round(blue * 1.35 + 18)),
        255,
    )

    canvas = Image.new("RGBA", (output_size, output_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((8, 8, 56, 56), fill=dark)
    draw.ellipse((11, 11, 53, 53), fill=base)
    draw.arc((13, 13, 51, 51), 205, 335, fill=light, width=3)
    draw.arc((13, 13, 51, 51), 25, 155, fill=dark, width=3)
    draw.ellipse((25, 25, 39, 39), fill=dark)
    draw.ellipse((28, 28, 36, 36), fill=light)
    return image_to_png(canvas)


def largest_alpha_component_box(image) -> tuple[int, int, int, int] | None:
    alpha = image.getchannel("A")
    width, height = image.size
    visible = {
        (x, y)
        for y in range(height)
        for x in range(width)
        if alpha.getpixel((x, y)) > 8
    }
    largest: list[tuple[int, int]] = []
    while visible:
        start = visible.pop()
        stack = [start]
        component = [start]
        while stack:
            x, y = stack.pop()
            for neighbor in (
                (x - 1, y),
                (x + 1, y),
                (x, y - 1),
                (x, y + 1),
            ):
                if neighbor in visible:
                    visible.remove(neighbor)
                    stack.append(neighbor)
                    component.append(neighbor)
        if len(component) > len(largest):
            largest = component
    if not largest:
        return alpha.getbbox()
    xs = [point[0] for point in largest]
    ys = [point[1] for point in largest]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def render_element_model(
    archive: zipfile.ZipFile,
    entries: dict[str, str],
    namespace: str,
    model: dict[str, Any],
    output_size: int = 64,
) -> bytes | None:
    if Image is None:
        return None

    textures = model.get("textures", {})
    if not isinstance(textures, dict):
        textures = {}
    texture_images: dict[str, Any] = {}
    for name, reference in textures.items():
        if not isinstance(name, str) or not isinstance(reference, str):
            continue
        resolved = resolve_texture_reference(reference, textures)
        if not resolved:
            continue
        texture_namespace, texture_path = split_resource_location(
            resolved,
            namespace,
        )
        entry = entries.get(
            f"assets/{texture_namespace}/textures/{texture_path}.png".lower()
        )
        if not entry:
            continue
        try:
            texture_images[name] = Image.open(
                BytesIO(archive.read(entry))
            ).convert("RGBA")
        except (KeyError, OSError, ValueError):
            continue
    if not texture_images:
        return None

    texture_size = model.get("texture_size", [16, 16])
    if (
        not isinstance(texture_size, list)
        or len(texture_size) < 2
        or not all(isinstance(value, (int, float)) for value in texture_size[:2])
    ):
        texture_size = [16, 16]

    gui = model.get("display", {}).get("gui", {})
    if not isinstance(gui, dict):
        gui = {}
    gui_rotation = vector3(gui.get("rotation"), (30.0, 225.0, 0.0))
    gui_scale = vector3(gui.get("scale"), (1.0, 1.0, 1.0))
    gui_translation = vector3(gui.get("translation"), (0.0, 0.0, 0.0))

    faces_to_draw: list[
        tuple[list[tuple[float, float, float]], list[tuple[float, float]], Any, float]
    ] = []
    for element in model.get("elements", []):
        if not isinstance(element, dict):
            continue
        from_pos = vector3(element.get("from"), (0.0, 0.0, 0.0))
        to_pos = vector3(element.get("to"), (16.0, 16.0, 16.0))
        element_rotation = element.get("rotation", {})
        if not isinstance(element_rotation, dict):
            element_rotation = {}
        rotation_axis = str(element_rotation.get("axis", "y")).lower()
        rotation_angle = safe_float(
            element_rotation.get("angle"),
            0.0,
        )
        rotation_origin = vector3(
            element_rotation.get("origin"),
            (8.0, 8.0, 8.0),
        )

        for face_name, face_data in element.get("faces", {}).items():
            if not isinstance(face_data, dict):
                continue
            texture_reference = face_data.get("texture")
            if not isinstance(texture_reference, str):
                continue
            texture_name = texture_reference.lstrip("#")
            texture = texture_images.get(texture_name)
            if texture is None:
                continue

            vertices = cuboid_face_vertices(from_pos, to_pos, face_name)
            if not vertices:
                continue
            transformed: list[tuple[float, float, float]] = []
            for vertex in vertices:
                vertex = rotate_about_axis(
                    vertex,
                    rotation_origin,
                    rotation_axis,
                    rotation_angle,
                )
                centered = (
                    (vertex[0] - 8.0) * gui_scale[0],
                    (vertex[1] - 8.0) * gui_scale[1],
                    (vertex[2] - 8.0) * gui_scale[2],
                )
                centered = rotate_xyz(centered, gui_rotation)
                transformed.append((
                    centered[0] + gui_translation[0],
                    centered[1] + gui_translation[1],
                    centered[2] + gui_translation[2],
                ))

            uv = face_data.get("uv", [0, 0, texture_size[0], texture_size[1]])
            if (
                not isinstance(uv, list)
                or len(uv) < 4
                or not all(isinstance(value, (int, float)) for value in uv[:4])
            ):
                uv = [0, 0, texture_size[0], texture_size[1]]
            uv_corners = [
                (float(uv[0]), float(uv[1])),
                (float(uv[2]), float(uv[1])),
                (float(uv[2]), float(uv[3])),
                (float(uv[0]), float(uv[3])),
            ]
            face_rotation = int(face_data.get("rotation", 0)) % 360
            for _ in range(face_rotation // 90):
                uv_corners = uv_corners[1:] + uv_corners[:1]
            shade = {
                "up": 1.0,
                "down": 0.62,
                "north": 0.82,
                "south": 0.95,
                "west": 0.72,
                "east": 0.88,
            }.get(str(face_name), 1.0)
            faces_to_draw.append(
                (transformed, uv_corners, texture, shade)
            )

    if not faces_to_draw:
        return None

    all_vertices = [
        vertex
        for vertices, _, _, _ in faces_to_draw
        for vertex in vertices
    ]
    min_x = min(vertex[0] for vertex in all_vertices)
    max_x = max(vertex[0] for vertex in all_vertices)
    min_y = min(vertex[1] for vertex in all_vertices)
    max_y = max(vertex[1] for vertex in all_vertices)
    model_width = max(max_x - min_x, 0.001)
    model_height = max(max_y - min_y, 0.001)
    scale = (output_size - 8) / max(model_width, model_height)
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    canvas = Image.new("RGBA", (output_size, output_size), (0, 0, 0, 0))
    z_buffer = [
        [float("-inf")] * output_size
        for _ in range(output_size)
    ]
    for vertices, uv_corners, texture, shade in faces_to_draw:
        screen_vertices = [
            (
                output_size / 2 + (vertex[0] - center_x) * scale,
                output_size / 2 - (vertex[1] - center_y) * scale,
                vertex[2],
            )
            for vertex in vertices
        ]
        rasterize_triangle(
            canvas,
            z_buffer,
            (screen_vertices[0], screen_vertices[1], screen_vertices[2]),
            (uv_corners[0], uv_corners[1], uv_corners[2]),
            texture,
            (float(texture_size[0]), float(texture_size[1])),
            shade,
        )
        rasterize_triangle(
            canvas,
            z_buffer,
            (screen_vertices[0], screen_vertices[2], screen_vertices[3]),
            (uv_corners[0], uv_corners[2], uv_corners[3]),
            texture,
            (float(texture_size[0]), float(texture_size[1])),
            shade,
        )

    alpha_box = canvas.getchannel("A").getbbox()
    if not alpha_box:
        return None
    return normalize_sprite(image_to_png(canvas), output_size=output_size)


def rasterize_triangle(
    canvas,
    z_buffer: list[list[float]],
    vertices: tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ],
    uvs: tuple[
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ],
    texture,
    texture_units: tuple[float, float],
    shade: float,
) -> None:
    x_values = [vertex[0] for vertex in vertices]
    y_values = [vertex[1] for vertex in vertices]
    width, height = canvas.size
    min_x = max(0, math.floor(min(x_values)))
    max_x = min(width - 1, math.ceil(max(x_values)))
    min_y = max(0, math.floor(min(y_values)))
    max_y = min(height - 1, math.ceil(max(y_values)))

    x1, y1, _ = vertices[0]
    x2, y2, _ = vertices[1]
    x3, y3, _ = vertices[2]
    denominator = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
    if abs(denominator) < 1e-8:
        return

    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            sample_x = x + 0.5
            sample_y = y + 0.5
            weight1 = (
                (y2 - y3) * (sample_x - x3)
                + (x3 - x2) * (sample_y - y3)
            ) / denominator
            weight2 = (
                (y3 - y1) * (sample_x - x3)
                + (x1 - x3) * (sample_y - y3)
            ) / denominator
            weight3 = 1.0 - weight1 - weight2
            if min(weight1, weight2, weight3) < -1e-6:
                continue

            depth = sum(
                weight * vertex[2]
                for weight, vertex in zip(
                    (weight1, weight2, weight3),
                    vertices,
                )
            )
            if depth < z_buffer[y][x]:
                continue

            u = sum(
                weight * uv[0]
                for weight, uv in zip(
                    (weight1, weight2, weight3),
                    uvs,
                )
            )
            v = sum(
                weight * uv[1]
                for weight, uv in zip(
                    (weight1, weight2, weight3),
                    uvs,
                )
            )
            tex_x = max(
                0,
                min(
                    texture.width - 1,
                    int(u / max(texture_units[0], 0.001) * texture.width),
                ),
            )
            tex_y = max(
                0,
                min(
                    texture.height - 1,
                    int(v / max(texture_units[1], 0.001) * texture.height),
                ),
            )
            red, green, blue, alpha = texture.getpixel((tex_x, tex_y))
            if alpha <= 8:
                continue
            color = (
                min(255, round(red * shade)),
                min(255, round(green * shade)),
                min(255, round(blue * shade)),
                alpha,
            )
            canvas.putpixel((x, y), color)
            z_buffer[y][x] = depth


def cuboid_face_vertices(
    from_pos: tuple[float, float, float],
    to_pos: tuple[float, float, float],
    face: str,
) -> list[tuple[float, float, float]]:
    x1, y1, z1 = from_pos
    x2, y2, z2 = to_pos
    return {
        "north": [(x2, y2, z1), (x1, y2, z1), (x1, y1, z1), (x2, y1, z1)],
        "south": [(x1, y2, z2), (x2, y2, z2), (x2, y1, z2), (x1, y1, z2)],
        "east": [(x2, y2, z2), (x2, y2, z1), (x2, y1, z1), (x2, y1, z2)],
        "west": [(x1, y2, z1), (x1, y2, z2), (x1, y1, z2), (x1, y1, z1)],
        "up": [(x1, y2, z1), (x2, y2, z1), (x2, y2, z2), (x1, y2, z2)],
        "down": [(x1, y1, z2), (x2, y1, z2), (x2, y1, z1), (x1, y1, z1)],
    }.get(str(face), [])


def vector3(
    value: Any,
    fallback: tuple[float, float, float],
) -> tuple[float, float, float]:
    if (
        isinstance(value, list)
        and len(value) >= 3
        and all(isinstance(number, (int, float)) for number in value[:3])
    ):
        return float(value[0]), float(value[1]), float(value[2])
    return fallback


def safe_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def rotate_about_axis(
    point: tuple[float, float, float],
    origin: tuple[float, float, float],
    axis: str,
    angle: float,
) -> tuple[float, float, float]:
    translated = (
        point[0] - origin[0],
        point[1] - origin[1],
        point[2] - origin[2],
    )
    rotated = rotate_axis(translated, axis, angle)
    return (
        rotated[0] + origin[0],
        rotated[1] + origin[1],
        rotated[2] + origin[2],
    )


def rotate_xyz(
    point: tuple[float, float, float],
    rotation: tuple[float, float, float],
) -> tuple[float, float, float]:
    point = rotate_axis(point, "x", rotation[0])
    point = rotate_axis(point, "y", rotation[1])
    return rotate_axis(point, "z", rotation[2])


def rotate_axis(
    point: tuple[float, float, float],
    axis: str,
    angle: float,
) -> tuple[float, float, float]:
    radians = math.radians(angle)
    sine = math.sin(radians)
    cosine = math.cos(radians)
    x, y, z = point
    if axis == "x":
        return x, y * cosine - z * sine, y * sine + z * cosine
    if axis == "z":
        return x * cosine - y * sine, x * sine + y * cosine, z
    return x * cosine + z * sine, y, -x * sine + z * cosine


def image_to_png(image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def resolve_item_texture(
    archive: zipfile.ZipFile,
    entries: dict[str, str],
    png_by_name: dict[str, list[str]],
    namespace: str,
    item_path: str,
) -> str | None:
    textures = load_model_textures(
        archive,
        entries,
        namespace,
        f"item/{item_path}",
    )
    preferred_keys = ("layer0", "0", "base", "all", "particle")
    ordered_values: list[str] = []
    for key in preferred_keys:
        if key in textures:
            ordered_values.append(textures[key])
    ordered_values.extend(
        value for key, value in textures.items()
        if key not in preferred_keys
    )

    for reference in ordered_values:
        resolved = resolve_texture_reference(reference, textures)
        if not resolved or resolved.startswith("#"):
            continue
        texture_namespace, texture_path = split_resource_location(
            resolved,
            namespace,
        )
        candidate = (
            f"assets/{texture_namespace}/textures/{texture_path}.png"
        ).lower()
        if candidate in entries:
            return entries[candidate]

    direct_candidates = (
        f"assets/{namespace}/textures/item/{item_path}.png",
        f"assets/{namespace}/textures/items/{item_path}.png",
        f"assets/{namespace}/textures/entity/{item_path}.png",
        f"assets/{namespace}/textures/entity/{item_path}_nopattern.png",
    )
    for candidate in direct_candidates:
        normalized = candidate.lower()
        if normalized in entries:
            return entries[normalized]

    file_names = (
        f"{Path(item_path).name}.png",
        f"{Path(item_path).name}_nopattern.png",
    )
    for file_name in file_names:
        matches = png_by_name.get(file_name.lower(), [])
        namespace_prefix = f"assets/{namespace}/"
        for match in matches:
            if match.replace("\\", "/").lower().startswith(namespace_prefix):
                return match
    return None


def load_model_textures(
    archive: zipfile.ZipFile,
    entries: dict[str, str],
    namespace: str,
    model_path: str,
    visited: set[tuple[str, str]] | None = None,
) -> dict[str, str]:
    if visited is None:
        visited = set()
    key = (namespace, model_path)
    if key in visited or len(visited) >= 16:
        return {}
    visited.add(key)

    entry_path = f"assets/{namespace}/models/{model_path}.json".lower()
    original_path = entries.get(entry_path)
    if not original_path:
        return {}
    try:
        payload = json.loads(archive.read(original_path).decode("utf-8-sig"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}

    merged: dict[str, str] = {}
    parent = payload.get("parent")
    if isinstance(parent, str) and parent not in {
        "builtin/entity",
        "builtin/generated",
    }:
        parent_namespace, parent_path = split_resource_location(
            parent,
            namespace,
        )
        merged.update(
            load_model_textures(
                archive,
                entries,
                parent_namespace,
                parent_path,
                visited,
            )
        )

    textures = payload.get("textures")
    if isinstance(textures, dict):
        for name, value in textures.items():
            if isinstance(name, str) and isinstance(value, str):
                merged[name] = value
    return merged


def resolve_texture_reference(
    reference: str,
    textures: dict[str, str],
) -> str | None:
    current = reference
    visited: set[str] = set()
    while current.startswith("#"):
        variable = current[1:]
        if variable in visited:
            return None
        visited.add(variable)
        next_value = textures.get(variable)
        if not next_value:
            return None
        current = next_value
    return current


def split_resource_location(
    value: str,
    default_namespace: str,
) -> tuple[str, str]:
    if ":" in value:
        namespace, path = value.split(":", 1)
        return namespace.lower(), path.lower()
    return default_namespace.lower(), value.lower()


def find_minecraft_client_jar(
    mods_folder: Path,
    version: str = "1.21.1",
) -> Path | None:
    """Próbuje znaleźć klienta Minecrafta używanego przez CurseForge."""

    candidates = [
        mods_folder.parent.parent.parent
        / "Install"
        / "versions"
        / version
        / f"{version}.jar",
        Path.home()
        / "AppData"
        / "Roaming"
        / ".minecraft"
        / "versions"
        / version
        / f"{version}.jar",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None
