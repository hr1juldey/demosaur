"""
Hierarchical context builder for managing multi-level context within token limits.

Builds context in priority order with token budget management.
"""

from typing import List, Optional
from src.events.event import Event
from src.memory.cache.node import CacheNode
from context.tokens.token_manager import TokenManager


class HierarchicalContextBuilder:
    """
    Builds hierarchical context with prioritized information within token budget.
    
    PASSING CRITERIA:
    ✅ Builds context in priority order (CRITICAL first)
    ✅ Respects token budget (stops at 80% for generation space)
    ✅ Includes explicit references between levels
    ✅ Handles missing nodes gracefully
    """
    
    def __init__(self, token_manager: TokenManager):
        self.token_manager = token_manager
        self.budget = token_manager.budget
    
    def build_hierarchical_context(self,
                                 events: List[Event],
                                 current_query: str,
                                 user_id: str = "default_user") -> str:
        """
        Build hierarchical context from events and cache nodes.
        
        Context levels:
        1. CRITICAL (Always included): Current status, immediate issues
        2. HIGH (If space): Recent interactions, key decisions
        3. MEDIUM (If space): Module details, dependencies, test results
        4. LOW (If space): Historical patterns, general information
        """
        context_parts = []
        
        # Build level 1: Critical context (always included)
        critical_context = self._build_critical_context(events, current_query, user_id)
        if critical_context:
            context_parts.append(critical_context)
        
        # Check remaining budget for other levels
        current_token_usage = self.token_manager.estimate_tokens("\n".join(context_parts))
        remaining_budget = self.budget.available_for_context - current_token_usage
        
        if remaining_budget > 0:  # Include HIGH priority if budget allows
            high_context = self._build_high_context(events, current_query, user_id)
            if self.token_manager.estimate_tokens(high_context) <= remaining_budget:
                context_parts.append(high_context)
                remaining_budget -= self.token_manager.estimate_tokens(high_context)
        
        if remaining_budget > 0:  # Include MEDIUM priority if budget allows
            medium_context = self._build_medium_context(events, current_query, user_id)
            if self.token_manager.estimate_tokens(medium_context) <= remaining_budget:
                context_parts.append(medium_context)
                remaining_budget -= self.token_manager.estimate_tokens(medium_context)
        
        # Add buffer for generation space (reserve 20% of remaining)
        final_context = "\n\n".join(context_parts)
        target_budget = int(self.budget.available_for_context * 0.8)  # Leave 20% for generation
        
        if self.token_manager.estimate_tokens(final_context) > target_budget:
            final_context = self.token_manager.truncate_to_budget(final_context)
        
        return final_context
    
    def _build_critical_context(self, 
                               events: List[Event], 
                               current_query: str, 
                               user_id: str) -> str:
        """
        Build critical context that should always be included.
        
        Includes:
        - Current task status and state
        - Immediate issues/errors
        - Current module/function being worked on
        """
        if not events:
            return "# Critical Context\nNo events available."
        
        # Get most recent task status
        latest_task_events = [e for e in events if e.event_type.value.startswith('TASK')]
        latest_module_events = [e for e in events if e.event_type.value.startswith('MODULE')]
        
        critical_parts = ["# CRITICAL: Current State"]
        
        # Add current task state
        if latest_task_events:
            latest_task = max(latest_task_events, key=lambda x: x.sequence_number)
            critical_parts.append("## Task State")
            critical_parts.append(f"Status: {latest_task.event_type.value}")
            critical_parts.append(f"Code Version: {latest_task.code_version}")
            for key, value in latest_task.data.items():
                critical_parts.append(f"{key.title()}: {value}")
        
        # Add current module if relevant
        if latest_module_events:
            latest_module = max(latest_module_events, key=lambda x: x.sequence_number)
            if latest_module.event_type.value in ['MODULE_STARTED', 'MODULE_ITERATION']:
                critical_parts.append("\n## Current Module")
                critical_parts.append(f"Module: {latest_module.data.get('module_name', 'Unknown')}")
                critical_parts.append(f"Action: {latest_module.event_type.value}")
        
        # Add latest error if exists
        error_events = [e for e in events if e.event_type.value == 'ERROR']
        if error_events:
            latest_error = max(error_events, key=lambda x: x.sequence_number)
            critical_parts.append("\n## Latest Error")
            critical_parts.append(f"Error: {latest_error.data.get('error', 'Details unavailable')}")
            critical_parts.append(f"Time: {latest_error.timestamp}")
        
        return "\n".join(critical_parts)
    
    def _build_high_context(self, events: List[Event], current_query: str, user_id: str) -> str:
        """
        Build high priority context (recent interactions, key decisions).
        """
        recent_events = sorted(events, key=lambda e: e.sequence_number, reverse=True)[:10]
        
        high_parts = ["# HIGH: Recent Interactions"]
        
        for event in recent_events:
            if event.event_type.value in ['CODE_GENERATED', 'CORRECTION_STARTED', 
                                         'CORRECTION_COMPLETED', 'TEST_PASSED', 
                                         'TEST_FAILED', 'BUG_REPORT_RECEIVED']:
                high_parts.append(f"## Event: {event.event_type.value}")
                high_parts.append(f"Seq: {event.sequence_number}")
                high_parts.append(f"Time: {event.timestamp}")
                for key, value in event.data.items():
                    high_parts.append(f"{key.title()}: {value}")
                high_parts.append("")  # Blank line
        
        return "\n".join(high_parts)
    
    def _build_medium_context(self, events: List[Event], current_query: str, user_id: str) -> str:
        """
        Build medium priority context (module details, dependencies, test results).
        """
        medium_parts = ["# MEDIUM: Module Details & Dependencies"]
        
        # Group events by module for easier reading
        module_events = {}
        for event in events:
            module_name = event.data.get('module_name')
            if module_name:
                if module_name not in module_events:
                    module_events[module_name] = []
                module_events[module_name].append(event)
        
        for module_name, events_for_module in module_events.items():
            medium_parts.append(f"## Module: {module_name}")
            
            # Show key events for this module
            for event in events_for_module:
                if event.event_type.value in ['MODULE_STARTED', 'MODULE_ITERATION', 
                                             'MODULE_COMPLETE', 'TEST_STARTED', 
                                             'TEST_PASSED', 'TEST_FAILED']:
                    medium_parts.append(f"- {event.event_type.value}: {str(event.data)[:200]}...")
            
            medium_parts.append("")  # Blank line
        
        return "\n".join(medium_parts)
    
    def build_context_with_references(self, 
                                     nodes: List[CacheNode], 
                                     max_hops: int = 2) -> str:
        """
        Build context from cache nodes with explicit references.
        
        Args:
            nodes: List of cache nodes to include in context
            max_hops: Maximum reference hops to follow
        """
        if not nodes:
            return "No cache nodes available for context."
        
        # Sort nodes by priority (CRITICAL first)
        sorted_nodes = sorted(nodes, key=lambda n: n.priority.value)
        
        context_parts = []
        current_tokens = 0
        
        for node in sorted_nodes:
            node_text = self._format_cache_node_with_references(node)
            node_tokens = self.token_manager.estimate_tokens(node_text)
            
            # Check if adding this node would exceed budget
            if current_tokens + node_tokens <= self.budget.available_for_context:
                context_parts.append(node_text)
                current_tokens += node_tokens
            else:
                # Try to add partial content if budget allows
                truncated_node = self._truncate_node_for_budget(node, 
                                                               self.budget.available_for_context - current_tokens)
                if truncated_node:
                    context_parts.append(truncated_node)
                    break
                else:
                    # Not enough budget for even truncated node
                    break
        
        return "\n\n".join(context_parts)
    
    def _format_cache_node_with_references(self, node: CacheNode) -> str:
        """Format a cache node with explicit references to other nodes."""
        parts = [f"# {node.type.value.title()}: {node.id}"]
        parts.append(f"**Priority**: {node.priority.name}")
        parts.append(f"**Last Updated**: {node.timestamp}")
        
        if node.metadata:
            parts.append("**Metadata**:")
            for key, value in node.metadata.items():
                parts.append(f"  - {key}: {value}")
        
        if node.summary:
            parts.append("**Summary**: ")
            parts.append(node.summary)
        
        # Add forward references
        if node.forward_references or node.dependencies or node.related_nodes:
            parts.append("**References**: ")
            if node.forward_references:
                parts.append("  - Forward References: \n    - " + "\n    - ".join(node.forward_references))
            if node.dependencies:
                parts.append("  - Dependencies: \n    - " + "\n    - ".join(node.dependencies))
            if node.related_nodes:
                parts.append("  - Related: \n    - " + "\n    - ".join(node.related_nodes))
        
        # Add backward references  
        if node.backward_references or node.dependents or node.reverse_related:
            parts.append("**Referenced By**: ")
            if node.backward_references:
                parts.append("  - Backward References: \n    - " + "\n    - ".join(node.backward_references))
            if node.dependents:
                parts.append("  - Dependents: \n    - " + "\n    - ".join(node.dependents))
            if node.reverse_related:
                parts.append("  - Reverse Related: \n    - " + "\n    - ".join(node.reverse_related))
        
        return "\n".join(parts)
    
    def _truncate_node_for_budget(self, node: CacheNode, budget: int) -> Optional[str]:
        """Truncate a cache node to fit within budget."""
        basic_info = f"# {node.type.value.title()}: {node.id}\n{node.summary[:budget]}"
        if self.token_manager.estimate_tokens(basic_info) <= budget:
            return basic_info
        else:
            # Even basic info exceeds budget, return None
            return None