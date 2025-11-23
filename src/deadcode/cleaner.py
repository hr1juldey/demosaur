"""
Dead Code Cleaner - Removes dead code safely.

Auto-removes high-confidence dead code with backup.
Follows SRP: Code removal only.
"""

import ast
from typing import List
from dataclasses import dataclass

from src.deadcode.analyzer import DeadCodeItem


@dataclass
class CleaningResult:
    """Result of cleaning operation"""
    original_code: str
    cleaned_code: str
    removed_items: List[DeadCodeItem]
    lines_removed: int
    success: bool
    error: str = ""


class DeadCodeCleaner:
    """Removes dead code from Python source"""

    def clean(
        self,
        code: str,
        dead_items: List[DeadCodeItem],
        min_confidence: int = 100
    ) -> CleaningResult:
        """
        Remove dead code from source.

        Args:
            code: Python source code
            dead_items: List of dead code items
            min_confidence: Only remove items >= this confidence

        Returns:
            CleaningResult with cleaned code
        """
        # Filter by confidence
        items_to_remove = [
            item for item in dead_items
            if item.confidence >= min_confidence
        ]

        if not items_to_remove:
            return CleaningResult(
                original_code=code,
                cleaned_code=code,
                removed_items=[],
                lines_removed=0,
                success=True
            )

        try:
            # Parse code for validation
            ast.parse(code)
            lines = code.split('\n')

            # Get lines to remove
            lines_to_remove = self._get_lines_to_remove(
                items_to_remove
            )

            # Remove lines (in reverse order to preserve line numbers)
            cleaned_lines = [
                line for idx, line in enumerate(lines, 1)
                if idx not in lines_to_remove
            ]

            cleaned_code = '\n'.join(cleaned_lines)

            return CleaningResult(
                original_code=code,
                cleaned_code=cleaned_code,
                removed_items=items_to_remove,
                lines_removed=len(lines_to_remove),
                success=True
            )

        except SyntaxError as e:
            return CleaningResult(
                original_code=code,
                cleaned_code=code,
                removed_items=[],
                lines_removed=0,
                success=False,
                error=f"Syntax error: {e}"
            )

    def _get_lines_to_remove(
        self,
        items: List[DeadCodeItem]
    ) -> set:
        """Get set of line numbers to remove"""
        lines_to_remove = set()

        for item in items:
            lines_to_remove.add(item.line)

        return lines_to_remove
