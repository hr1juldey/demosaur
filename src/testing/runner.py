"""
Test execution engine.

Runs pytest tests and captures results.
Follows SRP: Test execution only.
"""

import subprocess
import tempfile
from pathlib import Path

from src.common.types import TestResults
from src.common.config import settings


class TestRunner:
    """Executes pytest tests in isolated environment"""

    def __init__(self):
        self.workspace = None

    async def run_tests(
        self,
        code: str,
        test_code: str,
        module_name: str
    ) -> TestResults:
        """
        Run pytest tests for code.

        Args:
            code: Source code
            test_code: Test code
            module_name: Name of module

        Returns: Test results
        """
        # Create temporary workspace
        self.workspace = Path(tempfile.mkdtemp(prefix="test_"))

        try:
            # Write code and tests
            code_file = self.workspace / f"{module_name}.py"
            test_file = self.workspace / f"test_{module_name}.py"

            code_file.write_text(code)
            test_file.write_text(test_code)

            # Run pytest
            result = await self._run_pytest(test_file)

            return result

        finally:
            # Cleanup
            if self.workspace and self.workspace.exists():
                import shutil
                shutil.rmtree(self.workspace, ignore_errors=True)

    async def _run_pytest(self, test_file: Path) -> TestResults:
        """Execute pytest and parse results"""
        try:
            # Run pytest with JSON report
            cmd = [
                "pytest",
                str(test_file),
                "--json-report",
                "--json-report-file=/tmp/report.json",
                "-v",
                f"--timeout={settings.test_timeout_seconds}"
            ]

            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=settings.test_timeout_seconds + 5
            )

            # Parse results
            return self._parse_pytest_output(
                process.stdout,
                process.stderr,
                process.returncode
            )

        except subprocess.TimeoutExpired:
            return TestResults(
                total=0,
                passed=0,
                failed=0,
                errors=["Tests timed out"],
                duration=settings.test_timeout_seconds
            )

        except Exception as e:
            return TestResults(
                total=0,
                passed=0,
                failed=0,
                errors=[f"Test execution failed: {str(e)}"],
                duration=0.0
            )

    def _parse_pytest_output(
        self,
        stdout: str,
        stderr: str,
        returncode: int
    ) -> TestResults:
        """Parse pytest output to TestResults"""
        # Simple parsing (can be enhanced)
        lines = stdout.split('\n')

        total = 0
        passed = 0
        failed = 0
        errors = []

        for line in lines:
            if " passed" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed":
                        passed = int(parts[i-1])
                        total += passed

            if " failed" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "failed":
                        failed = int(parts[i-1])
                        total += failed

        if stderr:
            errors.append(stderr)

        return TestResults(
            total=total or 1,  # At least 1
            passed=passed,
            failed=failed,
            errors=errors,
            duration=0.0  # TODO: extract from output
        )
