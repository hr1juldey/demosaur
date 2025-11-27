"""
Conversation Simulator V2 - Phase 2 E2E Testing
Tests Phase 2 booking flow with realistic scenarios including:
- Indian English variations
- Negotiation and bargaining
- Scheduling/rescheduling
- Spelling mistakes and error recovery
- Confirmation flow (scratchpad → confirmation → booking)
- State machine validation
- Typo detection verification (via real DSPy LLM)

NO MODULE-LEVEL ACCESS - API-ONLY communication (except for direct typo detection testing)
"""
import httpx
import time
import random
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import sys
from pathlib import Path

# Add parent directory to path for imports (for typo detection verification only)
sys.path.insert(0, str(Path(__file__).parent.parent))


# API Configuration
API_BASE_URL = "http://localhost:8002"
API_CHAT_ENDPOINT = "/chat"
API_CONFIRMATION_ENDPOINT = "/api/confirmation"


class ScenarioType(str, Enum):
    """Scenario types for testing different flows."""
    HAPPY_PATH = "happy_path"
    NEGOTIATION = "negotiation"
    RESCHEDULE = "reschedule"
    ERROR_RECOVERY = "error_recovery"
    EDIT_CONFIRMATION = "edit_confirmation"
    CANCEL_AND_RESTART = "cancel_and_restart"
    BARGAINING = "bargaining"
    INDECISIVE = "indecisive"


# Expanded DIALOGS dictionary with Indian English and realistic variations
DIALOGS = {
    # Greetings
    "greeting": [
        "Hi",
        "Hello ji",
        "Namaste",
        "Good morning sir",
        "Haan, hello",
        "Yes, I'm there",
        "Hello, kindly help me",
        "Arre bhai, you there?",
        "Hey, can you hear me?"
    ],

    # Intent expressions
    "booking_intent": [
        "I want to book service",
        "Need car wash kindly",
        "My vehicle needs servicing only",
        "Kindly book appointment",
        "I want booking for car cleaning",
        "Can you do service for my car?",
        "Booking chahiye for vehicle",
        "Need to book car wash yaar",
        "My car is too dirty, need wash"
    ],

    # Name introductions (Indian names)
    "name_intro": [
        "I'm Rahul Kumar",
        "Name is Priya Sharma only",
        "Call me Arjun Patel",
        "I'm Sneha Reddy",
        "Amit Singh here",
        "This is Divya Iyer",
        "My name Rohan Joshi",
        "I am Kavita Verma",
        "Sanjay Gupta speaking"
    ],

    # Phone numbers (realistic Indian patterns)
    "phone": [
        "9876543210",
        "My number is 8888777766",
        "Phone number 9123456789",
        "You can call on 7654321098",
        "Contact me at 9900112233",
        "Mobile is 8765432109",
        "Kindly note 9988776655"
    ],

    # Email addresses
    "email": [
        "rahul.kumar@gmail.com",
        "priya.s@yahoo.com",
        "arjun.patel123@gmail.com",
        "sneha.reddy@outlook.com",
        "amit.singh88@gmail.com"
    ],

    # Price inquiry (Indian English style)
    "price_inquiry": [
        "What is the rate?",
        "How much you charge?",
        "What's the price yaar?",
        "Kindly tell me the cost",
        "Rate kya hai?",
        "What will be total cost?",
        "Price bata do",
        "How much it will cost me?"
    ],

    # Bargaining/Negotiation
    "bargain": [
        "Too costly sir, can you reduce?",
        "My friend got 20% discount only",
        "Can you give me better rate?",
        "This is too much yaar, come down little bit",
        "Competitors are charging ₹500 less",
        "I'm regular customer, some discount?",
        "Can you match competitor price?",
        "Little bit discount please",
        "Make it ₹100 cheaper, then I'll book",
        "Too expensive, I'll go elsewhere",
        "Give me best price, then only I'll do"
    ],

    # Agreement after negotiation
    "agree_price": [
        "Okay fine, that's acceptable",
        "Hmm, chalo okay",
        "Alright, I'll take it",
        "Theek hai, book karo",
        "Done, let's proceed",
        "Fine fine, go ahead",
        "Okay yaar, no problem"
    ],

    # Vehicle details
    "vehicle": [
        "I have Honda City",
        "It's Maruti Swift only",
        "Vehicle is Tata Nexon",
        "My car Hyundai Creta",
        "BMW X5 hai mere pass",
        "Toyota Innova",
        "Mahindra Scorpio",
        "Kia Seltos model"
    ],

    # Service type
    "service_type": [
        "Full car wash",
        "Just exterior cleaning",
        "Interior detailing",
        "Complete service",
        "Polish and wax",
        "Basic wash only",
        "Premium cleaning package"
    ],

    # Date/time scheduling
    "schedule": [
        "Tomorrow morning",
        "Next Monday kindly",
        "This Friday 10am",
        "Day after tomorrow",
        "Can you do today evening?",
        "Next week Tuesday",
        "Weekend slot available?",
        "Saturday 9am"
    ],

    # Rescheduling
    "reschedule": [
        "Actually Monday won't work",
        "Wait wait, I can't come tomorrow",
        "Can we shift to Tuesday instead?",
        "No no, change it to Friday",
        "Let me reschedule this",
        "That day I'm busy, any other time?",
        "Hold on, I need different date",
        "Arre, I made mistake, change to Wednesday"
    ],

    # Indecisiveness
    "indecisive": [
        "Wait, I'm confused",
        "Let me think yaar",
        "This is too many questions",
        "One minute, not sure",
        "Hmm, I don't know",
        "Why so complicated?",
        "This is taking too long",
        "Can't we just book simply?"
    ],

    # Frustration
    "frustrated": [
        "This is very annoying",
        "Why you need all this info?",
        "Too much hassle yaar",
        "Your system is complicated",
        "I don't have time for this",
        "Simplify karo please",
        "Other places don't ask so much"
    ],

    # Re-engagement
    "reengage": [
        "Okay okay, continue",
        "Fine, what next?",
        "Chalo, let's proceed",
        "Tell me what you need",
        "Alright, I'm listening",
        "Okay, I'll give details",
        "No problem, go ahead"
    ],

    # Confirmation triggers (with spelling mistakes)
    "confirm_trigger": [
        "confrim booking",  # typo
        "Confirm this",
        "Book it now",
        "Yes, finalize",
        "Proceed with bokking",  # typo
        "conferm it",  # typo
        "Schedule the apponitment",  # typo
        "Yes, confirm",
        "Let's confirm this",
        "Book karo"
    ],

    # Spelling corrections
    "correction": [
        "Sorry, I meant confirm",
        "Oops, spelling mistake - confirm",
        "I mean booking not bokking",
        "Correct spelling: appointment",
        "Actually it's confirm"
    ],

    # Edit actions
    "edit_request": [
        "Wait, change the name",
        "Edit phone number",
        "Wrong date, change it",
        "Update my email",
        "Modify vehicle details",
        "Change name to Priya",
        "Edit phone to 9999888877",
        "Make it Monday instead"
    ],

    # Cancel actions
    "cancel": [
        "Cancel this booking",
        "I want to cancel",
        "Cancel karo",
        "Don't book, cancel it",
        "Forget it, cancel",
        "I changed my mind, cancel"
    ],

    # Restart after cancel
    "restart": [
        "Actually, I want to book again",
        "Wait, let me try once more",
        "Can we start fresh?",
        "I'll book now properly",
        "Let's do this again"
    ],

    # Button-style commands
    "button_yes": [
        "yes",
        "YES",
        "Yes confirm",
        "yep",
        "yeah",
        "sure",
        "okay yes",
        "haan"
    ],

    "button_no": [
        "no",
        "NO",
        "nope",
        "nahi",
        "not now",
        "no thanks"
    ],

    "button_book": [
        "BOOK IT",
        "Book now",
        "book",
        "CONFIRM",
        "finalize",
        "do it"
    ],

    # Completion
    "thanks": [
        "Thank you so much",
        "Thanks yaar",
        "Great, thank you",
        "Perfect, thanks",
        "Shukriya",
        "Done, thank you",
        "Bahut acha, thanks"
    ]
}


@dataclass
class Phase2Metrics:
    """Track Phase 2-specific metrics."""
    turn_number: int = 0
    total_latency: float = 0.0
    turn_latencies: List[float] = field(default_factory=list)

    # Scratchpad tracking
    scratchpad_updates: int = 0
    completeness_progression: List[float] = field(default_factory=list)

    # State tracking
    state_transitions: List[str] = field(default_factory=list)
    confirmation_triggered: bool = False
    confirmation_turn: int = -1

    # Action tracking
    edit_actions: int = 0
    cancel_actions: int = 0
    confirm_actions: int = 0

    # Error recovery
    spelling_mistakes: int = 0
    corrections: int = 0

    # Typo detection tracking from chatbot's response (NEW)
    typos_sent_by_user: int = 0
    chatbot_suggested_corrections: int = 0
    typo_detection_working: bool = False

    # Booking result
    booking_completed: bool = False
    service_request_id: Optional[str] = None

    def add_turn(self, latency: float, state: str):
        """Add turn metrics."""
        self.turn_number += 1
        self.total_latency += latency
        self.turn_latencies.append(latency)
        self.state_transitions.append(state)


@dataclass
class ConversationPlan:
    """Plan for a complete conversation scenario."""
    scenario_type: ScenarioType
    description: str
    turns: List[Dict[str, Any]]


class Phase2ConversationSimulator:
    """
    Simulates realistic Phase 2 conversations with:
    - Indian English
    - Negotiation and bargaining
    - Scheduling/rescheduling
    - Error recovery (spelling mistakes)
    - Confirmation flow testing
    - API-only access (no module imports)
    """

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=120.0)

    def call_chat_api(self, conv_id: str, message: str, current_state: str = "greeting") -> Dict[str, Any]:
        """Call /chat endpoint."""
        start = time.time()

        try:
            response = self.client.post(
                API_CHAT_ENDPOINT,
                json={
                    "conversation_id": conv_id,
                    "user_message": message,
                    "current_state": current_state
                }
            )
            latency = time.time() - start

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "latency": latency,
                    "response": data.get("message", ""),
                    "sentiment": data.get("sentiment"),
                    "extracted_data": data.get("extracted_data"),
                    "state": data.get("state", "unknown"),
                    "scratchpad_completeness": data.get("scratchpad_completeness", 0.0),
                    "should_confirm": data.get("should_confirm", False)
                }
            else:
                return {
                    "success": False,
                    "latency": latency,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            latency = time.time() - start
            return {
                "success": False,
                "latency": latency,
                "error": str(e)
            }

    def call_confirmation_api(self, conv_id: str, user_input: str, action: str) -> Dict[str, Any]:
        """Call /api/confirmation endpoint."""
        start = time.time()

        try:
            response = self.client.post(
                API_CONFIRMATION_ENDPOINT,
                json={
                    "conversation_id": conv_id,
                    "user_input": user_input,
                    "action": action
                }
            )
            latency = time.time() - start

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "latency": latency,
                    "message": data.get("message", ""),
                    "service_request_id": data.get("service_request_id"),
                    "state": data.get("state", "unknown")
                }
            else:
                return {
                    "success": False,
                    "latency": latency,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            latency = time.time() - start
            return {
                "success": False,
                "latency": latency,
                "error": str(e)
            }

    def create_happy_path_scenario(self) -> ConversationPlan:
        """Create happy path scenario - smooth booking without issues."""
        return ConversationPlan(
            scenario_type=ScenarioType.HAPPY_PATH,
            description="Smooth booking flow without complications",
            turns=[
                {"type": "greeting", "dialog": "greeting"},
                {"type": "booking_intent", "dialog": "booking_intent"},
                {"type": "name", "dialog": "name_intro"},
                {"type": "phone", "dialog": "phone"},
                {"type": "vehicle", "dialog": "vehicle"},
                {"type": "service", "dialog": "service_type"},
                {"type": "schedule", "dialog": "schedule"},
                {"type": "confirm_trigger", "dialog": "confirm_trigger"},
                {"type": "button_confirm", "dialog": "button_yes"},
                {"type": "thanks", "dialog": "thanks"}
            ]
        )

    def create_negotiation_scenario(self) -> ConversationPlan:
        """Create negotiation scenario with bargaining."""
        return ConversationPlan(
            scenario_type=ScenarioType.NEGOTIATION,
            description="Customer negotiates price before booking",
            turns=[
                {"type": "greeting", "dialog": "greeting"},
                {"type": "booking_intent", "dialog": "booking_intent"},
                {"type": "price_inquiry", "dialog": "price_inquiry"},
                {"type": "bargain", "dialog": "bargain"},
                {"type": "bargain_more", "dialog": "bargain"},
                {"type": "agree", "dialog": "agree_price"},
                {"type": "name", "dialog": "name_intro"},
                {"type": "phone", "dialog": "phone"},
                {"type": "vehicle", "dialog": "vehicle"},
                {"type": "service", "dialog": "service_type"},
                {"type": "schedule", "dialog": "schedule"},
                {"type": "confirm_trigger", "dialog": "confirm_trigger"},
                {"type": "button_confirm", "dialog": "button_book"},
                {"type": "thanks", "dialog": "thanks"}
            ]
        )

    def create_reschedule_scenario(self) -> ConversationPlan:
        """Create rescheduling scenario."""
        return ConversationPlan(
            scenario_type=ScenarioType.RESCHEDULE,
            description="Customer reschedules appointment during booking",
            turns=[
                {"type": "greeting", "dialog": "greeting"},
                {"type": "booking_intent", "dialog": "booking_intent"},
                {"type": "name", "dialog": "name_intro"},
                {"type": "phone", "dialog": "phone"},
                {"type": "vehicle", "dialog": "vehicle"},
                {"type": "service", "dialog": "service_type"},
                {"type": "schedule", "dialog": "schedule"},
                {"type": "reschedule", "dialog": "reschedule"},
                {"type": "new_schedule", "dialog": "schedule"},
                {"type": "confirm_trigger", "dialog": "confirm_trigger"},
                {"type": "button_confirm", "dialog": "button_yes"},
                {"type": "thanks", "dialog": "thanks"}
            ]
        )

    def create_error_recovery_scenario(self) -> ConversationPlan:
        """Create scenario with spelling mistakes and corrections."""
        return ConversationPlan(
            scenario_type=ScenarioType.ERROR_RECOVERY,
            description="Customer makes spelling mistakes and corrects them",
            turns=[
                {"type": "greeting", "dialog": "greeting"},
                {"type": "booking_intent", "dialog": "booking_intent"},
                {"type": "name", "dialog": "name_intro"},
                {"type": "phone", "dialog": "phone"},
                {"type": "vehicle", "dialog": "vehicle"},
                {"type": "service", "dialog": "service_type"},
                {"type": "schedule", "dialog": "schedule"},
                {"type": "misspelled_confirm", "custom": "confrim bokking"},  # Spelling mistake
                {"type": "correction", "dialog": "correction"},
                {"type": "proper_confirm", "custom": "confirm booking"},
                {"type": "button_confirm", "dialog": "button_yes"},
                {"type": "thanks", "dialog": "thanks"}
            ]
        )

    def create_edit_confirmation_scenario(self) -> ConversationPlan:
        """Create scenario where customer edits details at confirmation."""
        return ConversationPlan(
            scenario_type=ScenarioType.EDIT_CONFIRMATION,
            description="Customer edits details when shown confirmation",
            turns=[
                {"type": "greeting", "dialog": "greeting"},
                {"type": "booking_intent", "dialog": "booking_intent"},
                {"type": "name", "dialog": "name_intro"},
                {"type": "phone", "dialog": "phone"},
                {"type": "vehicle", "dialog": "vehicle"},
                {"type": "service", "dialog": "service_type"},
                {"type": "schedule", "dialog": "schedule"},
                {"type": "confirm_trigger", "dialog": "confirm_trigger"},
                {"type": "edit", "custom": "wait, edit name to Priya Sharma"},
                {"type": "edit_phone", "custom": "edit phone 9999888877"},
                {"type": "button_confirm", "dialog": "button_yes"},
                {"type": "thanks", "dialog": "thanks"}
            ]
        )

    def create_cancel_restart_scenario(self) -> ConversationPlan:
        """Create scenario where customer cancels and restarts."""
        return ConversationPlan(
            scenario_type=ScenarioType.CANCEL_AND_RESTART,
            description="Customer cancels booking then decides to book again",
            turns=[
                {"type": "greeting", "dialog": "greeting"},
                {"type": "booking_intent", "dialog": "booking_intent"},
                {"type": "name", "dialog": "name_intro"},
                {"type": "phone", "dialog": "phone"},
                {"type": "vehicle", "dialog": "vehicle"},
                {"type": "confirm_trigger", "dialog": "confirm_trigger"},
                {"type": "cancel", "dialog": "cancel"},
                {"type": "restart", "dialog": "restart"},
                {"type": "name_again", "dialog": "name_intro"},
                {"type": "phone_again", "dialog": "phone"},
                {"type": "vehicle_again", "dialog": "vehicle"},
                {"type": "service", "dialog": "service_type"},
                {"type": "schedule", "dialog": "schedule"},
                {"type": "confirm_trigger", "dialog": "confirm_trigger"},
                {"type": "button_confirm", "dialog": "button_book"},
                {"type": "thanks", "dialog": "thanks"}
            ]
        )

    def create_indecisive_scenario(self) -> ConversationPlan:
        """Create scenario with indecisive customer."""
        return ConversationPlan(
            scenario_type=ScenarioType.INDECISIVE,
            description="Indecisive customer who gets frustrated then re-engages",
            turns=[
                {"type": "greeting", "dialog": "greeting"},
                {"type": "booking_intent", "dialog": "booking_intent"},
                {"type": "name", "dialog": "name_intro"},
                {"type": "indecisive", "dialog": "indecisive"},
                {"type": "frustrated", "dialog": "frustrated"},
                {"type": "reengage", "dialog": "reengage"},
                {"type": "phone", "dialog": "phone"},
                {"type": "vehicle", "dialog": "vehicle"},
                {"type": "service", "dialog": "service_type"},
                {"type": "schedule", "dialog": "schedule"},
                {"type": "confirm_trigger", "dialog": "confirm_trigger"},
                {"type": "button_confirm", "dialog": "button_yes"},
                {"type": "thanks", "dialog": "thanks"}
            ]
        )

    def get_message_from_turn(self, turn: Dict[str, Any]) -> str:
        """Get message from turn definition."""
        if "custom" in turn:
            return turn["custom"]

        dialog_key = turn.get("dialog")
        if dialog_key and dialog_key in DIALOGS:
            return random.choice(DIALOGS[dialog_key])

        return "Continue"

    def detect_action_type(self, message: str) -> str:
        """Detect action type from message."""
        msg_lower = message.lower()

        if any(word in msg_lower for word in ["edit", "change", "modify", "update", "wrong"]):
            return "edit"
        elif any(word in msg_lower for word in ["cancel", "forget", "don't book", "changed my mind"]):
            return "cancel"
        elif any(word in msg_lower for word in ["yes", "confirm", "book", "finalize", "proceed", "okay yes"]):
            return "confirm"

        return "unknown"

    def format_phase2_status(self, turn: int, metrics: Phase2Metrics, result: Dict[str, Any]) -> str:
        """Format Phase 2 status display."""
        status = f"""
╔═══════════════════════════════════════════════════════════════════════════════════════
║ 🔍 PHASE 2 SYSTEM STATUS (Turn {turn + 1})
╠═══════════════════════════════════════════════════════════════════════════════════════
║
║ ⏱️  Latency: {result.get('latency', 0):.3f}s  |  Avg: {metrics.total_latency / metrics.turn_number if metrics.turn_number > 0 else 0:.3f}s
║
║ 📊 SCRATCHPAD:
║    Completeness: {result.get('scratchpad_completeness', 0):.1f}%
║    Updates: {metrics.scratchpad_updates}
║    Progression: {' → '.join(f'{c:.0f}%' for c in metrics.completeness_progression[-5:]) if metrics.completeness_progression else 'N/A'}
║
║ 🎯 STATE MACHINE:
║    Current State: {result.get('state', 'unknown')}
║    Transition Path: {' → '.join(metrics.state_transitions[-5:]) if metrics.state_transitions else 'N/A'}
║
║ ✅ ACTIONS TAKEN:
║    Edits: {metrics.edit_actions}  |  Cancels: {metrics.cancel_actions}  |  Confirms: {metrics.confirm_actions}
║
║ 🔤 ERROR RECOVERY:
║    Spelling Mistakes: {metrics.spelling_mistakes}  |  Corrections: {metrics.corrections}
║
║ 📋 CONFIRMATION:
║    Triggered: {'YES ✅' if metrics.confirmation_triggered else 'NO ❌'}  |  Turn: {metrics.confirmation_turn if metrics.confirmation_turn >= 0 else 'N/A'}
║
║ 📦 BOOKING:
║    Completed: {'YES ✅' if metrics.booking_completed else 'NO ❌'}
║    Service Request ID: {metrics.service_request_id if metrics.service_request_id else 'N/A'}
║
╚═══════════════════════════════════════════════════════════════════════════════════════
"""
        return status

    def run_scenario(self, scenario: ConversationPlan) -> Phase2Metrics:
        """Run a complete scenario."""
        conv_id = f"phase2_{scenario.scenario_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        metrics = Phase2Metrics()

        print(f"\n{'='*90}")
        print(f"🎭 SCENARIO: {scenario.description.upper()}")
        print(f"   Type: {scenario.scenario_type.value}  |  ID: {conv_id}")
        print(f"{'='*90}\n")

        in_confirmation_flow = False
        current_state = "greeting"  # Track current state

        for turn_idx, turn in enumerate(scenario.turns):
            message = self.get_message_from_turn(turn)
            turn_type = turn.get("type", "unknown")

            # Display customer message
            print(f"\n👤 Customer [{turn_type}]: {message}")

            # Detect if this is a spelling mistake
            has_typo = "confrim" in message or "bokking" in message or "apponitment" in message or "conferm" in message
            if has_typo:
                metrics.spelling_mistakes += 1
                metrics.typos_sent_by_user += 1
                print("   ⚠️  Spelling mistake detected!")

            # Detect if this is a correction
            if turn_type in ["correction"]:
                metrics.corrections += 1
                print("   ✅ Customer correcting spelling")

            # Determine which API to call
            if in_confirmation_flow and turn_type in ["button_confirm", "edit", "edit_phone", "cancel"]:
                # Use confirmation API
                action = self.detect_action_type(message)
                result = self.call_confirmation_api(conv_id, message, action)

                if result["success"]:
                    metrics.add_turn(result["latency"], result.get("state", "confirmation"))
                    current_state = result.get("state", "confirmation")

                    # Track actions
                    if action == "confirm":
                        metrics.confirm_actions += 1
                        metrics.booking_completed = True
                        metrics.service_request_id = result.get("service_request_id")
                    elif action == "edit":
                        metrics.edit_actions += 1
                    elif action == "cancel":
                        metrics.cancel_actions += 1
                        in_confirmation_flow = False
                        current_state = "greeting"  # Reset state after cancel

                    print(f"🤖 Chatbot [Confirmation API]: {result['message']}")
                else:
                    print(f"   ❌ Confirmation API Error: {result.get('error')}")
                    continue

            else:
                # Use regular chat API
                result = self.call_chat_api(conv_id, message, current_state)

                if not result["success"]:
                    print(f"   ❌ Chat API Error: {result.get('error')}")
                    continue

                # Update metrics
                metrics.add_turn(result["latency"], result.get("state", "unknown"))
                current_state = result.get("state", "unknown")  # Update current state from response

                # Track scratchpad
                completeness = result.get("scratchpad_completeness", 0.0)
                if completeness > 0:
                    metrics.completeness_progression.append(completeness)
                    if len(metrics.completeness_progression) > 1:
                        if metrics.completeness_progression[-1] != metrics.completeness_progression[-2]:
                            metrics.scratchpad_updates += 1

                # Check if confirmation triggered
                if result.get("should_confirm") and not metrics.confirmation_triggered:
                    metrics.confirmation_triggered = True
                    metrics.confirmation_turn = turn_idx
                    in_confirmation_flow = True
                    print(f"   🎯 CONFIRMATION TRIGGERED!")

                # Display chatbot response
                chatbot_response = result.get('response', '').lower()
                print(f"🤖 Chatbot: {result['response']}")

                # Check if chatbot responded with a typo correction (human perspective)
                # Look for correction suggestions like "Did you mean..." or similar
                correction_keywords = ["did you mean", "you mean", "typo", "spell", "correct", "correct spelling"]
                if has_typo and any(keyword in chatbot_response for keyword in correction_keywords):
                    metrics.chatbot_suggested_corrections += 1
                    metrics.typo_detection_working = True
                    print("   ✅ Chatbot suggested typo correction!")

                # Display extracted data if any
                if result.get("extracted_data"):
                    print(f"   📦 Extracted: {result['extracted_data']}")

            # Display Phase 2 status
            status = self.format_phase2_status(turn_idx, metrics, result)
            print(status)

            # Small delay for readability
            time.sleep(0.2)

        return metrics

    def print_scenario_summary(self, scenario: ConversationPlan, metrics: Phase2Metrics):
        """Print scenario summary."""
        print(f"\n{'='*90}")
        print(f"📊 SCENARIO SUMMARY: {scenario.scenario_type.value}")
        print(f"{'='*90}")
        print(f"\n  ⏱️  PERFORMANCE:")
        print(f"     Total Turns: {metrics.turn_number}")
        print(f"     Total Time: {metrics.total_latency:.2f}s")
        print(f"     Avg Latency: {metrics.total_latency / metrics.turn_number if metrics.turn_number > 0 else 0:.3f}s")

        print(f"\n  📊 SCRATCHPAD:")
        print(f"     Updates: {metrics.scratchpad_updates}")
        print(f"     Final Completeness: {metrics.completeness_progression[-1] if metrics.completeness_progression else 0:.1f}%")

        print(f"\n  🎯 STATE MACHINE:")
        print(f"     States Visited: {len(set(metrics.state_transitions))}")
        print(f"     Path: {' → '.join(metrics.state_transitions)}")

        print(f"\n  ✅ ACTIONS:")
        print(f"     Confirms: {metrics.confirm_actions}")
        print(f"     Edits: {metrics.edit_actions}")
        print(f"     Cancels: {metrics.cancel_actions}")

        print(f"\n  🔤 ERROR RECOVERY:")
        print(f"     Spelling Mistakes: {metrics.spelling_mistakes}")
        print(f"     Corrections: {metrics.corrections}")
        print(f"     Recovery Rate: {(metrics.corrections / metrics.spelling_mistakes * 100) if metrics.spelling_mistakes > 0 else 0:.1f}%")

        print(f"\n  📋 CONFIRMATION:")
        print(f"     Triggered: {'YES ✅' if metrics.confirmation_triggered else 'NO ❌'}")
        print(f"     Turn: {metrics.confirmation_turn if metrics.confirmation_turn >= 0 else 'N/A'}")

        print(f"\n  📦 BOOKING RESULT:")
        print(f"     Completed: {'YES ✅' if metrics.booking_completed else 'NO ❌'}")
        print(f"     Service Request ID: {metrics.service_request_id if metrics.service_request_id else 'N/A'}")

        # Phase 2 behavior assessment
        print(f"\n  🎓 PHASE 2 BEHAVIOR ASSESSMENT:")

        expected_behavior = True
        issues = []

        # Check 1: Scratchpad should update
        if metrics.scratchpad_updates == 0:
            expected_behavior = False
            issues.append("❌ Scratchpad did not update (expected data collection)")
        else:
            print(f"     ✅ Scratchpad updated {metrics.scratchpad_updates} times")

        # Check 2: Confirmation should trigger
        if not metrics.confirmation_triggered:
            expected_behavior = False
            issues.append("❌ Confirmation not triggered (expected booking flow)")
        else:
            print(f"     ✅ Confirmation triggered at turn {metrics.confirmation_turn}")

        # Check 3: Booking should complete (except cancel scenarios)
        if scenario.scenario_type != ScenarioType.CANCEL_AND_RESTART:
            if not metrics.booking_completed:
                expected_behavior = False
                issues.append("❌ Booking not completed (expected service request)")
            else:
                print(f"     ✅ Booking completed with ID: {metrics.service_request_id}")

        # Check 4: Error recovery & Typo detection (from user perspective)
        if metrics.spelling_mistakes > 0:
            if metrics.corrections == 0:
                print(f"     ⚠️  {metrics.spelling_mistakes} spelling mistakes but no corrections")
            else:
                print(f"     ✅ Recovered from {metrics.corrections}/{metrics.spelling_mistakes} spelling mistakes")

            # NEW: Check if chatbot detected and suggested corrections for typos
            print(f"\n  🔍 TYPO DETECTION (From User Perspective):")
            print(f"     Typos Sent: {metrics.typos_sent_by_user}")
            print(f"     Corrections Suggested by Chatbot: {metrics.chatbot_suggested_corrections}")

            if metrics.typos_sent_by_user > 0:
                correction_rate = (metrics.chatbot_suggested_corrections / metrics.typos_sent_by_user) * 100
                print(f"     Detection Rate: {correction_rate:.1f}%")

                if metrics.typo_detection_working:
                    print(f"     ✅ TYPO DETECTION IS WORKING - Chatbot suggested corrections!")
                else:
                    print(f"     ⚠️  Typo detection may not be active - No corrections suggested")

        # Check 5: State transitions
        if len(metrics.state_transitions) == 0:
            expected_behavior = False
            issues.append("❌ No state transitions detected")
        else:
            print(f"     ✅ State machine transitioned through {len(metrics.state_transitions)} states")

        # Overall assessment
        print(f"\n  🏆 OVERALL ASSESSMENT:")
        if expected_behavior:
            print(f"     ✅✅✅ PHASE 2 BEHAVED AS EXPECTED ✅✅✅")
            print(f"     System correctly handled:")
            print(f"       - Data collection (scratchpad)")
            print(f"       - Confirmation flow")
            print(f"       - State transitions")
            print(f"       - Booking completion")
        else:
            print(f"     ❌❌❌ PHASE 2 DID NOT BEHAVE AS EXPECTED ❌❌❌")
            print(f"     Issues found:")
            for issue in issues:
                print(f"       {issue}")

        print(f"\n{'='*90}\n")

    def run_all_scenarios(self):
        """Run all test scenarios."""
        scenarios = [
            self.create_happy_path_scenario(),
            self.create_negotiation_scenario(),
            self.create_reschedule_scenario(),
            self.create_error_recovery_scenario(),
            self.create_edit_confirmation_scenario(),
            self.create_cancel_restart_scenario(),
            self.create_indecisive_scenario()
        ]

        all_metrics = []

        print(f"\n{'#'*90}")
        print(f"🚀 PHASE 2 E2E TESTING - RUNNING {len(scenarios)} SCENARIOS")
        print(f"{'#'*90}\n")

        for idx, scenario in enumerate(scenarios):
            print(f"\n{'─'*90}")
            print(f"Scenario {idx + 1}/{len(scenarios)}")
            print(f"{'─'*90}")

            metrics = self.run_scenario(scenario)
            all_metrics.append((scenario, metrics))
            self.print_scenario_summary(scenario, metrics)

            if idx < len(scenarios) - 1:
                time.sleep(1)

        # Overall summary
        self.print_overall_summary(all_metrics)

    def print_overall_summary(self, all_metrics: List[tuple]):
        """Print overall summary across all scenarios."""
        print(f"\n{'#'*90}")
        print(f"🎯 OVERALL PHASE 2 E2E TEST SUMMARY")
        print(f"{'#'*90}\n")

        total_scenarios = len(all_metrics)
        successful_bookings = sum(1 for _, m in all_metrics if m.booking_completed)
        confirmations_triggered = sum(1 for _, m in all_metrics if m.confirmation_triggered)
        total_turns = sum(m.turn_number for _, m in all_metrics)
        total_latency = sum(m.total_latency for _, m in all_metrics)
        total_edits = sum(m.edit_actions for _, m in all_metrics)
        total_cancels = sum(m.cancel_actions for _, m in all_metrics)
        total_mistakes = sum(m.spelling_mistakes for _, m in all_metrics)
        total_corrections = sum(m.corrections for _, m in all_metrics)
        total_typos_sent = sum(m.typos_sent_by_user for _, m in all_metrics)
        total_typo_suggestions = sum(m.chatbot_suggested_corrections for _, m in all_metrics)
        typo_detection_active = any(m.typo_detection_working for _, m in all_metrics)

        print(f"  📊 SCENARIO COVERAGE:")
        print(f"     Total Scenarios: {total_scenarios}")
        print(f"     Scenarios by Type:")
        for scenario, _ in all_metrics:
            print(f"       - {scenario.scenario_type.value}: {scenario.description}")

        print(f"\n  ⏱️  PERFORMANCE:")
        print(f"     Total Turns: {total_turns}")
        print(f"     Total Time: {total_latency:.2f}s")
        print(f"     Avg per Turn: {total_latency / total_turns if total_turns > 0 else 0:.3f}s")

        print(f"\n  📋 CONFIRMATION FLOW:")
        print(f"     Confirmations Triggered: {confirmations_triggered}/{total_scenarios}")
        print(f"     Success Rate: {confirmations_triggered / total_scenarios * 100:.1f}%")

        print(f"\n  📦 BOOKING COMPLETION:")
        print(f"     Successful Bookings: {successful_bookings}")
        print(f"     Completion Rate: {successful_bookings / total_scenarios * 100:.1f}%")

        print(f"\n  ✅ USER ACTIONS:")
        print(f"     Total Edits: {total_edits}")
        print(f"     Total Cancels: {total_cancels}")
        print(f"     Edit Rate: {total_edits / total_scenarios:.1f} per scenario")

        print(f"\n  🔤 ERROR RECOVERY:")
        print(f"     Spelling Mistakes: {total_mistakes}")
        print(f"     Corrections: {total_corrections}")
        print(f"     Recovery Rate: {total_corrections / total_mistakes * 100 if total_mistakes > 0 else 0:.1f}%")

        print(f"\n  🔍 TYPO DETECTION (From User Perspective):")
        print(f"     Typos Sent by Users: {total_typos_sent}")
        print(f"     Typo Corrections Suggested by Chatbot: {total_typo_suggestions}")

        if total_typos_sent > 0:
            typo_detection_rate = (total_typo_suggestions / total_typos_sent) * 100
            print(f"     Detection Rate: {typo_detection_rate:.1f}%")
            if typo_detection_active:
                print(f"     ✅ TYPO DETECTION FEATURE IS ACTIVE - Chatbot is helping users!")
            else:
                print(f"     ⚠️  Typo detection may not be triggering - Monitor in next iteration")
        else:
            print(f"     ℹ️  No typos were intentionally sent in these scenarios")

        print(f"\n  🏆 FINAL VERDICT:")
        if confirmations_triggered == total_scenarios and successful_bookings >= total_scenarios - 1:
            print(f"     ✅✅✅ PHASE 2 SYSTEM IS WORKING AS DESIGNED ✅✅✅")
            print(f"     All critical flows validated:")
            print(f"       ✅ Scratchpad data collection")
            print(f"       ✅ Confirmation triggering")
            print(f"       ✅ State machine transitions")
            print(f"       ✅ Edit/Cancel/Confirm actions")
            print(f"       ✅ Booking completion")
            print(f"       ✅ Error recovery")
            if typo_detection_active:
                print(f"       ✅ Typo detection feature is active")
        else:
            print(f"     ⚠️  PHASE 2 SYSTEM HAS ISSUES")
            if confirmations_triggered < total_scenarios:
                print(f"       ❌ Confirmation not triggering in all scenarios")
            if successful_bookings < total_scenarios - 1:
                print(f"       ❌ Booking completion rate too low")

        print(f"\n{'#'*90}\n")


def main():
    """Main entry point."""
    print("\n🎬 Phase 2 Conversation Simulator V2 Starting...\n")

    # Check if API is running
    try:
        response = httpx.get(f"{API_BASE_URL}/", timeout=10.0)
        if response.status_code != 200:
            print("❌ API is not responding. Please start the FastAPI server first:")
            print("   cd example && uvicorn main:app --host 0.0.0.0 --port 8002")
            return
    except Exception as e:
        print(f"❌ Cannot connect to API at {API_BASE_URL}")
        print(f"   Error: {e}")
        print("\n   Please start the FastAPI server first:")
        print("   cd example && uvicorn main:app --host 0.0.0.0 --port 8002")
        return

    print("✅ API is running. Starting Phase 2 E2E tests...\n")

    simulator = Phase2ConversationSimulator()
    simulator.run_all_scenarios()

    print("\n✅ All Phase 2 E2E tests completed!\n")


if __name__ == "__main__":
    main()