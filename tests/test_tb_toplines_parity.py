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
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "tb-toplines-parity"


def load_parity():
    loader = importlib.machinery.SourceFileLoader("tb_toplines_parity", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError("cannot create import spec")
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


class ConcurrencyCoverageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="toplines-concurrency-")
        self.db_path = Path(self.temporary.name) / "state.db"
        with sqlite3.connect(self.db_path) as connection:
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
                INSERT INTO work_items VALUES ('wi_test', 'open', 100);
                INSERT INTO assignments VALUES ('asg_direct', 'wi_test', NULL, 100, NULL);
                INSERT INTO assignments VALUES ('asg_review', NULL, 'asg_direct', 100, NULL);
                """
            )
        self.parity = load_parity()
        self.parity.DB_PATH = self.db_path

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def changed_input(self) -> str | None:
        return self.parity.changing_input(
            {"wi_test"},
            1_000,
            2_000,
            {"wi_test": "open"},
            {"wi_test": "open"},
        )

    def assert_inconclusive(self, changed: str | None) -> None:
        self.assertIsNotNone(changed)
        self.assertEqual(
            self.parity.classify_outcome(changed, "wi_test: quiet mismatch"),
            ("inconclusive", None),
        )

    def test_job_turn_end_is_inconclusive(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "INSERT INTO turns VALUES (?, ?, ?, ?)",
                (1, None, "wi_test", 1_500),
            )
        self.assert_inconclusive(self.changed_input())

    def test_resolved_assignment_turn_end_is_inconclusive(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "INSERT INTO turns VALUES (?, ?, ?, ?)",
                (1, "asg_review", None, 1_500),
            )
        self.assert_inconclusive(self.changed_input())

    def test_disposition_is_inconclusive(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "INSERT INTO causal_events VALUES (?, ?, ?, ?)",
                (1, "disposition_transition", "wi_test", 1_600),
            )
        self.assert_inconclusive(self.changed_input())


class DailyGuardTest(unittest.TestCase):
    def test_two_concurrent_production_starts_make_one_cli_call(self) -> None:
        with tempfile.TemporaryDirectory(prefix="toplines-daily-") as name:
            directory = Path(name)
            app = directory / "app"
            binary = app / "bin"
            fakebin = directory / "fakebin"
            state_home = directory / "state"
            binary.mkdir(parents=True)
            fakebin.mkdir()
            shutil.copy2(SCRIPT, binary / SCRIPT.name)

            cli_log = directory / "cli.log"
            generator_log = directory / "generator.log"
            cli_json = directory / "cli.json"
            generated_json = directory / "generated.json"
            output_json = directory / "toplines.json"
            parity_json = directory / "parity.json"
            atc_json = directory / "atc.json"
            db_path = directory / "state.db"
            (directory / "gateway.json").write_text("{}\n", encoding="utf-8")

            item = {
                "id": "wi_test",
                "state": "open",
                "sinceProgressMs": 10,
                "cards": {"open": 0, "closed": 0},
                "attests": {"total": 0},
                "stage": 0,
            }
            cli_json.write_text(
                json.dumps(
                    {
                        "coverage": {"basis": "conservative_shared"},
                        "edgeBasis": "concurrent_turn",
                        "items": [
                            {
                                "id": "wi_test",
                                "state": "open",
                                "sinceProgressMs": 10,
                                "assignments": {"open": 0, "closed": 0},
                                "attests": {"total": 0},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            generated_json.write_text(
                json.dumps({"generatedAt": 0, "items": [item]}), encoding="utf-8"
            )
            atc_json.write_text(
                json.dumps({"items": [{"id": "wi_test", "stage": 0}]}),
                encoding="utf-8",
            )
            with sqlite3.connect(db_path) as connection:
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
                    INSERT INTO work_items VALUES ('wi_test', 'open', 100);
                    """
                )

            fake_cli = fakebin / "tightbeam"
            fake_cli.write_text(
                "#!/bin/sh\n"
                'printf "call\\n" >> "$TEST_CLI_LOG"\n'
                "sleep 0.1\n"
                'cat "$TEST_CLI_JSON"\n',
                encoding="utf-8",
            )
            fake_generator = binary / "tb-toplines-gen"
            fake_generator.write_text(
                "#!/bin/sh\n"
                'printf "call\\n" >> "$TEST_GENERATOR_LOG"\n'
                'cp "$TEST_GENERATED_JSON" "$TB_TOPLINES_OUT"\n',
                encoding="utf-8",
            )
            fake_cli.chmod(0o755)
            fake_generator.chmod(0o755)

            environment = os.environ.copy()
            environment.update(
                {
                    "PATH": f"{fakebin}:/usr/bin:/bin",
                    "XDG_STATE_HOME": str(state_home),
                    "TB_TOPLINES_DB": str(db_path),
                    "TB_TOPLINES_OUT": str(output_json),
                    "TB_TOPLINES_PARITY": str(parity_json),
                    "TB_TOPLINES_ATC_DATA": str(atc_json),
                    "TB_TOPLINES_OPERATOR": "maya",
                    "TB_TOPLINES_TZ": "UTC",
                    "TEST_CLI_LOG": str(cli_log),
                    "TEST_CLI_JSON": str(cli_json),
                    "TEST_GENERATOR_LOG": str(generator_log),
                    "TEST_GENERATED_JSON": str(generated_json),
                }
            )

            command = [sys.executable, str(binary / SCRIPT.name)]
            first = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env=environment
            )
            second = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, env=environment
            )
            first_stdout, first_stderr = first.communicate()
            second_stdout, second_stderr = second.communicate()

            self.assertEqual(first.returncode, 0, first_stderr)
            self.assertEqual(second.returncode, 0, second_stderr)
            self.assertEqual(cli_log.read_text(encoding="utf-8"), "call\n")
            self.assertEqual(generator_log.read_text(encoding="utf-8"), "call\n")
            self.assertEqual(
                sum(
                    "already recorded" in output
                    for output in (first_stdout, second_stdout)
                ),
                1,
            )
            attempts = list((state_home / "tb-toplines").glob("parity-attempt-*"))
            self.assertEqual(len(attempts), 1)


class AttemptRecordingTest(unittest.TestCase):
    def test_legacy_success_is_preserved_as_last_success(self) -> None:
        with tempfile.TemporaryDirectory(prefix="toplines-legacy-") as name:
            path = Path(name) / "parity.json"
            path.write_text(
                json.dumps({"ranAt": 123, "outcome": "ok", "checked": 18}),
                encoding="utf-8",
            )
            parity = load_parity()
            parity.PARITY_PATH = path
            migrated = parity.previous_parity()
            self.assertEqual(migrated["lastAttemptAt"], 123)
            self.assertEqual(migrated["lastAttemptOutcome"], "ok")
            self.assertEqual(migrated["lastSuccessAt"], 123)
            self.assertEqual(migrated["lastSuccessOutcome"], "ok")

    def test_malformed_attempt_is_persisted_without_erasing_last_success(self) -> None:
        with tempfile.TemporaryDirectory(prefix="toplines-attempt-") as name:
            directory = Path(name)
            output = directory / "toplines.json"
            atc = directory / "atc.json"
            capture = directory / "execution-map.json"
            parity = directory / "parity.json"
            item = {
                "id": "wi_test",
                "state": "open",
                "sinceProgressMs": 10,
                "cards": {"open": 1, "closed": 0},
                "attests": {"total": 2},
                "stage": 3,
            }
            output.write_text(
                json.dumps({"generatedAt": 1, "items": [item]}), encoding="utf-8"
            )
            atc.write_text(
                json.dumps({"items": [{"id": "wi_test", "stage": 3}]}),
                encoding="utf-8",
            )
            capture.write_text(
                json.dumps(
                    {
                        "coverage": {"basis": "conservative_shared"},
                        "edgeBasis": "concurrent_turn",
                        "items": [
                            {
                                "id": "wi_test",
                                "state": "open",
                                "sinceProgressMs": 10,
                                "assignments": {"open": 1, "closed": 0},
                                "attests": {"total": 2},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment.update(
                {
                    "TB_TOPLINES_CLI_JSON": str(capture),
                    "TB_TOPLINES_OUT": str(output),
                    "TB_TOPLINES_PARITY": str(parity),
                    "TB_TOPLINES_ATC_DATA": str(atc),
                }
            )
            first = subprocess.run(
                [sys.executable, str(SCRIPT)], capture_output=True, text=True,
                env=environment, check=False,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            success = json.loads(parity.read_text(encoding="utf-8"))
            self.assertEqual(success["lastAttemptOutcome"], "ok")
            self.assertEqual(success["lastSuccessAt"], success["lastAttemptAt"])

            capture.write_text(json.dumps({"items": []}), encoding="utf-8")
            second = subprocess.run(
                [sys.executable, str(SCRIPT)], capture_output=True, text=True,
                env=environment, check=False,
            )
            self.assertEqual(second.returncode, 2)
            failed = json.loads(parity.read_text(encoding="utf-8"))
            self.assertEqual(failed["lastAttemptOutcome"], "failed")
            self.assertIn("CLI coverage must be a JSON object", failed["failureReason"])
            self.assertEqual(failed["lastSuccessAt"], success["lastSuccessAt"])
            self.assertEqual(failed["ranAt"], success["ranAt"])
            self.assertEqual(failed["outcome"], "ok")


if __name__ == "__main__":
    unittest.main()
