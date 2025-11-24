"""
Cache node data structure with 2-way linking for networked cache system.

Implements bidirectional references to maintain relationships within token limits.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
from src.orchestrator.priority import TaskPriority


class CacheNodeType(Enum):
    """Types of cache nodes for different contexts"""
    TASK = "task"
    MODULE = "module"
    FUNCTION = "function"
    TEST = "test"
    REQUIREMENT = "requirement"
    PLAN = "plan"
    CONCEPT = "concept"
    LIBRARY = "library"
    ERROR = "error"


@dataclass
class CacheNode:
    """
    Cache node with bidirectional references for networked cache.

    Each node maintains both forward references (what it depends on/references)
    and backward references (what references this node), enabling 2-way linking.
    """
    # Node identification
    id: str  # "task:abc123", "module:utils.py", "func:validate_email"
    type: CacheNodeType
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Content and metadata
    summary: str = ""  # Compressed summary within token budget
    full_content_ref: Optional[str] = None  # Reference to full content in EventStore
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata

    # 2-way linking: Forward references (what this node references)
    forward_references: List[str] = field(default_factory=list)  # IDs this node depends on/links to
    dependencies: List[str] = field(default_factory=list)  # Dependencies this node has
    related_nodes: List[str] = field(default_factory=list)  # Related but not dependent nodes

    # 2-way linking: Backward references (what references this node)
    backward_references: List[str] = field(default_factory=list)  # IDs that link TO this node
    dependents: List[str] = field(default_factory=list)  # Nodes that depend on this
    reverse_related: List[str] = field(default_factory=list)  # Nodes related TO this

    # Cache management
    vector_clock: Dict[str, int] = field(default_factory=dict)  # For invalidation
    tokens: int = 0  # Estimated token count for budget management
    priority: TaskPriority = TaskPriority.MEDIUM  # Selection priority
    last_accessed: Optional[str] = None  # Last access timestamp

    def add_forward_reference(self, node_id: str) -> None:
        """Add a forward reference to another node"""
        if node_id not in self.forward_references:
            self.forward_references.append(node_id)

    def add_backward_reference(self, node_id: str) -> None:
        """Add a backward reference from another node"""
        if node_id not in self.backward_references:
            self.backward_references.append(node_id)

    def add_dependency(self, node_id: str) -> None:
        """Add a dependency relationship"""
        if node_id not in self.dependencies:
            self.dependencies.append(node_id)
        # Also add to forward references for completeness
        if node_id not in self.forward_references:
            self.forward_references.append(node_id)

    def add_dependent(self, node_id: str) -> None:
        """Add a dependent relationship"""
        if node_id not in self.dependents:
            self.dependents.append(node_id)
        # Also add to backward references for completeness
        if node_id not in self.backward_references:
            self.backward_references.append(node_id)

    def add_related_node(self, node_id: str) -> None:
        """Add a related node (non-dependency relationship)"""
        if node_id not in self.related_nodes:
            self.related_nodes.append(node_id)
        # Also add to forward references
        if node_id not in self.forward_references:
            self.forward_references.append(node_id)