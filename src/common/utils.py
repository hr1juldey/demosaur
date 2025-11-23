"""
Utility functions for Code Intern MCP Server.

General-purpose helper functions used across modules.
Follows SRP: Each function has single, well-defined purpose.
"""

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path


def generate_task_id() -> str:
    """Generate unique task ID using timestamp + hash"""
    timestamp = datetime.utcnow().isoformat()
    hash_input = f"{timestamp}".encode()
    hash_digest = hashlib.sha256(hash_input).hexdigest()[:8]
    return f"task-{hash_digest}"


def sanitize_filename(name: str) -> str:
    """Convert module name to valid filename"""
    # Replace special chars with underscore
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Remove multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Ensure it doesn't start with number
    if sanitized[0].isdigit():
        sanitized = f"m_{sanitized}"
    return sanitized.lower()


def format_code(code: str) -> str:
    """Basic code formatting"""
    # Remove trailing whitespace
    lines = [line.rstrip() for line in code.split('\n')]
    # Remove multiple blank lines
    formatted = '\n'.join(lines)
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)
    return formatted.strip()


def count_lines(code: str) -> int:
    """Count non-empty, non-comment lines"""
    lines = code.split('\n')
    code_lines = [
        line for line in lines
        if line.strip() and not line.strip().startswith('#')
    ]
    return len(code_lines)


def extract_imports(code: str) -> List[str]:
    """Extract import statements from code"""
    import_pattern = r'^(?:from\s+[\w.]+\s+)?import\s+.*$'
    lines = code.split('\n')
    imports = [
        line.strip() for line in lines
        if re.match(import_pattern, line.strip())
    ]
    return imports


def safe_json_dumps(obj: Any, indent: int = 2) -> str:
    """JSON dumps with fallback for non-serializable objects"""
    def default_handler(o):
        if hasattr(o, '__dict__'):
            return o.__dict__
        return str(o)

    return json.dumps(obj, indent=indent, default=default_handler)


def ensure_directory(path: str | Path) -> Path:
    """Ensure directory exists, create if not"""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def parse_complexity(description: str) -> Optional[str]:
    """Extract complexity notation from text"""
    # Match O(n), O(log n), O(n^2), etc.
    pattern = r'O\([^)]+\)'
    match = re.search(pattern, description)
    return match.group(0) if match else None


def truncate_text(text: str, max_length: int = 1000) -> str:
    """Truncate text with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
