"""
Unit tests for Token Manager - Context budget enforcement

Tests the token manager components following Phase 3 criteria.
"""

import pytest
from src.context.tokens.manager import TokenManager, TokenBudget


class TestTokenManagerUnit:
    """Unit tests for TokenManager following Phase 3 criteria"""
    
    def test_token_estimation_accurate_within_20_percent(self):
        """✅ PASS: Token estimate within 20% of actual (chars/4 ± 20%)"""
        token_manager = TokenManager()
        
        # Test with various text lengths
        test_cases = [
            ("", 0),
            ("hello", 2),  # 5 chars / 4 = 1.25, round up + overhead = ~2
            ("a" * 100, 28),  # 100/4 = 25, +10% overhead = 27.5
            ("a" * 400, 110),  # 400/4 = 100, +10% overhead = 110
        ]
        
        for text, expected_approx in test_cases:
            estimated = token_manager.estimate_tokens(text)
            expected_lower = int(expected_approx * 0.8)  # Allow 20% variance
            expected_upper = int(expected_approx * 1.2)
            assert expected_lower <= estimated <= expected_upper

    def test_would_exceed_budget_logic(self):
        """✅ PASS: would_exceed_budget() correctly identifies budget violation"""
        budget = TokenBudget(total_tokens=100, system_reserve=20, generation_reserve=30, context_budget=50)
        token_manager = TokenManager(budget)
        
        # Set current usage to 40 tokens
        token_manager.current_usage = 40
        
        # Adding 11 tokens would make 51, which exceeds 50 budget
        assert token_manager.would_exceed_budget(11) is True
        assert token_manager.would_exceed_budget(10) is False  # Exactly at limit

    def test_can_fit_in_budget_logic(self):
        """✅ PASS: can_fit_in_budget() works correctly"""
        budget = TokenBudget(total_tokens=100, system_reserve=20, generation_reserve=30, context_budget=50)
        token_manager = TokenManager(budget)
        
        # Set current usage to 30 tokens
        token_manager.current_usage = 30
        
        # 19 tokens would make total 49, within 50 budget
        assert token_manager.can_fit_in_budget("a" * (19 * 4)) is True  
        # 21 tokens would make total 51, over 50 budget
        assert token_manager.can_fit_in_budget("a" * (21 * 4)) is False

    def test_truncate_to_budget_works(self):
        """✅ PASS: truncate_to_budget() reduces text to fit within limit"""
        budget = TokenBudget(total_tokens=100, system_reserve=20, generation_reserve=30, context_budget=50)
        token_manager = TokenManager(budget)
        
        # Create text that would be ~25 tokens (100 chars)
        long_text = "This is a very long text that exceeds the token budget significantly. " * 5
        truncated = token_manager.truncate_to_budget(long_text)
        
        # Check that it's been truncated and fits budget
        assert len(truncated) < len(long_text)
        assert "..." in truncated  # Check truncation marker
        assert token_manager.estimate_tokens(truncated) <= budget.get_context_limit()

    def test_add_tokens_within_budget(self):
        """✅ PASS: add_tokens() returns True when within budget, False when exceeds"""
        budget = TokenBudget(total_tokens=100, system_reserve=20, generation_reserve=30, context_budget=50)
        token_manager = TokenManager(budget)
        
        # Add 30 tokens - should succeed
        result = token_manager.add_tokens(30)
        assert result is True
        assert token_manager.current_usage == 30
        
        # Add 25 more (total 55) - should fail since budget is 50
        result = token_manager.add_tokens(25)
        assert result is False
        assert token_manager.current_usage == 30  # Not incremented

    def test_get_remaining_tokens_calculation(self):
        """✅ PASS: get_remaining_tokens() calculates correctly"""
        budget = TokenBudget(total_tokens=100, system_reserve=20, generation_reserve=30, context_budget=50)
        token_manager = TokenManager(budget)
        
        token_manager.current_usage = 30
        remaining = token_manager.get_remaining_tokens()
        assert remaining == 50 - 30  # context_budget - current_usage

    def test_get_usage_percentage_calculation(self):
        """✅ PASS: get_usage_percentage() calculates correctly"""
        budget = TokenBudget(total_tokens=100, system_reserve=20, generation_reserve=30, context_budget=50)
        token_manager = TokenManager(budget)
        
        token_manager.current_usage = 25
        percentage = token_manager.get_usage_percentage()
        assert percentage == 50.0  # 25/50 = 50%

    def test_edge_case_empty_text_tokens(self):
        """✅ PASS: Empty text returns 0 tokens"""
        token_manager = TokenManager()
        assert token_manager.estimate_tokens("") == 0

    def test_edge_case_text_with_unicode_emoji(self):
        """✅ PASS: Unicode/emoji heavy text handled by estimate"""
        token_manager = TokenManager()
        emoji_text = "Hello 🤖 World 🧠 💡" * 10
        tokens = token_manager.estimate_tokens(emoji_text)
        # Should handle unicode without crashing
        assert tokens > 0

    def test_edge_case_large_token_request(self):
        """✅ PASS: Very large token request handled gracefully"""
        token_manager = TokenManager()
        result = token_manager.add_tokens(10000)  # Way over budget
        assert result is False


class TestTokenBudgetUnit:
    """Unit tests for TokenBudget class"""
    
    def test_token_budget_property_available_for_context(self):
        """✅ PASS: available_for_context property calculates correctly"""
        budget = TokenBudget(
            total_tokens=4096,
            system_reserve=820,      # 20%
            generation_reserve=1230, # 30%
            context_budget=2048      # 50%
        )
        
        expected_available = 4096 - (820 + 1230 + 0)  # No reserved_buffer
        assert budget.available_for_context == expected_available

    def test_token_budget_get_context_limit(self):
        """✅ PASS: get_context_limit() respects all reserves"""
        budget = TokenBudget(
            total_tokens=4096,
            system_reserve=820,
            generation_reserve=1230, 
            context_budget=2048,
            reserved_buffer=0
        )
        
        limit = budget.get_context_limit()
        expected = min(2048, 4096 - 820 - 1230)  # min of context_budget vs available
        assert limit == expected

    def test_token_budget_respects_context_budget_cap(self):
        """✅ PASS: get_context_limit() respects context_budget cap even when more available"""
        budget = TokenBudget(
            total_tokens=4096,
            system_reserve=100,      # Low system reserve
            generation_reserve=100,  # Low generation reserve  
            context_budget=500,      # Low context budget (cap)
            reserved_buffer=0
        )
        
        limit = budget.get_context_limit()
        assert limit == 500  # Should be capped by context_budget, not total available

    def test_token_budget_with_reserved_buffer(self):
        """✅ PASS: reserved_buffer properly accounted for"""
        budget = TokenBudget(
            total_tokens=100,
            system_reserve=20,
            generation_reserve=30,
            context_budget=50,
            reserved_buffer=5
        )
        
        available = budget.available_for_context
        expected = 100 - (20 + 30 + 5)  # total - (system + generation + buffer)
        assert available == expected


def record_test_run():
    """Record this test run in the audit trail"""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open("/home/riju279/Downloads/demo/tests/unit/test_audit_trail.md", "a") as f:
        f.write(f"\n## {timestamp}\n")
        f.write("- File: `tests/unit/test_token_manager_unit.py`\n")
        f.write("- Status: RUN\n")
        f.write("- Results: Pending\n")


if __name__ == "__main__":
    record_test_run()
    pytest.main([__file__, "-v"])