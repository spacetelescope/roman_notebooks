"""Execute the existing workflow's version script against disposable Git tags."""

from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash") if os.name != "nt" else r"C:\Program Files\Git\bin\bash.exe"


@unittest.skipUnless(BASH and Path(BASH).exists() and shutil.which("git"), "Git and Bash required")
class ReleaseVersionTests(unittest.TestCase):
    def calculate(self, tags, release_type):
        workflow = yaml.safe_load((ROOT / ".github/workflows/release.yaml").read_text())
        script = next(step["run"] for step in workflow["jobs"]["release"]["steps"]
                      if step.get("id") == "ver")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def git(*args):
                subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)

            git("init")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "commit", "--allow-empty", "-m", "fixture")
            git("remote", "add", "origin", ".")
            for tag in tags:
                git("tag", tag)
            script_path = root / "compute.sh"
            script_path.write_text(script, encoding="utf-8")
            environment = dict(os.environ, RELEASE_TYPE=release_type,
                               GITHUB_REF="refs/heads/main", GITHUB_SHA="fixture",
                               GITHUB_OUTPUT="versions.txt")
            result = subprocess.run([BASH, "compute.sh"], cwd=root, env=environment,
                                    text=True, capture_output=True)
            if result.returncode:
                self.fail(result.stdout + result.stderr)
            return dict(line.split("=", 1) for line in (root / "versions.txt").read_text().splitlines())

    def test_semver_calver_cases(self):
        year = datetime.now(timezone.utc).year
        cases = [
            ([], "minor", "v0.1.0", f"{year}.1.0"),
            (["v1.2.0", f"{year}.1.7"], "minor", "v1.3.0", f"{year}.1.8"),
            (["v1.2.0", f"{year}.1.7"], "major", "v2.0.0", f"{year}.2.0"),
            (["v4.9.0", f"{year - 1}.8.9"], "minor", "v4.10.0", f"{year}.1.0"),
            (["v4.9.0", f"{year - 1}.8.9"], "major", "v5.0.0", f"{year}.1.0"),
        ]
        for tags, bump, semver, calver in cases:
            with self.subTest(tags=tags, bump=bump):
                self.assertEqual(self.calculate(tags, bump), dict(semver=semver, calver=calver))
