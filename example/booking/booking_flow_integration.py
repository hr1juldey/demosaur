"""BookingFlowManager: High-level orchestration of all Phase 2 components."""

from typing import Tuple, Optional
from booking.scratchpad import ScratchpadManager
from booking.confirmation import ConfirmationGenerator
from booking.booking_detector import BookingIntentDetector
from booking.confirmation_handler import ConfirmationHandler, ConfirmationAction
from booking.service_request import ServiceRequestBuilder, ServiceRequest
from booking.state_manager import BookingStateMachine, BookingState


class BookingFlowManager:
    """Orchestrates entire booking flow. Facade hiding Phase 2 complexity."""

    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.scratchpad = ScratchpadManager(conversation_id)
        self.state_machine = BookingStateMachine()
        self.handler = ConfirmationHandler(self.scratchpad)

    def process_for_booking(self, user_message: str, extracted_data: dict,
                           intent=None) -> Tuple[str, Optional[ServiceRequest]]:
        """
        Main entry point: process user message through booking flow.

        Returns:
            (response_message, service_request_if_confirmed or None)
        """
        # Step 1: Add extracted data to scratchpad
        self._add_extracted_data(extracted_data)

        # Step 2: Check if booking intent detected
        should_confirm = BookingIntentDetector.should_trigger_confirmation(
            user_message, intent, self.state_machine.get_current_state().value
        )

        if should_confirm and self.state_machine.get_current_state() != BookingState.CONFIRMATION:
            # Transition to confirmation
            self.state_machine.transition(BookingState.CONFIRMATION)
            summary = ConfirmationGenerator.generate_summary(self.scratchpad.form)
            return summary, None

        # Step 3: Handle confirmation actions (if in confirmation state)
        if self.state_machine.get_current_state() == BookingState.CONFIRMATION:
            action = self.handler.detect_action(user_message)

            if action == ConfirmationAction.CONFIRM:
                # Build service request and move to booking
                service_request = ServiceRequestBuilder.build(
                    self.scratchpad, self.conversation_id
                )
                self.state_machine.transition(BookingState.BOOKING)
                self.state_machine.transition(BookingState.COMPLETION)
                return (f"Booking confirmed! Reference: {service_request.service_request_id}",
                        service_request)

            elif action == ConfirmationAction.EDIT:
                # Update scratchpad and re-show form
                field_ref = self.handler.parse_edit_instruction(user_message)
                if field_ref:
                    # Extract value after field reference
                    parts = user_message.lower().split(field_ref, 1)
                    if len(parts) > 1:
                        new_value = parts[1].strip()
                        self.handler.handle_edit(f"{field_ref} {new_value}")
                summary = ConfirmationGenerator.generate_summary(self.scratchpad.form)
                return summary, None

            elif action == ConfirmationAction.CANCEL:
                # Cancel booking
                msg = self.handler.handle_cancel()
                self.state_machine.transition(BookingState.CANCELLED)
                self.state_machine.reset()
                return msg, None

        # Step 4: Continue data collection
        if self.state_machine.get_current_state() == BookingState.DATA_COLLECTION:
            completeness = self.scratchpad.get_completeness()
            return (f"Got it! We're {completeness}% done. "
                   f"Anything else you'd like to share?"), None

        # Default: acknowledge and continue
        completeness = self.scratchpad.get_completeness()
        return (f"Thanks! Data saved ({completeness}% complete). "
               f"Feel free to continue."), None

    def _add_extracted_data(self, extracted_data: dict) -> None:
        """Add extracted data to scratchpad."""
        if not extracted_data:
            return

        turn = len(self.scratchpad.form.metadata.get("turns", [])) + 1

        for key, value in extracted_data.items():
            if value is None:
                continue

            # Map extracted fields to scratchpad sections
            section_map = {
                "first_name": ("customer", "first_name"),
                "last_name": ("customer", "last_name"),
                "phone": ("customer", "phone"),
                "email": ("customer", "email"),
                "vehicle_brand": ("vehicle", "brand"),
                "vehicle_model": ("vehicle", "model"),
                "appointment_date": ("appointment", "date"),
                "service_type": ("appointment", "service_type"),
            }

            if key in section_map:
                section, field_name = section_map[key]
                self.scratchpad.add_field(
                    section, field_name, value,
                    source="direct_extraction",
                    turn=turn,
                    confidence=0.85
                )

    def get_scratchpad(self) -> ScratchpadManager:
        """Get current scratchpad."""
        return self.scratchpad

    def get_state(self) -> BookingState:
        """Get current booking state."""
        return self.state_machine.get_current_state()

    def is_complete(self) -> bool:
        """Check if booking is complete."""
        return self.state_machine.is_booking_complete()

    def reset(self) -> None:
        """Reset flow (for cancellation or new booking)."""
        self.scratchpad.clear_all()
        self.state_machine.reset()
