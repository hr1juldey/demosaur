"""
Dead Code Reporter - Formats reports for display.

Formats dead code analysis for human readability.
Follows SRP: Report formatting only.
"""

from typing import List, Dict
from src.deadcode.analyzer import DeadCodeReport, DeadCodeItem


class DeadCodeReporter:
    """Formats dead code reports"""

    def format_report(self, report: DeadCodeReport) -> str:
        """
        Format complete report as text.

        Args:
            report: Dead code report

        Returns:
            Formatted text
        """
        lines = [
            "=" * 60,
            "Dead Code Analysis Report",
            "=" * 60,
            "",
            f"Total Items: {report.total_items}",
            f"High Confidence (≥90%): {report.high_confidence_count}",
            f"Removable Lines: {report.removable_lines}",
            f"Potential Token Savings: ~{report.potential_token_savings} tokens",
            ""
        ]

        # Group by type
        by_type = self._group_by_type(report.items)

        for item_type, items in by_type.items():
            if not items:
                continue

            lines.append(f"\n{item_type.upper()}S ({len(items)}):")
            lines.append("-" * 40)

            for item in items:
                confidence_str = f"{item.confidence}%"
                lines.append(
                    f"  Line {item.line}: {item.name} "
                    f"({confidence_str} confidence)"
                )

        return "\n".join(lines)

    def format_summary(self, report: DeadCodeReport) -> str:
        """Format brief summary"""
        if report.total_items == 0:
            return "✓ No dead code detected"

        return (
            f"⚠ Found {report.total_items} dead code items "
            f"({report.high_confidence_count} high confidence). "
            f"Potential savings: ~{report.potential_token_savings} tokens"
        )

    def format_by_confidence(
        self,
        report: DeadCodeReport
    ) -> Dict[str, List[DeadCodeItem]]:
        """Group items by confidence level"""
        groups = {
            "100": [],
            "90-99": [],
            "80-89": [],
            "60-79": []
        }

        for item in report.items:
            if item.confidence == 100:
                groups["100"].append(item)
            elif item.confidence >= 90:
                groups["90-99"].append(item)
            elif item.confidence >= 80:
                groups["80-89"].append(item)
            else:
                groups["60-79"].append(item)

        return groups

    def _group_by_type(
        self,
        items: List[DeadCodeItem]
    ) -> Dict[str, List[DeadCodeItem]]:
        """Group items by type"""
        groups = {
            "import": [],
            "function": [],
            "class": [],
            "variable": [],
            "unreachable": []
        }

        for item in items:
            if item.type in groups:
                groups[item.type].append(item)
            else:
                if "unknown" not in groups:
                    groups["unknown"] = []
                groups["unknown"].append(item)

        return groups
