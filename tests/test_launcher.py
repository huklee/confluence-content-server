import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "run_server.sh"


class ServerLauncherTest(unittest.TestCase):
    def run_launcher(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(LAUNCHER), *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_launcher_is_executable_and_documents_options(self) -> None:
        self.assertTrue(os.access(LAUNCHER, os.X_OK))
        result = self.run_launcher("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--port PORT", result.stdout)
        self.assertIn("--plantuml-jar PATH", result.stdout)

    def test_dry_run_resolves_custom_host_port_and_reload(self) -> None:
        result = self.run_launcher(
            "--host", "0.0.0.0", "--port", "8123", "--reload", "--dry-run"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--host 0.0.0.0", result.stdout)
        self.assertIn("--port 8123", result.stdout)
        self.assertIn("--reload", result.stdout)

    def test_invalid_port_is_rejected(self) -> None:
        result = self.run_launcher("--port", "70000", "--dry-run")
        self.assertEqual(result.returncode, 2)
        self.assertIn("port must be an integer from 1 to 65535", result.stderr)


if __name__ == "__main__":
    unittest.main()
