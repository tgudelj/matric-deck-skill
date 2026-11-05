"""Acceptance checks for distribution of the standalone skill."""
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package_skill", ROOT / "tools/package_skill.py")
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class PackagingTests(unittest.TestCase):
    def test_packaged_xplane_inventory_runs_without_repository(self):
        with tempfile.TemporaryDirectory(prefix="matric-xplane-package-") as temp:
            root = Path(temp)
            archive, _ = packager.package(root / "release")
            with zipfile.ZipFile(archive) as zipped:
                zipped.extractall(root / "installed")
            profile = root / "X-Plane Keys.prf"
            profile.write_text("I\n1005 version\nG CTRL sim/synthetic/gear\n", encoding="utf-8")
            script = root / "installed/matric-decks/scripts/game_bindings.py"
            result = subprocess.run([sys.executable, "-B", str(script), "inventory", "--game", "xplane",
                                     "--profile", str(profile)], cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["bindings"][0]["candidate"]["KeyCode"], 71)
            self.assertEqual(report["bindings"][0]["candidate"]["Modifiers"], ["LCONTROL"])

    def test_portable_reproducible_payload_and_checksum(self):
        with tempfile.TemporaryDirectory(prefix="matric-package-test-") as temp:
            archive, checksum = packager.package(Path(temp) / "first")
            other, _ = packager.package(Path(temp) / "second")
            self.assertEqual(archive.read_bytes(), other.read_bytes())
            self.assertEqual(checksum.read_text().split()[0], hashlib.sha256(archive.read_bytes()).hexdigest())
            with zipfile.ZipFile(archive) as zipped:
                names = zipped.namelist()
                self.assertIn("matric-decks/SKILL.md", names)
                self.assertIn("matric-decks/assets/additional-resources/deck2.json", names)
                self.assertIn("matric-decks/scripts/obs_inventory.py", names)
                self.assertIn("matric-decks/scripts/obs_live.py", names)
                self.assertIn("matric-decks/scripts/applet_tool.py", names)
                self.assertIn("matric-decks/assets/applet-starter/applet.html", names)
                self.assertIn("matric-decks/assets/applet-starter/bridge.js", names)
                self.assertIn("matric-decks/scripts/dcs_bios.py", names)
                self.assertIn("matric-decks/assets/dcs-demo/SKILL_DEMO.json", names)
                self.assertEqual(zipped.read("matric-decks/LICENSE.txt"), (ROOT / "LICENSE").read_bytes())
                self.assertTrue(all(n.startswith("matric-decks/") for n in names))
                self.assertFalse(any(n.endswith((".dll", ".exe", ".cs", ".pyc")) or "/__pycache__/" in n for n in names))
            with self.assertRaises(FileExistsError):
                packager.package(archive.parent)


if __name__ == "__main__":
    unittest.main()
