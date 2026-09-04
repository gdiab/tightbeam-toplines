from __future__ import annotations

import hashlib
import importlib.machinery
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "tb-toplines-verify-install"


def load_gate():
    loader = importlib.machinery.SourceFileLoader(
        "tb_toplines_verify_install", str(SCRIPT)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError("cannot create import spec")
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


class InstallGateTest(unittest.TestCase):
    """Fail-closed behaviour of the install-provenance gate.

    The real artifacts are not reproducible here, so the gate's logic is
    exercised against a synthetic install root whose files are pinned to their
    own real sha256. Flipping a pin, altering a file, or removing a file must
    each abort with a non-zero status and nothing green.
    """

    def setUp(self) -> None:
        self.gate = load_gate()
        self.temporary = tempfile.TemporaryDirectory(prefix="toplines-gate-")
        self.root = Path(self.temporary.name)
        contents = {
            "bin/tb-toplines-gen": b"#!/usr/bin/env python3\n# generator\n",
            "bin/tb-toplines-serve": b"#!/usr/bin/env python3\n# server\n",
            "web/index.html": b"<!doctype html><title>TopLines</title>\n",
            "systemd/tb-toplines.service": b"[Service]\nExecStart=/bin/true\n",
        }
        pins: dict[str, str] = {}
        for relpath, data in contents.items():
            target = self.root / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            pins[relpath] = hashlib.sha256(data).hexdigest()
        # Point the gate at this synthetic tree instead of the host install.
        self.gate.PINS = dict(pins)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_all_match_passes(self) -> None:
        self.assertEqual(self.gate.verify(self.root), [])
        self.assertEqual(self.gate.main(["--root", str(self.root)]), 0)

    def test_flipped_pin_aborts(self) -> None:
        relpath = "bin/tb-toplines-gen"
        self.gate.PINS[relpath] = "0" * 64
        failures = self.gate.verify(self.root)
        self.assertEqual(len(failures), 1)
        self.assertIn(relpath, failures[0])
        self.assertIn("ALTERED", failures[0])
        self.assertEqual(self.gate.main(["--root", str(self.root)]), 1)

    def test_altered_artifact_aborts(self) -> None:
        (self.root / "web/index.html").write_bytes(b"<script>evil()</script>\n")
        self.assertEqual(self.gate.main(["--root", str(self.root)]), 1)

    def test_missing_artifact_aborts(self) -> None:
        (self.root / "bin/tb-toplines-gen").unlink()
        failures = self.gate.verify(self.root)
        self.assertTrue(any(f.startswith("MISSING") for f in failures))
        self.assertEqual(self.gate.main(["--root", str(self.root)]), 1)


if __name__ == "__main__":
    unittest.main()
