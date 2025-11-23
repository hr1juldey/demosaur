"""
Intervention Manager - Handles mid-execution guidance.

Manages interventions from Claude during code generation.
Follows SRP: Intervention management only.
"""

from typing import Dict, List, Optional
from datetime import datetime


class InterventionManager:
    """Manages pending interventions"""

    def __init__(self):
        # task_id -> list of interventions
        self.interventions: Dict[str, List[Dict]] = {}

    def add_intervention(
        self,
        task_id: str,
        guidance: str
    ):
        """Add intervention for a task"""
        if task_id not in self.interventions:
            self.interventions[task_id] = []

        self.interventions[task_id].append({
            "guidance": guidance,
            "timestamp": datetime.utcnow().isoformat(),
            "applied": False
        })

    def get_pending(self, task_id: str) -> List[str]:
        """Get pending interventions for task"""
        if task_id not in self.interventions:
            return []

        return [
            i["guidance"]
            for i in self.interventions[task_id]
            if not i["applied"]
        ]

    def mark_applied(self, task_id: str):
        """Mark all interventions as applied"""
        if task_id in self.interventions:
            for i in self.interventions[task_id]:
                i["applied"] = True

    def clear(self, task_id: str):
        """Clear interventions for task"""
        if task_id in self.interventions:
            del self.interventions[task_id]


# Global intervention manager
_intervention_manager: Optional[InterventionManager] = None


def get_intervention_manager() -> InterventionManager:
    """Get global intervention manager"""
    global _intervention_manager
    if _intervention_manager is None:
        _intervention_manager = InterventionManager()
    return _intervention_manager


def add_intervention(task_id: str, guidance: str):
    """Add intervention (convenience function)"""
    manager = get_intervention_manager()
    manager.add_intervention(task_id, guidance)


def get_pending_interventions(task_id: str) -> List[str]:
    """Get pending interventions (convenience function)"""
    manager = get_intervention_manager()
    return manager.get_pending(task_id)


def mark_interventions_applied(task_id: str):
    """Mark interventions as applied (convenience function)"""
    manager = get_intervention_manager()
    manager.mark_applied(task_id)
