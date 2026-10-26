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
                CREATE TABLE assignment_cannot_proceed (
                  id TEXT PRIMARY KEY, assignmentId TEXT NOT NULL, attestId TEXT,
                  decisionRequestId TEXT, decisionWakeId TEXT, openerRef TEXT,
                  disposerRef TEXT, reason TEXT, releaseFactKind TEXT,
                  releaseFactScope TEXT, releaseFactPrincipalRef TEXT,
                  state TEXT NOT NULL, createdAt INTEGER NOT NULL, settledAt INTEGER,
                  settlementKind TEXT, settlementFactId TEXT, settledBy TEXT
                );
                CREATE TABLE condition_facts (
                  id TEXT PRIMARY KEY, kind TEXT NOT NULL, scope TEXT NOT NULL,
                  ts INTEGER NOT NULL, ownerUserId TEXT, payload TEXT
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

    def generate(self, **extra_environment: str) -> dict[str, object]:
        environment = os.environ.copy()
        environment.update(
            {
                "TB_TOPLINES_DB": str(self.db_path),
                "TB_TOPLINES_OUT": str(self.output_path),
                "TB_TOPLINES_PARITY": str(self.directory / "missing-parity.json"),
            }
        )
        environment.update(extra_environment)
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

    def test_non_george_install_config_is_emitted(self) -> None:
        snapshot = self.generate(
            TB_TOPLINES_OPERATOR="maya",
            TB_TOPLINES_ATC_URL="https://example.ts.net/atc",
            TB_TOPLINES_TZ="Europe/Berlin",
        )
        self.assertEqual(
            snapshot["config"],
            {
                "operator": "maya",
                "atcUrl": "https://example.ts.net/atc",
                "tz": "Europe/Berlin",
            },
        )

    def test_confirmed_action_requires_exact_user_principal_and_drops_on_fact(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(
                """
                INSERT INTO work_items VALUES ('wi_confirm', 'Confirm me', 'open', NULL, 101);
                INSERT INTO assignments VALUES (
                  'asg_confirm', 'agent:test s_test', 101, 'open', NULL,
                  'wi_confirm', NULL
                );
                INSERT INTO assignment_cannot_proceed (
                  id, assignmentId, attestId, reason, releaseFactKind,
                  releaseFactScope, releaseFactPrincipalRef, state, createdAt
                ) VALUES (
                  'cp_confirm', 'asg_confirm', 'att_confirm',
                  'Upload the signed release receipt', 'release.receipt',
                  'wi_confirm', 'user:george', 'open', 500
                );
                INSERT INTO assignment_cannot_proceed (
                  id, assignmentId, attestId, reason, releaseFactKind,
                  releaseFactScope, releaseFactPrincipalRef, state, createdAt
                ) VALUES (
                  'cp_session', 'asg_test', 'att_session',
                  'Agent owned', 'agent.ready', 'wi_test',
                  'agent:main:clawline:george:main s_test', 'open', 501
                );
                """
            )

        org = self.generate(TB_TOPLINES_OPERATOR="george")["org"]
        self.assertEqual(org["blockedOnYouCount"], 1)
        self.assertEqual(org["blockedOnYou"][0]["source"], "cp_confirm")
        self.assertEqual(org["recordedBlockers"], [])

        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                "INSERT INTO condition_facts VALUES (?, ?, ?, ?, ?, ?)",
                ("fact_release", "release.receipt", "wi_confirm", 600, "george", "{}"),
            )
        org = self.generate(TB_TOPLINES_OPERATOR="george")["org"]
        self.assertEqual(org["blockedOnYouCount"], 0)

    def test_settled_block_is_secondary_historical_and_newest_wins(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.executescript(
                """
                INSERT INTO assignment_cannot_proceed (
                  id, assignmentId, attestId, reason, state, createdAt,
                  settledAt, settlementKind
                ) VALUES (
                  'cp_old', 'asg_test', 'att_old', 'Old source',
                  'settled', 300, 350, 'disposed'
                );
                INSERT INTO assignment_cannot_proceed (
                  id, assignmentId, attestId, reason, state, createdAt,
                  settledAt, settlementKind
                ) VALUES (
                  'cp_new', 'asg_test', 'att_new',
                  '<button>Do this now</button> source text that remains historical',
                  'settled', 400, 450, 'disposed'
                );
                """
            )
        org = self.generate(TB_TOPLINES_OPERATOR="george")["org"]
        self.assertEqual(org["blockedOnYouCount"], 0)
        self.assertEqual(len(org["recordedBlockers"]), 1)
        blocker = org["recordedBlockers"][0]
        self.assertEqual(blocker["source"], "cp_new")
        self.assertEqual(blocker["status"], "unknown")
        self.assertIn("<button>", blocker["summary"])
        self.assertEqual(
            org["recordedBlockersCoverage"],
            {
                "total": 1,
                "shown": 1,
                "omitted": 0,
                "selection": (
                    "latest per work item, most-recent first, cap 20; "
                    "not an exhaustive human-dependency inventory"
                ),
            },
        )

    def test_parity_overdue_is_recomputed_from_last_success(self) -> None:
        parity_path = self.directory / "parity.json"
        parity_path.write_text(
            json.dumps(
                {
                    "ranAt": 1,
                    "outcome": "ok",
                }
            ),
            encoding="utf-8",
        )
        parity = self.generate(TB_TOPLINES_PARITY=str(parity_path))["parity"]
        self.assertEqual(parity["lastAttemptAt"], 1)
        self.assertEqual(parity["lastSuccessAt"], 1)
        self.assertTrue(parity["overdue"])

    def test_historical_resolution_and_visible_cap(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            for index in range(22):
                item_id = f"wi_hist_{index:02d}"
                assignment_id = f"asg_hist_{index:02d}"
                connection.execute(
                    "INSERT INTO work_items VALUES (?, ?, 'open', NULL, ?)",
                    (item_id, f"Historical {index}", 1_000 + index),
                )
                connection.execute(
                    "INSERT INTO assignments VALUES (?, ?, ?, 'open', NULL, ?, NULL)",
                    (assignment_id, "agent:test s_test", 1_000 + index, item_id),
                )
                connection.execute(
                    """INSERT INTO assignment_cannot_proceed (
                         id, assignmentId, attestId, reason, state, createdAt,
                         settledAt, settlementKind
                       ) VALUES (?, ?, ?, ?, 'settled', ?, ?, 'disposed')""",
                    (
                        f"cp_hist_{index:02d}", assignment_id, f"att_hist_{index:02d}",
                        f"Historical source {index}", 2_000 + index, 3_000 + index,
                    ),
                )
            connection.execute(
                """UPDATE assignment_cannot_proceed
                   SET releaseFactKind='resolved.kind', releaseFactScope='wi_hist_21'
                   WHERE id='cp_hist_21'"""
            )
            connection.execute(
                "INSERT INTO condition_facts VALUES (?, ?, ?, ?, ?, ?)",
                ("fact_hist", "resolved.kind", "wi_hist_21", 4_000, "george", "{}"),
            )

        coverage = self.generate(TB_TOPLINES_OPERATOR="george")["org"][
            "recordedBlockersCoverage"
        ]
        self.assertEqual(coverage["total"], 21)
        self.assertEqual(coverage["shown"], 20)
        self.assertEqual(coverage["omitted"], 1)


if __name__ == "__main__":
    unittest.main()
