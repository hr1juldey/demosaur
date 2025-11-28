"""
Scratchpad Coordinator - Manages scratchpad updates during data collection.

Single Responsibility: Update scratchpad based on extracted data and state.
Reason to change: Scratchpad update logic changes.
"""
import logging
from typing import Dict, Any
from config import ConversationState
from booking.scratchpad import ScratchpadManager

logger = logging.getLogger(__name__)


class ScratchpadCoordinator:
    """
    Coordinates scratchpad updates based on extracted data and conversation state.

    Follows Single Responsibility Principle (SRP):
    - Only handles scratchpad creation and updates
    - Does NOT handle data extraction or state transitions
    """

    def __init__(self):
        """Initialize scratchpad coordinator with manager storage."""
        self.scratchpad_managers: Dict[str, ScratchpadManager] = {}

    def get_or_create(self, conversation_id: str) -> ScratchpadManager:
        """
        Get existing scratchpad or create new one for conversation.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            ScratchpadManager instance
        """
        if conversation_id not in self.scratchpad_managers:
            self.scratchpad_managers[conversation_id] = ScratchpadManager(conversation_id)
        return self.scratchpad_managers[conversation_id]

    def update_from_extraction(
        self,
        scratchpad: ScratchpadManager,
        state: ConversationState,
        field_name: str,
        value: Any
    ) -> None:
        """
        Update scratchpad based on extracted data field and current state.

        Args:
            scratchpad: Scratchpad manager instance
            state: Current conversation state
            field_name: Name of extracted field
            value: Extracted value

        Note:
            Maps extracted fields to scratchpad sections based on state:
            - NAME_COLLECTION → customer section
            - VEHICLE_DETAILS → vehicle section
            - DATE_SELECTION → appointment section
        """
        # Map extracted fields to scratchpad sections
        if state == ConversationState.NAME_COLLECTION:
            section = "customer"
            # Map field names
            if field_name in ["first_name", "last_name", "full_name"]:
                scratchpad.add_field(section, field_name, value, "extraction", turn=0)

        elif state == ConversationState.VEHICLE_DETAILS:
            section = "vehicle"
            # Map vehicle fields
            field_mapping = {
                "vehicle_brand": "brand",
                "vehicle_model": "model",
                "vehicle_plate": "plate"
            }
            scratchpad_field = field_mapping.get(field_name, field_name)
            scratchpad.add_field(section, scratchpad_field, value, "extraction", turn=0)

        elif state == ConversationState.DATE_SELECTION:
            section = "appointment"
            field_mapping = {
                "appointment_date": "date"
            }
            scratchpad_field = field_mapping.get(field_name, field_name)
            scratchpad.add_field(section, scratchpad_field, value, "extraction", turn=0)