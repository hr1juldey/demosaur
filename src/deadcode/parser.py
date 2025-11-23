"""
Vulture Output Parser - Parses Vulture text output.

Converts Vulture's text format into structured data.
Follows SRP: Parsing only.
"""

import re
from typing import List, Dict, Any


class VultureOutputParser:
    """Parses Vulture text output into structured data"""

    def parse(self, output: str, filename: str) -> List[Dict[str, Any]]:
        """
        Parse vulture text output into structured data.

        Args:
            output: Raw vulture stdout
            filename: File being analyzed

        Returns:
            List of dead code items
        """
        items = []

        for line in output.strip().split('\n'):
            if not line or ':' not in line:
                continue

            # Parse: file:line: message (confidence%)
            try:
                parts = line.split(':', 3)
                if len(parts) >= 3:
                    line_num = int(parts[1])
                    message = parts[2].strip() if len(parts) > 2 else ""

                    # Extract confidence
                    confidence = self._extract_confidence(message)

                    # Extract type and name
                    item_type, name = self._extract_type_and_name(message)

                    items.append({
                        "type": item_type,
                        "name": name,
                        "line": line_num,
                        "confidence": confidence,
                        "file": filename,
                        "message": message
                    })

            except (ValueError, IndexError):
                continue

        return items

    def _extract_confidence(self, message: str) -> int:
        """Extract confidence percentage from message"""
        match = re.search(r'\((\d+)% confidence\)', message)
        return int(match.group(1)) if match else 60

    def _extract_type_and_name(self, message: str) -> tuple:
        """Extract item type and name from message"""
        msg_lower = message.lower()

        if 'unused import' in msg_lower:
            name = message.split("'")[1] if "'" in message else "unknown"
            return "import", name
        elif 'unused function' in msg_lower or 'unused method' in msg_lower:
            name = message.split("'")[1] if "'" in message else "unknown"
            return "function", name
        elif 'unused class' in msg_lower:
            name = message.split("'")[1] if "'" in message else "unknown"
            return "class", name
        elif 'unused variable' in msg_lower:
            name = message.split("'")[1] if "'" in message else "unknown"
            return "variable", name
        elif 'unreachable code' in msg_lower:
            return "unreachable", "code"
        else:
            return "unknown", "unknown"
