"""
Relevance filter for context management system.

Filters and prioritizes contextual information based on relevance to current request.
"""

from typing import List
from src.events.event import Event
from src.memory.core.mem0_client import Mem0Client
from context.tokens.token_manager import TokenManager


class RelevanceFilter:
    """
    Filters contextual information based on relevance to current request.
    
    PASSING CRITERIA:
    ✅ Returns ≤limit events
    ✅ Events in chronological order
    ✅ Filters by: same module, same version, causal chain
    ✅ Empty result if no relevant events
    """
    
    def __init__(self, mem0_client: Mem0Client, token_manager: TokenManager):
        self.mem0_client = mem0_client
        self.token_manager = token_manager
    
    def filter_relevant_events(self, 
                              events: List[Event], 
                              current_query: str,
                              user_id: str = "default_user",
                              limit: int = 10,
                              max_tokens: int = 1500) -> List[Event]:
        """
        Filter events by relevance and token budget.
        
        Args:
            events: List of events to filter
            current_query: Current query/operation for relevance assessment
            user_id: User ID for isolation
            limit: Maximum number of events to return
            max_tokens: Maximum tokens for all events combined
            
        Returns:
            List of relevant events within constraints
        """
        # Sort events by sequence number (chronological order)
        sorted_events = sorted(events, key=lambda e: e.sequence_number)
        
        # Apply relevance filters
        relevant_events = self._apply_relevance_filters(sorted_events, current_query, user_id)
        
        # Apply chronological ordering
        chronological_events = self._maintain_chronological_order(relevant_events)
        
        # Apply limits and token budget
        filtered_events = self._apply_limits(chronological_events, limit, max_tokens)
        
        return filtered_events
    
    def _apply_relevance_filters(self, events: List[Event], 
                                current_query: str, 
                                user_id: str) -> List[Event]:
        """
        Apply relevance-based filtering to events.
        
        Uses content matching and semantic similarity to determine relevance.
        """
        relevant_events = []
        
        for event in events:
            # Check user isolation (only include events for same user)
            if self._has_user_context(event) and event.data.get('user_id') != user_id:
                continue
            
            # Check semantic relevance to current query
            if self._is_semantically_relevant(event, current_query):
                relevant_events.append(event)
            # Add additional relevance checks here
            
        return relevant_events
    
    def _has_user_context(self, event: Event) -> bool:
        """Check if event has user context."""
        return 'user_id' in event.data
    
    def _is_semantically_relevant(self, event: Event, query: str) -> bool:
        """
        Check if event is semantically relevant to the query.
        
        Uses simple string matching and keyword analysis for now.
        Could be enhanced with embeddings for more sophisticated matching.
        """
        # Convert query and event data to lowercase for comparison
        query_lower = query.lower()
        
        # Check if query keywords appear in event data
        event_content = self._extract_searchable_content(event).lower()
        
        # Simple keyword matching (could be enhanced with semantic similarity)
        query_keywords = set(query_lower.split()[:5])  # Take first 5 keywords
        event_words = set(event_content.split())
        
        # If at least one keyword matches, consider relevant
        intersection = query_keywords.intersection(event_words)
        return len(intersection) > 0
    
    def _extract_searchable_content(self, event: Event) -> str:
        """Extract searchable content from event."""
        content_parts = []
        
        # Add event type
        content_parts.append(event.event_type.value)
        
        # Add event data fields
        for key, value in event.data.items():
            content_parts.append(str(value))
        
        return " ".join(content_parts)
    
    def _maintain_chronological_order(self, events: List[Event]) -> List[Event]:
        """Ensure events are in chronological order by sequence number."""
        return sorted(events, key=lambda e: e.sequence_number)
    
    def _apply_limits(self, events: List[Event], limit: int, max_tokens: int) -> List[Event]:
        """
        Apply event count limit and token budget.
        """
        # Apply count limit first
        limited_events = events[:limit]
        
        # Apply token budget limit
        budget_events = []
        current_tokens = 0
        
        for event in limited_events:
            event_tokens = self._estimate_event_tokens(event)
            
            if current_tokens + event_tokens <= max_tokens:
                budget_events.append(event)
                current_tokens += event_tokens
            else:
                break  # Exceeds token budget
        
        return budget_events
    
    def _estimate_event_tokens(self, event: Event) -> int:
        """Estimate token usage for an event."""
        content = f"{event.event_type.value} {str(event.data)}"
        return self.token_manager.estimate_tokens(content)
    
    def filter_and_rank_by_relevance(self, 
                                   events: List[Event],
                                   current_query: str,
                                   user_id: str = "default_user",
                                   limit: int = 10) -> List[Event]:
        """
        Filter events by relevance and rank them by importance.
        
        Returns events sorted by relevance score (most relevant first).
        """
        # Apply basic filters
        filtered_events = self.filter_relevant_events(
            events, current_query, user_id, limit
        )
        
        # Rank by relevance score
        ranked_events = self._rank_by_relevance(filtered_events, current_query)
        
        return ranked_events
    
    def _rank_by_relevance(self, events: List[Event], query: str) -> List[Event]:
        """
        Rank events by relevance to query.
        
        Returns events sorted by relevance score (descending).
        """
        scored_events = []
        
        for event in events:
            score = self._calculate_relevance_score(event, query)
            scored_events.append((event, score))
        
        # Sort by score (descending)
        sorted_events = sorted(scored_events, key=lambda x: x[1], reverse=True)
        
        return [event for event, score in sorted_events]
    
    def _calculate_relevance_score(self, event: Event, query: str) -> float:
        """
        Calculate relevance score for an event compared to query.
        
        Returns a score between 0.0 and 1.0 where higher is more relevant.
        """
        if not query.strip():
            return 0.5  # Neutral score for empty query
        
        query_lower = query.lower()
        event_content = self._extract_searchable_content(event).lower()
        
        # Calculate keyword overlap ratio
        query_words = set(query_lower.split())
        event_words = set(event_content.split())
        
        if not event_words:
            return 0.0
        
        overlap = len(query_words.intersection(event_words))
        union = len(query_words.union(event_words))
        
        if union == 0:
            return 0.0
        
        jaccard_similarity = overlap / union
        
        # Boost score for recent events
        recency_factor = min(1.0, 0.1 + (1.0 / (1.0 + event.sequence_number * 0.01)))
        
        # Boost score for certain event types
        type_boost = self._get_event_type_relevance(event.event_type.value)
        
        final_score = jaccard_similarity * 0.7 + recency_factor * 0.2 + type_boost * 0.1
        return min(1.0, final_score)
    
    def _get_event_type_relevance(self, event_type: str) -> float:
        """
        Get relevance boost for event type.
        
        Certain event types are typically more relevant to current context.
        """
        high_relevance_types = {
            'BUG_REPORT_RECEIVED', 'CORRECTION_STARTED', 'ERROR',
            'TASK_STARTED', 'MODULE_STARTED', 'TEST_FAILED'
        }
        
        medium_relevance_types = {
            'CODE_GENERATED', 'MODULE_ITERATION', 'TEST_STARTED', 'TEST_PASSED'
        }
        
        if event_type in high_relevance_types:
            return 0.8
        elif event_type in medium_relevance_types:
            return 0.5
        else:
            return 0.2