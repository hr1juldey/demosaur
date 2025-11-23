"""
Dead Code Analyzer - Combines multiple detection sources.

Aggregates results from Ruff, Vulture, and Pyright.
Follows SRP: Analysis aggregation only.
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class DeadCodeItem:
    """Single dead code item"""
    type: str  # import, function, class, variable, unreachable
    name: str
    line: int
    confidence: int  # 60-100
    file: str
    reason: str
    source: str = "vulture"  # vulture, ruff, pyright


@dataclass
class DeadCodeReport:
    """Complete dead code analysis report"""
    items: List[DeadCodeItem] = field(default_factory=list)
    total_items: int = 0
    high_confidence_count: int = 0  # >= 90
    removable_lines: int = 0
    potential_token_savings: int = 0

    def __post_init__(self):
        """Calculate derived fields"""
        self.total_items = len(self.items)
        self.high_confidence_count = sum(
            1 for item in self.items
            if item.confidence >= 90
        )
        self.removable_lines = len(set(
            item.line for item in self.items
            if item.confidence >= 90
        ))
        # Rough estimate: 1 line = 10 tokens
        self.potential_token_savings = self.removable_lines * 10


class DeadCodeAnalyzer:
    """Analyzes and combines dead code detection results"""

    def combine_results(
        self,
        vulture_results: List[Dict[str, Any]],
        ruff_results: List[Dict[str, Any]] = None,
    ) -> DeadCodeReport:
        """
        Combine results from multiple sources.

        Args:
            vulture_results: Results from Vulture
            ruff_results: Optional results from Ruff

        Returns:
            Combined dead code report
        """
        items = []

        # Process Vulture results
        for result in vulture_results:
            if 'error' in result:
                continue

            items.append(DeadCodeItem(
                type=result['type'],
                name=result['name'],
                line=result['line'],
                confidence=result['confidence'],
                file=result['file'],
                reason=result.get('message', ''),
                source='vulture'
            ))

        # Process Ruff results (F401, F841)
        if ruff_results:
            for result in ruff_results:
                if 'error' in result:
                    continue

                # Ruff violations are 100% confidence
                items.append(DeadCodeItem(
                    type='import' if 'F401' in result.get('code', '') else 'variable',
                    name=result.get('message', '').split("'")[1] if "'" in result.get('message', '') else 'unknown',
                    line=result.get('location', {}).get('row', 0),
                    confidence=100,  # Ruff is definitive
                    file=result.get('filename', ''),
                    reason=result.get('message', ''),
                    source='ruff'
                ))

        # Remove duplicates (same line + type)
        items = self._deduplicate(items)

        return DeadCodeReport(items=items)

    def _deduplicate(
        self,
        items: List[DeadCodeItem]
    ) -> List[DeadCodeItem]:
        """Remove duplicate items"""
        seen = set()
        unique = []

        for item in items:
            key = (item.file, item.line, item.type)
            if key not in seen:
                seen.add(key)
                unique.append(item)

        return unique

    def filter_by_confidence(
        self,
        report: DeadCodeReport,
        min_confidence: int
    ) -> DeadCodeReport:
        """Filter report by minimum confidence"""
        filtered_items = [
            item for item in report.items
            if item.confidence >= min_confidence
        ]
        return DeadCodeReport(items=filtered_items)
