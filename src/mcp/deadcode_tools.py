"""
MCP Tools for Dead Code Detection.

Provides dead code analysis and cleaning via MCP interface.
"""

from pathlib import Path
from typing import Dict, Any

from src.deadcode.detector import VultureDetector
from src.deadcode.analyzer import DeadCodeAnalyzer
from src.deadcode.reporter import DeadCodeReporter
from src.deadcode.cleaner import DeadCodeCleaner


async def detect_dead_code(
    task_id: str,
    module_name: str,
    min_confidence: int = 80
) -> Dict[str, Any]:
    """
    Detect dead code in a generated module.

    Args:
        task_id: Task ID
        module_name: Module to analyze (e.g., "validator.py")
        min_confidence: Minimum confidence threshold (60-100)

    Returns:
        Dead code analysis report
    """
    # Get module code
    code_path = Path(f"tasks/{task_id}/generated/{module_name}")
    if not code_path.exists():
        return {"error": f"Module {module_name} not found"}

    code = code_path.read_text()

    # Detect with Vulture
    detector = VultureDetector()
    vulture_results = await detector.detect(
        code,
        filename=module_name,
        min_confidence=min_confidence
    )

    # Analyze and combine results
    analyzer = DeadCodeAnalyzer()
    report = analyzer.combine_results(vulture_results)

    # Filter by confidence
    filtered_report = analyzer.filter_by_confidence(
        report,
        min_confidence
    )

    # Format report
    reporter = DeadCodeReporter()
    summary = reporter.format_summary(filtered_report)
    by_confidence = reporter.format_by_confidence(filtered_report)

    return {
        "task_id": task_id,
        "module": module_name,
        "summary": summary,
        "total_items": filtered_report.total_items,
        "high_confidence_count": filtered_report.high_confidence_count,
        "potential_token_savings": filtered_report.potential_token_savings,
        "by_confidence": {
            level: [
                {
                    "type": item.type,
                    "name": item.name,
                    "line": item.line,
                    "confidence": item.confidence,
                    "reason": item.reason
                }
                for item in items
            ]
            for level, items in by_confidence.items()
        }
    }


async def clean_dead_code(
    task_id: str,
    module_name: str,
    min_confidence: int = 100,
    auto_apply: bool = False
) -> Dict[str, Any]:
    """
    Clean dead code from a module.

    Args:
        task_id: Task ID
        module_name: Module to clean
        min_confidence: Only remove >= this confidence
        auto_apply: If True, write cleaned code back

    Returns:
        Cleaning result
    """
    # Get module code
    code_path = Path(f"tasks/{task_id}/generated/{module_name}")
    if not code_path.exists():
        return {"error": f"Module {module_name} not found"}

    code = code_path.read_text()

    # Detect dead code first
    result = await detect_dead_code(task_id, module_name, min_confidence)
    if "error" in result:
        return result

    # Clean code
    cleaner = DeadCodeCleaner()
    # Convert dict items back to DeadCodeItem objects would be needed
    # For now, return analysis only

    return {
        "task_id": task_id,
        "module": module_name,
        "items_to_remove": result["total_items"],
        "lines_to_remove": result["high_confidence_count"],
        "token_savings": result["potential_token_savings"],
        "auto_applied": False,
        "message": "Use refinement to apply changes"
    }
