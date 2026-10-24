"""Acceptance checks for distribution of the standalone skill."""
import hashlib
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package_skill", ROOT / "tools/package_skill.py")
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class PackagingTests(unittest.TestCase):
    def test_portable_reproducible_payload_and_checksum(self):
        with tempfile.TemporaryDirectory(prefix="matric-package-test-") as temp:
            archive, checksum = packager.package(Path(temp) / "first")
            other, _ = packager.package(Path(temp) / "second")
            self.assertEqual(archive.read_bytes(), other.read_bytes())
            self.assertEqual(checksum.read_text().split()[0], hashlib.sha256(archive.read_bytes()).hexdigest())
            with zipfile.ZipFile(archive) as zipped:
                names = zipped.namelist()
                self.assertIn("matric-decks/SKILL.md", names)
                self.assertIn("matric-decks/scripts/obs_inventory.py", names)
                self.assertIn("matric-decks/scripts/obs_live.py", names)
                self.assertIn("matric-decks/scripts/dcs_bios.py", names)
                self.assertIn("matric-decks/assets/dcs-demo/SKILL_DEMO.json", names)
                self.assertEqual(zipped.read("matric-decks/LICENSE.txt"), (ROOT / "LICENSE").read_bytes())
                self.assertTrue(all(n.startswith("matric-decks/") for n in names))
                self.assertFalse(any(n.endswith((".dll", ".exe", ".cs", ".pyc")) or "/__pycache__/" in n for n in names))
            with self.assertRaises(FileExistsError):
                packager.package(archive.parent)


if __name__ == "__main__":
    unittest.main()
