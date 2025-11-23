"""
Quality Auto-Fixer - Applies Ruff auto-fixes.

Automatically fixes linting violations where possible.
Follows SRP: Auto-fixing only.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple


class QualityFixer:
    """Auto-fixes code quality issues"""

    async def fix_with_ruff(
        self,
        code: str,
        filepath: Optional[str] = None
    ) -> Tuple[str, bool]:
        """
        Auto-fix code with Ruff.

        Args:
            code: Python code to fix
            filepath: Optional filename hint

        Returns:
            (fixed_code, was_modified)
        """
        # Create temp file
        suffix = Path(filepath).suffix if filepath else '.py'
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=suffix,
            delete=False
        ) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            # Run ruff with --fix
            result = subprocess.run(
                ['ruff', 'check', '--fix', str(temp_path)],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Read fixed code
            fixed_code = temp_path.read_text()

            # Check if modified
            was_modified = (fixed_code != code)

            return fixed_code, was_modified

        except subprocess.TimeoutExpired:
            return code, False
        except FileNotFoundError:
            # Ruff not installed
            return code, False
        finally:
            # Cleanup
            temp_path.unlink(missing_ok=True)

    def format_violations(
        self,
        ruff_violations: list,
        pyright_errors: list
    ) -> str:
        """
        Format violations for display.

        Args:
            ruff_violations: Ruff violations
            pyright_errors: Pyright errors

        Returns:
            Formatted string
        """
        lines = []

        if ruff_violations:
            lines.append("Ruff Violations:")
            for v in ruff_violations[:10]:  # Limit to 10
                if isinstance(v, dict) and 'message' in v:
                    line = v.get('location', {}).get('row', '?')
                    msg = v.get('message', '')
                    lines.append(f"  Line {line}: {msg}")

        if pyright_errors:
            lines.append("\nPyright Type Errors:")
            for e in pyright_errors[:10]:  # Limit to 10
                if isinstance(e, dict) and 'message' in e:
                    line = e.get('range', {}).get('start', {}).get('line', '?')
                    msg = e.get('message', '')
                    lines.append(f"  Line {line}: {msg}")

        return "\n".join(lines) if lines else "No issues found"
