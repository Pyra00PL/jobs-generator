import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from core.compatibility import get_profile
from core.generator import generate_pack


class MinecraftCompatibilityTests(unittest.TestCase):
    def test_legacy_1211_uses_pack_format_48(self) -> None:
        metadata = get_profile("1.21.1").pack_metadata("test")

        self.assertEqual(metadata["pack"]["pack_format"], 48)

    def test_new_format_uses_min_and_max_format(self) -> None:
        metadata = get_profile("26.2").pack_metadata("test")

        self.assertNotIn("pack_format", metadata["pack"])
        self.assertEqual(metadata["pack"]["min_format"], [107, 1])
        self.assertEqual(metadata["pack"]["max_format"], [107, 1])

    def test_selected_profile_is_written_to_export(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "restrictions.zip"
            generate_pack([], output, profile="1.21.4")
            with zipfile.ZipFile(output) as archive:
                metadata = json.loads(
                    archive.read("pack.mcmeta")
                )

        self.assertEqual(metadata["pack"]["pack_format"], 61)


if __name__ == "__main__":
    unittest.main()
