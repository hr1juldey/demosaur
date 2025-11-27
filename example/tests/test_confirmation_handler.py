"""Tests for ConfirmationHandler."""

import pytest
from booking import ScratchpadManager, ConfirmationHandler, ConfirmationAction


class TestConfirmationHandler:
    """Test confirmation action handling."""

    def setup_method(self):
        """Setup for each test."""
        self.scratchpad = ScratchpadManager()
        self.handler = ConfirmationHandler(self.scratchpad)

    def test_detect_confirm_yes(self):
        """Test detecting confirm action."""
        action = self.handler.detect_action("yes")
        assert action == ConfirmationAction.CONFIRM

    def test_detect_confirm_variations(self):
        """Test various confirm phrases."""
        for phrase in ["correct", "proceed", "ok", "go"]:
            action = self.handler.detect_action(phrase)
            assert action == ConfirmationAction.CONFIRM

    def test_detect_cancel(self):
        """Test detecting cancel action."""
        action = self.handler.detect_action("cancel")
        assert action == ConfirmationAction.CANCEL

    def test_detect_cancel_variations(self):
        """Test various cancel phrases."""
        for phrase in ["no", "nevermind", "abort", "nope"]:
            action = self.handler.detect_action(phrase)
            assert action == ConfirmationAction.CANCEL

    def test_detect_edit(self):
        """Test detecting edit action."""
        action = self.handler.detect_action("edit name")
        assert action == ConfirmationAction.EDIT

    def test_detect_edit_variations(self):
        """Test various edit phrases."""
        for phrase in ["change date", "fix phone", "update email"]:
            action = self.handler.detect_action(phrase)
            assert action == ConfirmationAction.EDIT

    def test_handle_confirm(self):
        """Test confirm handler."""
        result = self.handler.handle_confirm()
        assert result is True

    def test_handle_edit_name(self):
        """Test editing name field."""
        self.scratchpad.add_field("customer", "first_name", "John", "direct", 1)
        result = self.handler.handle_edit("name Jane")
        assert result is not None
        assert result[0] == "customer"
        assert result[1] == "first_name"
        assert result[2] == "Jane"
        assert self.scratchpad.get_field("customer", "first_name").value == "Jane"

    def test_handle_edit_date(self):
        """Test editing date field."""
        result = self.handler.handle_edit("date 2024-12-25")
        assert result is not None
        assert result[0] == "appointment"
        assert result[2] == "2024-12-25"

    def test_handle_edit_phone(self):
        """Test editing phone field."""
        result = self.handler.handle_edit("phone 555-9999")
        assert result is not None
        assert result[0] == "customer"
        assert result[1] == "phone"

    def test_handle_edit_invalid_field(self):
        """Test editing invalid field."""
        result = self.handler.handle_edit("invalid_field value")
        assert result is None

    def test_handle_cancel(self):
        """Test cancel handler."""
        self.scratchpad.add_field("customer", "first_name", "John", "direct", 1)
        msg = self.handler.handle_cancel()
        assert "cancelled" in msg.lower()
        assert len(self.scratchpad.get_section("customer")) == 0

    def test_parse_edit_instruction_name(self):
        """Test parsing edit instruction."""
        field = self.handler.parse_edit_instruction("edit my name")
        assert field == "name"

    def test_parse_edit_instruction_phone(self):
        """Test parsing phone edit."""
        field = self.handler.parse_edit_instruction("change phone number")
        assert field == "phone"

    def test_parse_edit_instruction_date(self):
        """Test parsing date edit."""
        field = self.handler.parse_edit_instruction("fix appointment date")
        assert field == "date"

    def test_parse_edit_instruction_not_found(self):
        """Test parsing non-field edit."""
        field = self.handler.parse_edit_instruction("edit something")
        assert field is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
