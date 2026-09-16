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

    def test_env_redirect_bypass_is_closed(self) -> None:
        # Reproduces R1 F1 and proves it is closed. The OLD bypass: point
        # TB_TOPLINES_ROOT at a clean tree while an altered source is what gets
        # installed; the gate returned OK and the altered artifact shipped.
        # Now: (a) the env var is ignored (root is fixed unless --root is given),
        # and (b) the runbook verifies the SOURCE tree it copies from
        # (--root=<source>), so an altered source aborts non-zero -> the &&-chain
        # never copies.
        import os

        good = self.root  # setUp wrote files whose hashes are self.gate.PINS
        bad = Path(self.temporary.name) / "bad"
        for relpath in self.gate.PINS:
            src = good / relpath
            if src.is_file():
                dst = bad / relpath
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(src.read_bytes())
        altered = next(iter(self.gate.PINS))
        (bad / altered).write_bytes(b"TAMPERED SOURCE\n")

        prior = os.environ.get("TB_TOPLINES_ROOT")
        os.environ["TB_TOPLINES_ROOT"] = str(good)  # the old bypass lever
        try:
            reloaded = load_gate()
            reloaded.PINS = dict(self.gate.PINS)
            # (a) env cannot redirect the default root.
            self.assertEqual(reloaded.ROOT_DEFAULT, Path.home() / "tb-toplines")
            # (b) verifying the source tree the runbook copies from aborts even
            #     though the env points at the clean 'good' tree.
            self.assertEqual(reloaded.main(["--root", str(bad)]), 1)
            # sanity: the clean tree still passes.
            self.assertEqual(reloaded.main(["--root", str(good)]), 0)
        finally:
            if prior is None:
                os.environ.pop("TB_TOPLINES_ROOT", None)
            else:
                os.environ["TB_TOPLINES_ROOT"] = prior


if __name__ == "__main__":
    unittest.main()
