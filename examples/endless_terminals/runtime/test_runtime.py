"""Local contract tests that never contact an external endpoint."""

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from . import runner
from .contract import extract_action
from .models import EndpointModel, FixtureModel


class RuntimeTests(unittest.TestCase):
    """Exercise observable parser, failure, and grading boundaries."""

    def test_pinned_action_precedence(self) -> None:
        """Keep the pinned parser's last-command and done precedence."""
        self.assertEqual(
            extract_action("<command>first</command><command>last</command>")[
                "command"
            ],
            "last",
        )
        for response in (
            "<command>false</command><action>done</action>",
            "<command>DONE</command>",
        ):
            self.assertEqual(extract_action(response)["type"], "done")
        self.assertEqual(extract_action("hello")["type"], "invalid")

    def test_endpoint_rejects_credential_leaks(self) -> None:
        """Reject embedded credentials and remote plaintext transport."""
        for url in (
            "http://example.com/v1",
            "https://user:secret@example.com/v1",
            "https://example.com/v1?key=secret",
        ):
            with self.assertRaises(ValueError):
                EndpointModel(url, "fixture")

    def test_endpoint_deadline_has_no_retry(self) -> None:
        """An expired child deadline causes exactly one failed attempt."""
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired("worker", 1),
        ) as request:
            with self.assertRaises(TimeoutError):
                EndpointModel("http://127.0.0.1/v1", "fixture").complete([], 1)
            request.assert_called_once()

    def test_episode_failure_and_turn_limits(self) -> None:
        """Keep model failures separate from rewards and consume invalid turns."""
        for responses, expected, grading_error in (
            ([], "infrastructure_error", None),
            (["invalid", "invalid"], "max_actions", None),
            (
                ["<action>done</action>"],
                "infrastructure_error",
                "grader failed",
            ),
        ):
            with (
                self.subTest(responses=responses),
                tempfile.TemporaryDirectory() as root,
            ):
                directory = Path(root)
                (directory / "tests").mkdir()
                (directory / "instruction.md").write_text(
                    "Create an output file."
                )
                (directory / "tests/test_final_state.py").write_text(
                    "hidden grader"
                )
                task = {
                    "task_id": "fixture",
                    "local_image_id": "sha256:" + "a" * 64,
                    "task_file_sha256": {
                        name: hashlib.sha256(
                            (directory / name).read_bytes()
                        ).hexdigest()
                        for name in (
                            "instruction.md",
                            "tests/test_final_state.py",
                        )
                    },
                }
                env = MagicMock()
                env.__enter__.return_value = env
                env.container_id = "fixture-container"
                env.provenance = {"backend": "fixture"}
                env.closed = True
                env.stopped = False
                grading = {
                    "raw_reward": None if grading_error else 0,
                    "audited_valid": False,
                    "infrastructure_error": grading_error,
                }
                with (
                    patch.object(
                        runner, "DockerEnvironment", return_value=env
                    ),
                    patch.object(
                        runner, "grade_environment", return_value=grading
                    ) as grade,
                ):
                    result = runner.run_episode(
                        task,
                        directory,
                        FixtureModel(responses),
                        directory / "episode",
                        identity={"kind": "fixture"},
                        max_actions=2,
                    )
                self.assertEqual(result["exit_reason"], expected)
                self.assertTrue(result["cleanup_complete"])
                self.assertNotIn(
                    "hidden grader", json.dumps(result["transcript"])
                )
                env.execute.assert_not_called()
                env.__exit__.assert_called_once()
                if not responses:
                    grade.assert_not_called()
                    self.assertIsNone(result["grading"])
                saved = json.loads(
                    (directory / "episode/result.json").read_text()
                )
                self.assertEqual(saved, result)

    def test_supplied_prompt_reaches_model_and_artifact(self) -> None:
        """Record the hash of the exact system message delivered to the model."""
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            (directory / "instruction.md").write_text("Do the task.")
            model = MagicMock()
            model.complete.return_value = ("<action>done</action>", {})
            env = MagicMock()
            env.container_id = "fixture"
            env.provenance = {"backend": "fixture"}
            env.closed = True
            message = "Exact custom prompt.\n"
            with (
                patch.object(runner, "verify_task_files"),
                patch.object(runner, "DockerEnvironment", return_value=env),
                patch.object(runner, "grade_environment", return_value={}),
            ):
                result = runner.run_episode(
                    {"task_id": "fixture", "local_image_id": "image"},
                    directory,
                    model,
                    directory / "episode",
                    identity={},
                    system_message=message,
                )
            self.assertEqual(
                model.complete.call_args.args[0][0],
                {"role": "system", "content": message},
            )
            self.assertEqual(
                result["system_prompt_sha256"],
                hashlib.sha256(message.encode()).hexdigest(),
            )
            saved = json.loads((directory / "episode/result.json").read_text())
            self.assertEqual(
                saved["system_prompt_sha256"], result["system_prompt_sha256"]
            )

    def test_blank_prompt_rejected_before_sandbox(self) -> None:
        """Reject empty instructions before creating output or a sandbox."""
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / "episode"
            with (
                patch.object(runner, "DockerEnvironment") as sandbox,
                self.assertRaisesRegex(ValueError, "system_message"),
            ):
                runner.run_episode(
                    {},
                    Path(root),
                    FixtureModel([]),
                    output,
                    identity={},
                    system_message=" \n",
                )
            sandbox.assert_not_called()
            self.assertFalse(output.exists())

    def test_task_hash_validation_precedes_execution(self) -> None:
        """Reject changed task evidence before creating a Docker environment."""
        with tempfile.TemporaryDirectory() as root:
            task = {"task_file_sha256": {"instruction.md": "bad"}}
            with self.assertRaises(ValueError):
                runner.verify_task_files(task, Path(root))


if __name__ == "__main__":
    unittest.main()
