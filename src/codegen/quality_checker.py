"""
Code Quality Checker - Ruff and Pyright integration.

Checks generated code for linting and type errors.
Follows SRP: Quality checking only.
"""

import subprocess
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional


class QualityChecker:
    """Checks code quality using Ruff and Pyright"""

    async def check_with_ruff(
        self,
        code: str,
        filepath: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Run Ruff linter on code.

        Args:
            code: Python code to check
            filepath: Optional filename hint

        Returns:
            List of violations
        """
        # Create temp file
        suffix = Path(filepath).suffix if filepath else '.py'
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=suffix,
            delete=False
        ) as f:
            f.write(code)
            temp_path = f.name

        try:
            # Run ruff
            result = subprocess.run(
                ['ruff', 'check', '--output-format=json', temp_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Parse JSON output
            if result.stdout:
                violations = json.loads(result.stdout)
                return violations

            return []

        except subprocess.TimeoutExpired:
            return [{"error": "Ruff timeout"}]
        except json.JSONDecodeError:
            return [{"error": "Failed to parse ruff output"}]
        except FileNotFoundError:
            return [{"error": "Ruff not installed"}]
        finally:
            # Cleanup
            Path(temp_path).unlink(missing_ok=True)

    async def check_with_pyright(
        self,
        code: str,
        filepath: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Run Pyright type checker on code.

        Args:
            code: Python code to check
            filepath: Optional filename hint

        Returns:
            List of type errors
        """
        # Create temp file
        suffix = Path(filepath).suffix if filepath else '.py'
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=suffix,
            delete=False
        ) as f:
            f.write(code)
            temp_path = f.name

        try:
            # Run pyright
            result = subprocess.run(
                ['pyright', '--outputjson', temp_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Parse JSON output
            if result.stdout:
                output = json.loads(result.stdout)
                # Extract diagnostics
                return output.get('generalDiagnostics', [])

            return []

        except subprocess.TimeoutExpired:
            return [{"error": "Pyright timeout"}]
        except json.JSONDecodeError:
            return [{"error": "Failed to parse pyright output"}]
        except FileNotFoundError:
            return [{"error": "Pyright not installed"}]
        finally:
            Path(temp_path).unlink(missing_ok=True)
