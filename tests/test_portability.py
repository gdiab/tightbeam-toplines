from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "bin" / "tb-toplines-gen"
PARITY = ROOT / "bin" / "tb-toplines-parity"
WATCH = ROOT / "bin" / "tb-toplines-watch"
GATE = ROOT / "bin" / "tb-toplines-verify-install"
PAGE = ROOT / "web" / "index.html"
RUNBOOK = ROOT / "docs" / "runbook.md"


def load_script(path: Path, name: str):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


@contextmanager
def changed_environment(**changes: str | None):
    prior = {key: os.environ.get(key) for key in changes}
    try:
        for key, value in changes.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def write_minimal_ledger(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE work_items (
              id TEXT PRIMARY KEY, state TEXT NOT NULL, createdAt INTEGER NOT NULL
            );
            CREATE TABLE assignments (
              id TEXT PRIMARY KEY, workItemId TEXT, reviewsAssignmentId TEXT,
              openedAt INTEGER, closedAt INTEGER
            );
            CREATE TABLE attests (
              id TEXT PRIMARY KEY, assignmentId TEXT, ts INTEGER NOT NULL
            );
            CREATE TABLE turns (
              seq INTEGER PRIMARY KEY, assignmentId TEXT, jobRef TEXT, endedAt INTEGER
            );
            CREATE TABLE causal_events (
              seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, jobRef TEXT, at INTEGER NOT NULL
            );
            """
        )


class ConfigurationResolutionTest(unittest.TestCase):
    def test_a3_all_readers_resolve_the_same_base_and_override(self) -> None:
        with tempfile.TemporaryDirectory(prefix="toplines-resolve-") as name:
            home = Path(name) / "home"
            base = Path(name) / "instance"
            override = Path(name) / "other" / "state.db"
            home.mkdir()
            base.mkdir()
            override.parent.mkdir()
            with changed_environment(
                HOME=str(home), TB_BASE_DIR=str(base), TB_TOPLINES_DB=None
            ):
                gen = load_script(GEN, f"toplines_gen_{time.time_ns()}")
                parity = load_script(PARITY, f"toplines_parity_{time.time_ns()}")
                self.assertEqual(gen.resolve_ledger(), (base / "state.db").resolve())
                self.assertEqual(parity.resolve_ledger(), (base / "state.db").resolve())
            with changed_environment(
                HOME=str(home),
                TB_BASE_DIR=str(base),
                TB_TOPLINES_DB=str(override),
            ):
                gen = load_script(GEN, f"toplines_gen_{time.time_ns()}")
                parity = load_script(PARITY, f"toplines_parity_{time.time_ns()}")
                self.assertEqual(gen.resolve_ledger(), override.resolve())
                self.assertEqual(parity.resolve_ledger(), override.resolve())

    def test_a3_watcher_uses_base_dir_ledger_read_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="toplines-watch-") as name:
            directory = Path(name)
            base = directory / "instance"
            base.mkdir()
            write_minimal_ledger(base / "state.db")
            generator = directory / "generator"
            generator.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            generator.chmod(0o755)
            environment = os.environ.copy()
            environment.update(
                {
                    "TB_BASE_DIR": str(base),
                    "TB_TOPLINES_GEN": str(generator),
                    "TB_TOPLINES_BEAT": "3600",
                }
            )
            environment.pop("TB_TOPLINES_DB", None)
            process = subprocess.Popen(
                [str(WATCH)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=environment,
            )
            try:
                deadline = time.time() + 5
                stderr = ""
                while "ledger_uri=" not in stderr and time.time() < deadline:
                    assert process.stderr is not None
                    stderr += process.stderr.readline()
                self.assertIn(f"file:{base.resolve()}/state.db?mode=ro", stderr)
            finally:
                process.terminate()
                process.wait(timeout=5)
                if process.stdout is not None:
                    process.stdout.close()
                if process.stderr is not None:
                    process.stderr.close()

    def test_a4_non_gd_home_controls_default_install_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="toplines-home-") as name:
            environment = os.environ.copy()
            environment["HOME"] = name
            output = subprocess.check_output(
                [
                    sys.executable,
                    "-c",
                    (
                        "import runpy; "
                        f"m=runpy.run_path({str(GATE)!r}, run_name='gate_test'); "
                        "print(m['ROOT_DEFAULT'])"
                    ),
                ],
                text=True,
                env=environment,
            ).strip()
            self.assertEqual(output, str(Path(name) / "tb-toplines"))

    def test_a4_explicit_install_root_uses_unpinned_service_dropins(self) -> None:
        gate = load_script(GATE, f"toplines_gate_{time.time_ns()}")
        services = {
            "tb-toplines.service": "tb-toplines-serve",
            "tb-toplines-watch.service": "tb-toplines-watch",
            "tb-toplines-parity.service": "tb-toplines-parity",
        }
        with tempfile.TemporaryDirectory(prefix="toplines-root-") as name:
            scratch = Path(name)
            home = scratch / "non-gd-home"
            install_root = scratch / "srv-toplines"
            user_units = home / ".config" / "systemd" / "user"
            for relative in gate.PINS:
                source = ROOT / relative
                target = install_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
            shutil.copy2(GATE, install_root / "bin" / GATE.name)

            result = subprocess.run(
                [str(install_root / "bin" / GATE.name), "--root", str(install_root)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("all 10 deployed artifacts match", result.stdout)

            for unit, executable in services.items():
                dropin = user_units / f"{unit}.d" / "root.conf"
                dropin.parent.mkdir(parents=True, exist_ok=True)
                dropin.write_text(
                    "[Service]\n"
                    f"WorkingDirectory={install_root}\n"
                    "ExecStart=\n"
                    f"ExecStart={install_root}/bin/{executable}\n",
                    encoding="utf-8",
                )
                lines = dropin.read_text(encoding="utf-8").splitlines()
                self.assertEqual(lines[1], f"WorkingDirectory={install_root}")
                self.assertEqual(lines[2], "ExecStart=")
                self.assertEqual(lines[3], f"ExecStart={install_root}/bin/{executable}")

            self.assertFalse((home / "tb-toplines").exists())
            self.assertEqual(gate.verify(install_root), [])
            for relative, pinned in gate.PINS.items():
                self.assertEqual(gate.sha256_of(ROOT / relative), pinned)


class LiveParitySelectionTest(unittest.TestCase):
    def make_fixture(self, directory: Path, gateway: bool = True) -> dict[str, Path]:
        app_bin = directory / "app" / "bin"
        fake_bin = directory / "fake-bin"
        base = directory / "instance"
        ambient = directory / "ambient"
        for path in (app_bin, fake_bin, base, ambient):
            path.mkdir(parents=True)
        shutil.copy2(PARITY, app_bin / PARITY.name)
        write_minimal_ledger(base / "state.db")
        if gateway:
            (base / "gateway.json").write_text("{}\n", encoding="utf-8")
        (ambient / ".tightbeam-session").write_text("wrong instance\n", encoding="utf-8")

        cli_json = directory / "cli.json"
        top_json = directory / "toplines.json"
        generated_json = directory / "generated.json"
        parity_json = directory / "parity.json"
        atc_json = directory / "atc.json"
        cli_log = directory / "cli.log"
        cli_json.write_text(
            json.dumps(
                {
                    "coverage": {"basis": "conservative_shared"},
                    "edgeBasis": "concurrent_turn",
                    "items": [],
                }
            ),
            encoding="utf-8",
        )
        generated_json.write_text(
            json.dumps({"generatedAt": time.time_ns() // 1_000_000, "items": []}),
            encoding="utf-8",
        )
        atc_json.write_text(json.dumps({"items": []}), encoding="utf-8")
        fake_cli = fake_bin / "tightbeam"
        fake_cli.write_text(
            "#!/bin/sh\n"
            "printf '%s|%s|%s|%s|%s\\n' \"$PWD\" \"$TIGHTBEAM_BASE_DIR\" "
            '"${TIGHTBEAM_URL-unset}" "${TIGHTBEAM_TOKEN-unset}" "$*" >> "$TEST_CLI_LOG"\n'
            'cat "$TEST_CLI_JSON"\n',
            encoding="utf-8",
        )
        fake_cli.chmod(0o755)
        generator = app_bin / "tb-toplines-gen"
        generator.write_text(
            "#!/bin/sh\ncp \"$TEST_TOP_JSON\" \"$TB_TOPLINES_OUT\"\n",
            encoding="utf-8",
        )
        generator.chmod(0o755)
        return {
            "script": app_bin / PARITY.name,
            "fake_bin": fake_bin,
            "base": base,
            "ambient": ambient,
            "cli_json": cli_json,
            "top_json": top_json,
            "generated_json": generated_json,
            "parity_json": parity_json,
            "atc_json": atc_json,
            "cli_log": cli_log,
        }

    def run_fixture(
        self, fixture: dict[str, Path], operator: str | None
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "PATH": f"{fixture['fake_bin']}:/usr/bin:/bin",
                "XDG_STATE_HOME": str(fixture["ambient"] / "state"),
                "TB_BASE_DIR": str(fixture["base"]),
                "TB_TOPLINES_OUT": str(fixture["top_json"]),
                "TB_TOPLINES_PARITY": str(fixture["parity_json"]),
                "TB_TOPLINES_ATC_DATA": str(fixture["atc_json"]),
                "TB_TOPLINES_TZ": "UTC",
                "TIGHTBEAM_URL": "https://wrong.invalid",
                "TIGHTBEAM_TOKEN": "wrong-token",
                "TEST_CLI_LOG": str(fixture["cli_log"]),
                "TEST_CLI_JSON": str(fixture["cli_json"]),
                "TEST_TOP_JSON": str(fixture["generated_json"]),
            }
        )
        environment.pop("TB_TOPLINES_DB", None)
        if operator is None:
            environment.pop("TB_TOPLINES_OPERATOR", None)
        else:
            environment["TB_TOPLINES_OPERATOR"] = operator
        return subprocess.run(
            [sys.executable, str(fixture["script"])],
            cwd=fixture["ambient"],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_a1_missing_operator_makes_no_cli_call(self) -> None:
        with tempfile.TemporaryDirectory(prefix="toplines-operator-") as name:
            fixture = self.make_fixture(Path(name))
            result = self.run_fixture(fixture, None)
            self.assertEqual(result.returncode, 2)
            self.assertIn("TB_TOPLINES_OPERATOR is unset", result.stderr)
            self.assertFalse(fixture["cli_log"].exists())
            self.assertFalse((fixture["ambient"] / "state" / "tb-toplines").exists())

    def test_a3_missing_sibling_gateway_makes_no_cli_call(self) -> None:
        with tempfile.TemporaryDirectory(prefix="toplines-gateway-") as name:
            fixture = self.make_fixture(Path(name), gateway=False)
            result = self.run_fixture(fixture, "maya")
            self.assertEqual(result.returncode, 2)
            self.assertIn("no readable gateway.json under the ledger base", result.stderr)
            self.assertFalse(fixture["cli_log"].exists())
            self.assertFalse((fixture["ambient"] / "state" / "tb-toplines").exists())

    def test_a3_ambient_session_and_url_cannot_override_ledger_instance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="toplines-authority-") as name:
            fixture = self.make_fixture(Path(name))
            result = self.run_fixture(fixture, "maya")
            self.assertEqual(result.returncode, 0, result.stderr)
            fields = fixture["cli_log"].read_text(encoding="utf-8").strip().split("|")
            self.assertNotEqual(Path(fields[0]), fixture["ambient"])
            self.assertEqual(fields[1], str(fixture["base"].resolve()))
            self.assertEqual(fields[2:4], ["unset", "unset"])
            self.assertEqual(fields[4], "toplines --as-user maya")


class TimezoneAndEvidenceTest(unittest.TestCase):
    def test_a5_install_timezone_controls_day_boundary(self) -> None:
        parity = load_script(PARITY, f"toplines_parity_{time.time_ns()}")
        instant = int(
            datetime(2026, 1, 1, 23, 30, tzinfo=timezone.utc).timestamp() * 1_000
        )
        with tempfile.TemporaryDirectory(prefix="toplines-days-") as name:
            parity.ATTEMPT_DIR = Path(name)
            parity.TIMEZONE_NAME = "Europe/Berlin"
            berlin = parity.daily_attempt_path(instant)
            parity.TIMEZONE_NAME = "America/Los_Angeles"
            pacific = parity.daily_attempt_path(instant)
            self.assertEqual(berlin.name, "parity-attempt-2026-01-02")
            self.assertEqual(pacific.name, "parity-attempt-2026-01-01")

    def test_a5_invalid_timezone_is_a_named_hard_error(self) -> None:
        parity = load_script(PARITY, f"toplines_parity_{time.time_ns()}")
        parity.TIMEZONE_NAME = "Not/A-Timezone"
        with self.assertRaisesRegex(
            RuntimeError, "TB_TOPLINES_TZ is not a valid IANA timezone"
        ):
            parity.daily_attempt_path(0)

    def test_a6_missing_atc_is_truthful_degraded_success(self) -> None:
        with tempfile.TemporaryDirectory(prefix="toplines-atc-") as name:
            directory = Path(name)
            cli = directory / "cli.json"
            top = directory / "toplines.json"
            output = directory / "parity.json"
            cli.write_text(
                json.dumps(
                    {
                        "coverage": {"basis": "conservative_shared"},
                        "edgeBasis": "concurrent_turn",
                        "items": [],
                    }
                ),
                encoding="utf-8",
            )
            top.write_text(json.dumps({"items": []}), encoding="utf-8")
            environment = os.environ.copy()
            environment.update(
                {
                    "TB_TOPLINES_CLI_JSON": str(cli),
                    "TB_TOPLINES_OUT": str(top),
                    "TB_TOPLINES_PARITY": str(output),
                    "TB_TOPLINES_ATC_DATA": str(directory / "missing-atc.json"),
                    "TB_TOPLINES_ATC_URL": "https://example.ts.net/atc",
                }
            )
            result = subprocess.run(
                [sys.executable, str(PARITY)],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            value = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(value["outcome"], "ok-ledger-atc-missing")
            self.assertEqual(value["atcEvidence"], "missing")
            self.assertIn("missing-atc.json", value["atcEvidenceReason"])


class InstalledSurfaceTest(unittest.TestCase):
    def test_a1_a2_page_is_neutral_and_config_driven(self) -> None:
        source = PAGE.read_text(encoding="utf-8")
        self.assertNotIn("george", source.lower())
        self.assertIn('id="operator">--as-user &lt;operator&gt;', source)
        self.assertIn('id="atc" hidden', source)
        self.assertIn("atc.href=target.href", source)
        self.assertIn("ATC stage evidence unavailable", source)

    def test_a2_generator_accepts_only_http_atc_urls(self) -> None:
        with changed_environment(TB_TOPLINES_ATC_URL="https://example.ts.net/atc"):
            gen = load_script(GEN, f"toplines_gen_{time.time_ns()}")
            self.assertEqual(gen.configured_atc_url(), "https://example.ts.net/atc")
        for unsafe in ("javascript:alert(1)", "data:text/html,x", '"><script>'):
            with self.subTest(unsafe=unsafe), changed_environment(
                TB_TOPLINES_ATC_URL=unsafe
            ):
                gen = load_script(GEN, f"toplines_gen_{time.time_ns()}")
                self.assertIsNone(gen.configured_atc_url())
        with changed_environment(TB_TOPLINES_ATC_URL="http://localhost:8080/atc"):
            gen = load_script(GEN, f"toplines_gen_{time.time_ns()}")
            self.assertEqual(
                gen.configured_atc_url(), "http://localhost:8080/atc"
            )
        with changed_environment(TB_TOPLINES_ATC_URL=None):
            gen = load_script(GEN, f"toplines_gen_{time.time_ns()}")
            self.assertIsNone(gen.configured_atc_url())

    def test_a4_services_use_home_specifier_and_environment_file(self) -> None:
        services = {
            path.name: path.read_text(encoding="utf-8")
            for path in (ROOT / "systemd").glob("*")
        }
        self.assertNotIn("/home/gd", "\n".join(services.values()))
        self.assertIn("WorkingDirectory=%h/tb-toplines", services["tb-toplines.service"])
        self.assertIn("ExecStart=%h/tb-toplines/bin/tb-toplines-watch", services["tb-toplines-watch.service"])
        self.assertIn("EnvironmentFile=-%h/.config/tb-toplines/toplines.env", services["tb-toplines-watch.service"])
        self.assertIn("%h/.tightbeam/bin", services["tb-toplines-parity.service"])

    def test_a5_runbook_installs_timezone_dropin_that_clears_base_schedule(self) -> None:
        runbook = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("OnCalendar=\nOnCalendar=*-*-* 03:00:00 $TB_TOPLINES_TZ", runbook)
        timer = (ROOT / "systemd" / "tb-toplines-parity.timer").read_text(
            encoding="utf-8"
        )
        self.assertIn("OnCalendar=*-*-* 03:00:00 UTC", timer)

    def test_a7_fresh_install_and_sirius_migration_are_separate(self) -> None:
        runbook = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("https://github.com/gdiab/tightbeam-toplines.git", runbook)
        self.assertIn("exact merged `main` commit", runbook)
        self.assertIn("pre-merge rehearsal only", runbook)
        self.assertIn("cannot satisfy final A7 acceptance", runbook)
        self.assertIn("## Fresh install", runbook)
        self.assertIn("## Sirius migration", runbook)
        gate = load_script(GATE, f"toplines_gate_{time.time_ns()}")
        self.assertEqual(gate.verify(ROOT), [])

    def test_a8_a9_runbook_requires_exact_review_and_delivery_evidence(self) -> None:
        runbook = RUNBOOK.read_text(encoding="utf-8")
        self.assertIn("exact candidate commit", runbook)
        self.assertIn("independent reviewed-clean verdict", runbook)
        self.assertIn("Notify George through Main", runbook)
        self.assertIn("effective configuration", runbook)

    def test_a_bound_atc_is_only_a_read_only_input_and_link(self) -> None:
        parity = PARITY.read_text(encoding="utf-8")
        generator = GEN.read_text(encoding="utf-8")
        page = PAGE.read_text(encoding="utf-8")
        combined = parity + generator + page
        self.assertNotIn("ATC_PATH.write", combined)
        self.assertNotIn("open(ATC_PATH, \"w", combined)
        self.assertNotIn("subprocess.run([\"docker\"", combined)
        self.assertNotIn("subprocess.run([\"tailscale\"", combined)


if __name__ == "__main__":
    unittest.main()
