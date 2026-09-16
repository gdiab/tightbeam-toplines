from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "tb-toplines-gen"


class RunningTurnCountTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="toplines-gen-")
        self.directory = Path(self.temporary.name)
        self.db_path = self.directory / "state.db"
        self.output_path = self.directory / "toplines.json"
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(
                """
                CREATE TABLE work_items (
                  id TEXT PRIMARY KEY, title TEXT NOT NULL, state TEXT NOT NULL,
                  failReason TEXT, createdAt INTEGER NOT NULL
                );
                CREATE TABLE assignments (
                  id TEXT PRIMARY KEY, holderKey TEXT NOT NULL, openedAt INTEGER NOT NULL,
                  state TEXT NOT NULL, outcome TEXT, workItemId TEXT,
                  reviewsAssignmentId TEXT
                );
                CREATE TABLE attests (
                  id TEXT PRIMARY KEY, assignmentId TEXT NOT NULL, kind TEXT NOT NULL,
                  verdictKind TEXT, ts INTEGER NOT NULL
                );
                CREATE TABLE turns (
                  seq INTEGER PRIMARY KEY, sessionKey TEXT NOT NULL, assignmentId TEXT,
                  jobRef TEXT, status TEXT NOT NULL, startedAt INTEGER, endedAt INTEGER
                );
                CREATE TABLE wakes (
                  wakeId TEXT PRIMARY KEY, sessionKey TEXT NOT NULL, origin TEXT NOT NULL,
                  prompt TEXT, consumer TEXT NOT NULL, dueAt INTEGER NOT NULL,
                  assignmentId TEXT, state TEXT NOT NULL
                );
                CREATE TABLE sessions (
                  sessionKey TEXT PRIMARY KEY, displayName TEXT, spawnedBy TEXT,
                  harness TEXT, model TEXT, state TEXT NOT NULL, createdAt INTEGER NOT NULL
                );
                CREATE TABLE decision_requests (
                  id TEXT PRIMARY KEY, raiserId TEXT NOT NULL, assignmentId TEXT,
                  question TEXT NOT NULL, raisedAt INTEGER NOT NULL, deadlineAt INTEGER,
                  kind TEXT NOT NULL, status TEXT NOT NULL
                );
                CREATE TABLE causal_events_epoch (id INTEGER PRIMARY KEY, at INTEGER NOT NULL);
                CREATE TABLE causal_events (
                  seq INTEGER PRIMARY KEY, jobRef TEXT, at INTEGER NOT NULL, kind TEXT NOT NULL
                );

                INSERT INTO work_items VALUES ('wi_test', 'Test item', 'open', NULL, 100);
                INSERT INTO sessions VALUES (
                  'agent:test s_test', 'Coder - test', 'agent:main s_main',
                  'codex', 'test-model', 'active', 100
                );
                INSERT INTO assignments VALUES (
                  'asg_test', 'agent:test s_test', 100, 'open', NULL, 'wi_test', NULL
                );
                INSERT INTO causal_events_epoch VALUES (0, 0);
                """
            )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def insert_turn(
        self,
        seq: int,
        status: str,
        *,
        assignment_id: str | None = None,
        job_ref: str | None = None,
        ended_at: int | None = None,
    ) -> None:
        started_at = None if status == "queued" else 200 + seq
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "INSERT INTO turns VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    seq,
                    "agent:test s_test",
                    assignment_id,
                    job_ref,
                    status,
                    started_at,
                    ended_at,
                ),
            )

    def generate(self) -> dict[str, object]:
        environment = os.environ.copy()
        environment.update(
            {
                "TB_TOPLINES_DB": str(self.db_path),
                "TB_TOPLINES_OUT": str(self.output_path),
                "TB_TOPLINES_PARITY": str(self.directory / "missing-parity.json"),
            }
        )
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            text=True,
            env=environment,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(self.output_path.read_text(encoding="utf-8"))

    def test_zero_running_turns(self) -> None:
        self.assertEqual(self.generate()["org"]["runningTurns"], 0)

    def test_unattributed_running_turn_is_counted(self) -> None:
        self.insert_turn(1, "running")
        snapshot = self.generate()
        self.assertEqual(snapshot["org"]["runningTurns"], 1)
        self.assertFalse(snapshot["items"][0]["active"]["runningTurn"])

    def test_two_running_turns_on_one_item_are_both_counted(self) -> None:
        self.insert_turn(1, "running", assignment_id="asg_test")
        self.insert_turn(2, "running", job_ref="wi_test")
        snapshot = self.generate()
        self.assertEqual(snapshot["org"]["runningTurns"], 2)
        self.assertTrue(snapshot["items"][0]["active"]["runningTurn"])

    def test_queued_and_delivered_turns_are_excluded(self) -> None:
        self.insert_turn(1, "queued", assignment_id="asg_test")
        self.insert_turn(2, "delivered", assignment_id="asg_test", ended_at=300)
        self.assertEqual(self.generate()["org"]["runningTurns"], 0)


if __name__ == "__main__":
    unittest.main()
