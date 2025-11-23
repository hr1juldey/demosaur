"""
Dead Code Detector using Vulture.

Detects unused code using static analysis.
Follows SRP: Vulture integration only.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.deadcode.parser import VultureOutputParser


class VultureDetector:
    """Detects dead code using Vulture"""

    def __init__(self):
        self.parser = VultureOutputParser()

    async def detect(
        self,
        code: str,
        filename: Optional[str] = None,
        min_confidence: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Detect dead code in Python code.

        Args:
            code: Python code to analyze
            filename: Optional filename hint
            min_confidence: Minimum confidence (60-100)

        Returns:
            List of dead code items
        """
        # Create temp file
        suffix = Path(filename).suffix if filename else '.py'
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=suffix,
            delete=False
        ) as f:
            f.write(code)
            temp_path = Path(f.name)

        try:
            # Run vulture
            result = subprocess.run(
                [
                    'vulture',
                    str(temp_path),
                    f'--min-confidence={min_confidence}'
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Parse output
            dead_items = self.parser.parse(
                result.stdout,
                filename or temp_path.name
            )

            return dead_items

        except subprocess.TimeoutExpired:
            return [{"error": "Vulture timeout"}]
        except FileNotFoundError:
            return [{"error": "Vulture not installed"}]
        finally:
            # Cleanup
            temp_path.unlink(missing_ok=True)
