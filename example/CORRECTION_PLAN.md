# Correction Plan: Restructuring @example/ for DSPy ReAct + Templates

## Executive Summary

**Goal:** Implement intelligent decision-making layer using DSPy ReAct that decides:
- Whether to send template strings (rule-based CTA)
- Whether to have intelligent conversation (LLM-based empathy)
- Whether to combine both (optimal customer experience)

**Key Principle:** Let ReAct agent REASON about customer sentiment, context, and intent → Then DECIDE which tools to use

---

## Phase 1: Architecture Redesign

### Current Problems

**chatbot_orchestrator.py (506 lines - 2.8x bloat)**
- ❌ Repeats over-engineered state machine with manual transitions
- ❌ Artificial 3-second delays degrading UX
- ❌ Message chunking is premature optimization
- ❌ No intelligent reasoning before response decisions
- ❌ All responses go through LLM even when templates would be better

**data_extractor.py (942 lines - 6.7x bloat)**
- ❌ Strict Pydantic validation BLOCKS valid LLM outputs (BUGS_2 root cause)
- ❌ Violates DSPy-first principle (regex BEFORE proper LLM retry)
- ❌ Over-engineered caching with thread locks
- ❌ Complex normalization functions hide issues
- ❌ No graceful fallback when LLM extraction fails

### Solution Architecture

```
Customer Message
    ↓
Sentiment Analysis (Multi-dimensional: interest, anger, disgust, boredom, neutral)
    ↓
[DSPy ReAct Agent] ← REASONING LAYER
    │
    ├─ Reason about:
    │  ├─ Customer sentiment (should we push service? or just chat?)
    │  ├─ Message intent (booking? question? complaint?)
    │  ├─ Conversation state (what stage are we in?)
    │  └─ Context (have we already answered this?)
    │
    ├─ Decide to use tools:
    │  ├─ send_catalog_template → when customer asks about services
    │  ├─ send_pricing_template → when customer asks about costs
    │  ├─ send_booking_links → when customer wants to book
    │  ├─ answer_question → when customer needs clarification
    │  ├─ handle_complaint → when customer is angry/upset
    │  ├─ engage_conversation → when customer shows interest
    │  └─ extract_structured_data → when in data collection state
    │
    └─ Execute selected tools
        ↓
Final Response (template + chat, or just one)
```

---

## Phase 2: File-by-File Corrections

### 2.1 CHATBOT_ORCHESTRATOR.PY (506 → ~200 lines)

**Current Structure Issues:**
- Line 73-97: Keyword-based intent detection (basic)
- Line 99-147: LLM-based intent detection (unnecessary complexity)
- Line 193-212: Artificial response delays (DELETE)
- Line 214-253: Message chunking (DELETE)
- Line 171-191: Simulate human behavior (DELETE)

**New Structure:**

```python
"""
Simplified orchestrator using DSPy ReAct agent for intelligent decision-making.
"""
import dspy
from conversation_manager import ConversationManager
from sentiment_analyzer import SentimentAnalysisService
from data_extractor import DataExtractionService
from response_composer import ResponseComposer
from template_manager import TemplateManager

class ChatbotOrchestrator:
    """Coordinates ReAct agent for intelligent template + LLM decisions."""

    def __init__(self):
        self.conversation_manager = ConversationManager()
        self.sentiment_service = SentimentAnalysisService()
        self.data_extractor = DataExtractionService()
        self.response_composer = ResponseComposer()
        self.template_manager = TemplateManager()

        # ReAct agent for intelligent decision-making
        self.react_agent = dspy.ReAct(
            tools=[
                self._create_template_tool("catalog"),
                self._create_template_tool("pricing"),
                self._create_template_tool("booking"),
                self._create_extraction_tool("name"),
                self._create_extraction_tool("vehicle"),
                self._create_extraction_tool("date"),
                self._create_empathy_tool(),
            ]
        )

    def process_message(self, conversation_id, user_message, current_state):
        """Main entry point: Let ReAct agent reason and decide."""

        # 1. Add to conversation
        context = self.conversation_manager.add_user_message(conversation_id, user_message)
        history = self.conversation_manager.get_dspy_history(conversation_id)

        # 2. Analyze sentiment
        sentiment = self.sentiment_service.analyze(history, user_message)

        # 3. Let ReAct agent reason and decide
        reasoning = f"""
        Customer sentiment: Interest={sentiment.interest}, Anger={sentiment.anger}
        Current state: {current_state}
        Message: {user_message}

        Decide which tools to use and in what order.
        """

        agent_result = self.react_agent(
            query=reasoning,
            context={
                "sentiment": sentiment.to_dict(),
                "state": current_state,
                "message": user_message,
                "history": history
            }
        )

        # 4. Extract any structured data if needed
        extracted_data = self._extract_for_state(current_state, user_message, history)

        # 5. Compose response (agent decides template + LLM mix)
        response = self.response_composer.compose_response(
            user_message=user_message,
            llm_response=agent_result.get("llm_response", ""),
            sentiment_interest=sentiment.interest,
            sentiment_anger=sentiment.anger,
            current_state=current_state
        )

        return response

    def _create_template_tool(self, template_type):
        """Create a tool for sending templates."""
        @dspy.Tool
        def send_template(reason: str) -> str:
            f"""Send {template_type} template when appropriate."""
            return self.template_manager.get_template(template_type)
        return send_template

    def _create_extraction_tool(self, data_type):
        """Create a tool for data extraction."""
        @dspy.Tool
        def extract_data(user_message: str) -> dict:
            f"""Extract {data_type} data from user message."""
            # Use data extractor with lightweight validation
            return self.data_extractor.extract(data_type, user_message)
        return extract_data

    def _create_empathy_tool(self):
        """Create a tool for empathetic conversation."""
        @dspy.Tool
        def answer_empathetically(user_message: str, context: str) -> str:
            """Answer customer questions with empathy and understanding."""
            # Use LLM-based response generation
            return self._generate_empathetic_response(user_message, context)
        return answer_empathetically
```

**Key Changes:**
- ✅ Removed 300+ lines of bloat (delays, chunking, simulation)
- ✅ ReAct agent does ALL reasoning (no manual state machine)
- ✅ Tools defined clearly with docstrings
- ✅ Response composition delegated to ResponseComposer
- ✅ Sentiment drives all decisions
- ✅ No artificial delays or human behavior simulation

---

### 2.2 DATA_EXTRACTOR.PY (942 → ~250 lines)

**Current Structure Issues:**
- Lines 188-264: `_normalize_llm_name_output()` - 76 lines of over-engineering
- Lines 425-513: `_normalize_llm_vehicle_output()` - 88 lines of over-engineering
- Lines 687-754: `_normalize_llm_date_output()` - 68 lines of over-engineering
- Lines 26-41: Complex caching with thread locks (premature optimization)
- Lines 756-864: Complex preprocessing with Unicode handling (overkill)

**New Structure:**

```python
"""
Lean data extraction using DSPy with graceful fallbacks.
NOT validation-blocking, just structured extraction.
"""
import dspy
from typing import Optional
from datetime import datetime
from modules import NameExtractor, VehicleDetailsExtractor, DateParser
from models import ValidatedName, ValidatedVehicleDetails, ValidatedDate, ExtractionMetadata

class DataExtractionService:
    """Simple, DSPy-first extraction with lightweight fallbacks."""

    def __init__(self):
        self.name_extractor = NameExtractor()
        self.vehicle_extractor = VehicleDetailsExtractor()
        self.date_parser = DateParser()

    def extract_name(self, user_message: str, history: dspy.History = None) -> Optional[ValidatedName]:
        """Extract name: DSPy first, regex fallback only if needed."""

        try:
            # Primary: Try DSPy extraction
            history = history or dspy.History(messages=[])
            result = self.name_extractor(conversation_history=history, user_message=user_message)

            # Minimal normalization (just strip/lowercase check)
            first_name = str(result.first_name).strip()
            last_name = str(result.last_name).strip()

            if first_name and first_name.lower() not in ["none", "n/a", "unknown"]:
                return ValidatedName(
                    first_name=first_name,
                    last_name=last_name,
                    full_name=f"{first_name} {last_name}".strip(),
                    metadata=ExtractionMetadata(
                        confidence=0.9,
                        extraction_method="dspy",
                        extraction_source=user_message
                    )
                )
        except Exception:
            pass

        # Fallback: Simple regex only if DSPy fails
        import re
        match = re.search(r"i['\\s]*am\\s+(\\w+)|(my name is\\s+)(\\w+)", user_message, re.IGNORECASE)
        if match:
            name = match.group(1) or match.group(3)
            return ValidatedName(
                first_name=name.capitalize(),
                last_name="",
                full_name=name.capitalize(),
                metadata=ExtractionMetadata(
                    confidence=0.7,
                    extraction_method="regex",
                    extraction_source=user_message
                )
            )

        return None  # Let caller handle None gracefully

    def extract_vehicle_details(self, user_message: str, history: dspy.History = None) -> Optional[ValidatedVehicleDetails]:
        """Extract vehicle: DSPy first, regex fallback only if needed."""

        try:
            # Primary: Try DSPy extraction
            history = history or dspy.History(messages=[])
            result = self.vehicle_extractor(conversation_history=history, user_message=user_message)

            # Minimal normalization
            brand = str(result.brand).strip()
            model = str(result.model).strip()
            plate = str(result.number_plate).strip()

            if brand and brand.lower() not in ["none", "n/a", "unknown"]:
                return ValidatedVehicleDetails(
                    brand=brand,
                    model=model,
                    number_plate=plate,
                    metadata=ExtractionMetadata(
                        confidence=0.9,
                        extraction_method="dspy",
                        extraction_source=user_message
                    )
                )
        except Exception:
            pass

        # Fallback: Simple regex only if DSPy fails
        import re
        plate_match = re.search(r"[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{1,4}", user_message.upper())
        if plate_match:
            plate = plate_match.group()
            # Try to find brand
            brands = ["Honda", "Toyota", "Tata", "Maruti", "Mahindra"]
            brand = next((b for b in brands if b.lower() in user_message.lower()), "Unknown")

            return ValidatedVehicleDetails(
                brand=brand,
                model="Unknown",
                number_plate=plate,
                metadata=ExtractionMetadata(
                    confidence=0.7,
                    extraction_method="regex",
                    extraction_source=user_message
                )
            )

        return None

    def parse_date(self, user_message: str, history: dspy.History = None) -> Optional[ValidatedDate]:
        """Parse date: DSPy first, regex fallback only if needed."""

        try:
            # Primary: Try DSPy extraction
            history = history or dspy.History(messages=[])
            current_date = datetime.now().strftime("%Y-%m-%d")
            result = self.date_parser(
                conversation_history=history,
                user_message=user_message,
                current_date=current_date
            )

            date_str = str(result.parsed_date).strip()
            if date_str and date_str.lower() not in ["none", "unknown"]:
                return ValidatedDate(
                    date_str=date_str,
                    parsed_date=datetime.strptime(date_str, "%Y-%m-%d").date(),
                    confidence=0.9,
                    metadata=ExtractionMetadata(
                        confidence=0.9,
                        extraction_method="dspy",
                        extraction_source=user_message
                    )
                )
        except Exception:
            pass

        # Fallback: Simple date pattern regex only if DSPy fails
        import re
        patterns = [r'(\\d{4}-\\d{2}-\\d{2})', r'(\\d{2}/\\d{2}/\\d{4})']
        for pattern in patterns:
            match = re.search(pattern, user_message)
            if match:
                date_str = match.group(1)
                return ValidatedDate(
                    date_str=date_str,
                    parsed_date=datetime.strptime(date_str.replace('/', '-'), "%Y-%m-%d").date(),
                    confidence=0.7,
                    metadata=ExtractionMetadata(
                        confidence=0.7,
                        extraction_method="regex",
                        extraction_source=user_message
                    )
                )

        return None
```

**Key Changes:**
- ✅ 942 lines → ~250 lines (75% reduction)
- ✅ Removed ALL over-engineered normalization functions
- ✅ Removed caching with thread locks (premature optimization)
- ✅ Removed complex preprocessing with Unicode
- ✅ DSPy-FIRST principle: Try LLM, light fallback to regex ONLY if needed
- ✅ NO validation-blocking: returns None gracefully instead of raising
- ✅ Metadata tracking kept (good from @example/)

---

### 2.3 TEMPLATE_MANAGER.PY (Keep as-is) ✅

Already implemented correctly:
- Decides when to use templates vs LLM
- Considers sentiment and message intent
- No bloat, clean logic

---

### 2.4 RESPONSE_COMPOSER.PY (Keep as-is) ✅

Already implemented correctly:
- Combines LLM + templates intelligently
- Avoids "silent dumper" (all templates)
- Avoids "cheeky sales girl" (all chat)

---

## Phase 3: Integration Points

### ReAct Agent Decision Flow

```
ReAct Reasoning:
  IF customer_message matches ["catalog", "services", "menu"]:
      tool = send_catalog_template
  ELIF sentiment.anger > 6.0:
      tool = handle_complaint (empathy)
  ELIF sentiment.interest > 7.0:
      tool = [answer_question, send_pricing_template]  (both!)
  ELIF current_state == "NAME_COLLECTION":
      tool = extract_data("name")
  ELIF current_state == "GREETING":
      tool = engage_conversation
  ELSE:
      tool = answer_empathetically

ReAct Action:
  Execute selected tool(s) in order

ReAct Observation:
  Get result from tool execution

ReAct Response:
  Combine results into final response
```

---

## Phase 4: Testing Strategy

### Unit Tests Needed

```python
# test_react_agent.py
def test_react_decides_template_for_catalog_request():
    """When customer asks about services → send template"""

def test_react_decides_empathy_for_angry_customer():
    """When anger > 6.0 → use empathy tool, skip template"""

def test_react_combines_both_for_interested_customer():
    """When interest > 7.0 → send template + have conversation"""

def test_no_artificial_delays():
    """Verify response time < 500ms (no 3-second delays)"""

def test_dspy_first_extraction():
    """Verify LLM tries extraction before regex"""
```

---

## Phase 5: Rollout Plan

### Step 1: Replace chatbot_orchestrator.py
- ✅ Remove 300+ lines of bloat
- ✅ Implement ReAct-based decision layer
- ✅ Test with sentiment-driven decisions

### Step 2: Replace data_extractor.py
- ✅ Remove 700+ lines of over-engineered normalization
- ✅ Implement DSPy-first principle
- ✅ Test with graceful None returns (not exceptions)

### Step 3: Integrate ResponseComposer
- ✅ Use template_manager for template selection
- ✅ Let response_composer mix templates + LLM
- ✅ Test UX for both templates and conversation

### Step 4: End-to-End Testing
- ✅ Test sentiment-driven responses
- ✅ Test template vs conversation decisions
- ✅ Test combined (template + chat) responses
- ✅ Verify no artificial delays
- ✅ Verify DSPy extraction is attempted first

---

## Success Criteria

**Code Quality:**
- ✅ chatbot_orchestrator.py: < 300 lines (down from 506)
- ✅ data_extractor.py: < 300 lines (down from 942)
- ✅ NO artificial delays (remove 3-second waits)
- ✅ NO validation-blocking (return None gracefully)
- ✅ DSPy-first principle enforced

**User Experience:**
- ✅ ReAct reasons before responding (intelligent decisions)
- ✅ Angry customers get empathy, not templates
- ✅ Interested customers get templates + conversation
- ✅ Data collection states use extraction tools
- ✅ Response time < 500ms (no delays)

**Technical:**
- ✅ All 5 tests pass in test_llm_connection_fixed.py
- ✅ ReAct agent integrated and working
- ✅ Tools properly defined with docstrings
- ✅ Sentiment drives all decisions
- ✅ Templates managed by TemplateManager

---

## File Dependencies After Correction

```
chatbot_orchestrator.py (200 lines) ← NEW
  ├── conversation_manager.py ← existing
  ├── sentiment_analyzer.py ← existing
  ├── data_extractor.py (250 lines) ← NEW
  ├── response_composer.py ← existing
  ├── template_manager.py ← existing
  └── modules.py (114 lines) ← existing

data_extractor.py (250 lines) ← NEW
  ├── modules.py (114 lines)
  ├── models.py
  └── history_utils.py

response_composer.py ← existing
  ├── template_manager.py
  └── template_strings.py

template_manager.py ← existing (no dependencies)
template_strings.py ← existing (no dependencies)
```

---

## Timeline (Rough Estimate)

1. Rewrite chatbot_orchestrator.py: ~30 minutes
2. Rewrite data_extractor.py: ~30 minutes
3. Integration testing: ~30 minutes
4. End-to-end testing: ~20 minutes
5. **Total: ~110 minutes**

---

## Notes

- This plan follows QUICK_SUMMARY.txt recommendations
- Uses DSPy ReAct for intelligent reasoning
- Implements Tool-based architecture as learned
- Eliminates validation-blocking issues
- Achieves balance: templates + empathy + intelligence
- Removes all over-engineering and artificial features
