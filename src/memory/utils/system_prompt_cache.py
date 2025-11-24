"""
System prompt cache for context management.

Caches and manages system prompts for efficient token budget utilization.
"""

from typing import Dict, Any
from datetime import datetime
import hashlib


class SystemPromptCache:
    """
    Cache for system prompts to avoid regeneration and manage token usage.

    PASSING CRITERIA:
    ✅ First call generates prompt (cache miss)
    ✅ Second call reuses prompt (cache hit)
    ✅ clear_cache() invalidates all entries
    ✅ Different event_types have different prompts
    """

    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, str] = {}

    def get_system_prompt(self,
                         event_type: str,
                         context_requirements: Dict[str, Any]) -> str:
        """
        Get system prompt for event type, using cache when available.

        Args:
            event_type: Type of event to generate prompt for
            context_requirements: Requirements for context building

        Returns:
            System prompt string
        """
        # Create cache key based on event_type and requirements
        cache_key = self._generate_cache_key(event_type, context_requirements)

        # Check if we have a cached version
        if cache_key in self.cache:
            self._update_access_time(cache_key)
            return self.cache[cache_key]["prompt"]

        # Generate new prompt
        prompt = self._generate_system_prompt(event_type, context_requirements)

        # Cache it
        self.cache[cache_key] = {
            "prompt": prompt,
            "event_type": event_type,
            "requirements": context_requirements.copy(),
            "created_at": datetime.now().isoformat()
        }
        self.access_times[cache_key] = datetime.now().isoformat()

        return prompt

    def _generate_cache_key(self, event_type: str, requirements: Dict[str, Any]) -> str:
        """Generate unique cache key from event type and requirements."""
        req_str = str(sorted(requirements.items()))
        key_str = f"{event_type}:{req_str}"
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def _generate_system_prompt(self, event_type: str, requirements: Dict[str, Any]) -> str:
        """
        Generate system prompt based on event type and requirements.

        PASSING CRITERIA:
        ✅ Proper formatting for event type
        ✅ Context-appropriate instructions
        ✅ Token-efficient (doesn't waste tokens)
        ✅ Consistent across calls with same params
        """
        template_map = {
            "TASK_STARTED": self._generate_task_start_prompt,
            "PLANNING_COMPLETE": self._generate_planning_prompt,
            "MODULE_STARTED": self._generate_module_start_prompt,
            "TEST_STARTED": self._generate_testing_prompt,
            "CORRECTION_STARTED": self._generate_correction_prompt,
            "BUG_REPORT_RECEIVED": self._generate_bug_report_prompt,
            "MODULE_COMPLETE": self._generate_module_complete_prompt,
            "TASK_COMPLETE": self._generate_task_complete_prompt
        }

        generator = template_map.get(event_type, self._generate_generic_prompt)
        return generator(event_type, requirements)

    def _generate_task_start_prompt(self, event_type: str, requirements: Dict[str, Any]) -> str:
        """Generate prompt for task start events."""
        return f"""
You are a coding assistant helping to start a new task.

Task Goal: {requirements.get('goal', 'Not specified')}
Approach: {requirements.get('approach', 'Not specified')}
Technologies: {', '.join(requirements.get('technologies', []))}

Begin by understanding the requirements and planning the implementation approach.
        """.strip()

    def _generate_planning_prompt(self, event_type: str, requirements: Dict[str, Any]) -> str:
        """Generate prompt for planning events."""
        return f"""
You are a coding assistant working on planning implementation.

Current Plan: {requirements.get('current_plan', 'No plan yet')}
Module Requirements: {requirements.get('modules', [])}

Create a detailed plan for implementation with modules and dependencies.
        """.strip()

    def _generate_module_start_prompt(self, event_type: str, requirements: Dict[str, Any]) -> str:
        """Generate prompt for module start events."""
        return f"""
You are implementing a module: {requirements.get('module_name', 'Unknown')}

Requirements: {requirements.get('requirements', 'None specified')}
Dependencies: {requirements.get('dependencies', [])}

Generate code for this module following best practices.
        """.strip()

    def _generate_testing_prompt(self, event_type: str, requirements: Dict[str, Any]) -> str:
        """Generate prompt for testing events."""
        return f"""
You are writing tests for: {requirements.get('module_name', 'Unknown')}

Module code: {requirements.get('module_code', 'Not provided')}
Test requirements: {requirements.get('test_requirements', 'None specified')}

Generate comprehensive tests covering functionality and edge cases.
        """.strip()

    def _generate_correction_prompt(self, event_type: str, requirements: Dict[str, Any]) -> str:
        """Generate prompt for correction events."""
        return f"""
You need to fix: {requirements.get('issue', 'Unknown issue')}

Original code: {requirements.get('original_code', 'Not provided')}
Error details: {requirements.get('error_details', 'No details')}

Apply the necessary corrections to fix the issue.
        """.strip()

    def _generate_bug_report_prompt(self, event_type: str, requirements: Dict[str, Any]) -> str:
        """Generate prompt for bug report events."""
        return f"""
Bug report received: {requirements.get('bug_description', 'No description')}

Code version: {requirements.get('code_version', 'Unknown')}
Environment: {requirements.get('environment', 'Unknown')}

Analyze the bug and suggest fixes or improvements.
        """.strip()

    def _generate_module_complete_prompt(self, event_type: str, requirements: Dict[str, Any]) -> str:
        """Generate prompt for module completion events."""
        return f"""
Module {requirements.get('module_name', 'Unknown')} completed.

Generated code: {requirements.get('generated_code', 'Not provided')}
Test results: {requirements.get('test_results', 'No results')}

Module is complete. Prepare for next steps.
        """.strip()

    def _generate_task_complete_prompt(self, event_type: str, requirements: Dict[str, Any]) -> str:
        """Generate prompt for task completion events."""
        return f"""
Task completed successfully.

Final code version: {requirements.get('final_version', 'Unknown')}
Summary: {requirements.get('summary', 'No summary')}
Metrics: {requirements.get('metrics', {})}

Task is complete. Provide final summary and deliverables.
        """.strip()

    def _generate_generic_prompt(self, event_type: str, requirements: Dict[str, Any]) -> str:
        """Generate generic prompt for unknown event types."""
        return f"""
Processing event: {event_type}

Context: {str(requirements)}

Continue processing the event appropriately.
        """.strip()

    def _update_access_time(self, cache_key: str):
        """Update the access time for a cache entry."""
        self.access_times[cache_key] = datetime.now().isoformat()

    def clear_cache(self) -> None:
        """Clear all cached prompts."""
        self.cache.clear()
        self.access_times.clear()

    def invalidate_old_entries(self, hours_old: int = 24) -> int:
        """
        Remove entries older than specified hours.

        Returns:
            Number of entries removed
        """
        import time
        current_time = time.time()
        cutoff_time = current_time - (hours_old * 3600)

        to_remove = []
        for key, timestamp in self.access_times.items():
            # Convert ISO timestamp to epoch time for comparison
            try:
                entry_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp()
                if entry_time < cutoff_time:
                    to_remove.append(key)
            except ValueError:
                # If timestamp conversion fails, remove the entry
                to_remove.append(key)

        for key in to_remove:
            if key in self.cache:
                del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]

        return len(to_remove)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "entry_count": len(self.cache)
        }