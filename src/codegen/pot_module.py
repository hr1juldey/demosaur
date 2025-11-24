"""
ProgramOfThought wrapper for code execution.

Wraps DSPy POT with custom interpreter configuration.
Follows SRP: POT execution only.
"""

import dspy
from dspy.primitives import PythonInterpreter
import tempfile
from pathlib import Path
from typing import Dict, Any

from src.common.config import settings


class CodeExecutor:
    """Executes code using DSPy ProgramOfThought"""

    def __init__(self):
        self.workspace = None
        self.interpreter = None
        self._setup_interpreter()

    def _setup_interpreter(self):
        """Setup sandboxed Python interpreter"""
        # Create temporary workspace
        self.workspace = Path(tempfile.mkdtemp(prefix="code_intern_"))

        # Configure interpreter with sandbox
        self.interpreter = PythonInterpreter(
            # Security: limit what code can do
            enable_read_paths=[str(self.workspace)],
            enable_write_paths=[str(self.workspace)],
            enable_network_access=settings.sandbox_enable_network,

            # Cleanup
            sync_files=False  # Don't sync changes back
        )

    def execute(self, code: str) -> Dict[str, Any]:
        """
        Execute Python code in sandbox.

        Args:
            code: Python code to execute

        Returns: Dict with result, stdout, stderr, error
        """
        try:
            with self.interpreter as interp:
                result = interp(code)

            return {
                "success": True,
                "result": result,
                "stdout": "",
                "stderr": "",
                "error": None
            }

        except TimeoutError as e:
            return {
                "success": False,
                "result": None,
                "stdout": "",
                "stderr": "",
                "error": f"Timeout: {str(e)}"
            }

        except Exception as e:
            return {
                "success": False,
                "result": None,
                "stdout": "",
                "stderr": str(e),
                "error": str(e)
            }

    def cleanup(self):
        """Cleanup temporary workspace"""
        if self.workspace and self.workspace.exists():
            import shutil
            shutil.rmtree(self.workspace, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def create_pot_module(signature: type) -> dspy.Module:
    """
    Create ProgramOfThought module with custom interpreter.

    Args:
        signature: DSPy signature class

    Returns: Configured POT module
    """
    # Note: ProgramOfThought uses PythonInterpreter internally
    # We pass the signature and it handles execution
    pot = dspy.ProgramOfThought(signature)
    return pot
