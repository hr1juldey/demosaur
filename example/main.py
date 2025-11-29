"""
FastAPI integration for the intelligent chatbot with graceful startup/shutdown.
"""
import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

from config import ConversationState
from orchestrator.message_processor import MessageProcessor
from dspy_config import dspy_configurator

# Backward compatibility: ChatbotOrchestrator is now MessageProcessor
ChatbotOrchestrator = MessageProcessor

# Configure logging to show application-level logs (not just ASGI traces)
logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
    },
    'handlers': {
        'default': {
            'formatter': 'default',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['default'],
    },
}

logging.config.dictConfig(logging_config)

logger = logging.getLogger("yawlit.chatbot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown logic lives here.
    - Configure global things (dspy).
    - Create/start orchestrator and attach to app.state.
    - On shutdown: call orchestrator.shutdown() and any dspy shutdown hooks.
    """
    # --- Startup ---
    logger.info("Starting lifespan: configuring DSPy and starting orchestrator...")
    # configure DSPy (synchronous or async depending on your code)
    dspy_configurator.configure()

    # create orchestrator and start any background tasks it needs
    orchestrator = ChatbotOrchestrator()
    # If your orchestrator has an async start method, await it; otherwise call start()
    if hasattr(orchestrator, "start") and callable(orchestrator.start):
        maybe_coro = orchestrator.start()
        if hasattr(maybe_coro, "__await__"):
            await maybe_coro

    # attach to app for endpoint access
    app.state.orchestrator = orchestrator
    app.state.dspy_configurator = dspy_configurator

    yield

    # --- Shutdown ---
    logger.info("Shutdown initiated: stopping orchestrator and DSPy...")
    try:
        orch = app.state.orchestrator
        # Prefer an async shutdown if available
        if hasattr(orch, "shutdown") and callable(orch.shutdown):
            maybe_coro = orch.shutdown()
            if hasattr(maybe_coro, "__await__"):
                await maybe_coro
        logger.info("Orchestrator shutdown completed.")
    except Exception as e:
        logger.exception("Error shutting down orchestrator: %s", e)

    # If your dspy_configurator exposes a shutdown/cleanup hook, call it
    try:
        if hasattr(dspy_configurator, "shutdown"):
            maybe_coro = dspy_configurator.shutdown()
            if hasattr(maybe_coro, "__await__"):
                await maybe_coro
            logger.info("DSPy configurator shutdown completed.")
    except Exception as e:
        logger.exception("Error shutting down dspy_configurator: %s", e)

    logger.info("Lifespan shutdown finished.")


# Initialize FastAPI with lifespan
app = FastAPI(
    title="Yawlit Intelligent Chatbot",
    description="DSPy-powered intelligent layer for car wash chatbot",
    version="1.0.0",
    lifespan=lifespan
)


# Pydantic models
class ChatRequest(BaseModel):
    conversation_id: str
    user_message: str
    current_state: Optional[str] = None  # DEPRECATED: State is now managed internally


class ChatResponse(BaseModel):
    message: str
    should_proceed: bool
    extracted_data: Optional[Dict[str, Any]] = None
    sentiment: Optional[Dict[str, float]] = None
    suggestions: Optional[Dict[str, Any]] = None
    should_confirm: bool = False
    scratchpad_completeness: float = 0.0
    state: str = "greeting"
    data_extracted: bool = False
    typo_corrections: Optional[Dict[str, str]] = None


class SentimentRequest(BaseModel):
    conversation_id: str
    user_message: str


class DataExtractionRequest(BaseModel):
    user_message: str
    extraction_type: str  # 'name', 'vehicle', 'date'


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Yawlit Intelligent Chatbot",
        "dspy_configured": getattr(app.state, "dspy_configurator", None) is not None
    }


def get_orchestrator(request: Request) -> ChatbotOrchestrator:
    orch = getattr(request.app.state, "orchestrator", None)
    if orch is None:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    return orch


@app.post("/chat", response_model=ChatResponse)
async def process_chat(request: ChatRequest, req: Request):
    try:
        orchestrator = get_orchestrator(req)

        # State is now managed internally by orchestrator
        # The current_state parameter is deprecated and ignored
        result = orchestrator.process_message(
            conversation_id=request.conversation_id,
            user_message=request.user_message
        )

        return ChatResponse(
            message=result.message,
            should_proceed=result.should_proceed,
            extracted_data=result.extracted_data,
            sentiment=result.sentiment,
            suggestions=result.suggestions,
            should_confirm=result.should_confirm,
            scratchpad_completeness=result.scratchpad_completeness,
            state=result.state,
            data_extracted=result.data_extracted,
            typo_corrections=result.typo_corrections
        )

    except Exception as e:
        logger.exception("Error processing chat: %s", e)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.post("/sentiment")
async def analyze_sentiment(request: SentimentRequest, req: Request):
    try:
        orchestrator = get_orchestrator(req)

        context = orchestrator.conversation_manager.get_or_create(
            request.conversation_id
        )

        history = context.get_history_text(max_messages=10)
        sentiment = orchestrator.sentiment_service.analyze(
            history,
            request.user_message
        )

        return {
            "sentiment": sentiment.to_dict() if hasattr(sentiment, 'to_dict') else vars(sentiment),
            "should_proceed": sentiment.should_proceed() if hasattr(sentiment, 'should_proceed') else True,
            "needs_engagement": sentiment.needs_engagement() if hasattr(sentiment, 'needs_engagement') else False,
            "should_disengage": sentiment.should_disengage() if hasattr(sentiment, 'should_disengage') else False,
            "reasoning": getattr(sentiment, 'reasoning', 'No reasoning available')
        }
    except Exception as e:
        logger.exception("Error analyzing sentiment: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract")
async def extract_data(request: DataExtractionRequest, req: Request):
    try:
        orchestrator = get_orchestrator(req)

        # Access data extractor through extraction_coordinator
        data_extractor = orchestrator.extraction_coordinator.data_extractor

        if request.extraction_type == "name":
            result = data_extractor.extract_name(request.user_message)
            return {"extracted": result.__dict__ if result else None}

        elif request.extraction_type == "vehicle":
            result = data_extractor.extract_vehicle_details(request.user_message)
            return {"extracted": result.__dict__ if result else None}

        elif request.extraction_type == "date":
            result = data_extractor.parse_date(request.user_message)
            return {"extracted": result.__dict__ if result else None}

        else:
            raise HTTPException(status_code=400, detail="Invalid extraction type")

    except Exception as e:
        logger.exception("Error extracting data: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/confirmation")
async def handle_confirmation(req: Request):
    """Handle user actions on confirmation screen (confirm/edit/cancel).

    CRITICAL FIX: Uses same ConversationManager as /chat endpoint to maintain unified state.
    This ensures that when user confirms via button, the state transitions to COMPLETED
    and next /chat message sees COMPLETED state, not stuck at CONFIRMATION.
    """
    from booking_orchestrator_bridge import BookingOrchestrationBridge

    try:
        # Parse JSON body
        body = await req.json()
        conversation_id = body.get("conversation_id")
        user_input = body.get("user_input")
        action = body.get("action")

        if not conversation_id or not user_input or not action:
            raise HTTPException(
                status_code=422,
                detail="Missing required fields: conversation_id, user_input, action"
            )

        # Get orchestrator from app state (same instance used by /chat endpoint)
        orchestrator = get_orchestrator(req)

        # Initialize bridge with SHARED ConversationManager from orchestrator
        # This ensures /chat and /api/confirmation both use the same state
        bridge = BookingOrchestrationBridge(
            conversation_manager=orchestrator.conversation_manager
        )
        bridge.initialize_booking(conversation_id)

        # Process through booking flow
        response_msg, service_request = bridge.process_booking_turn(
            user_input, {}, intent=None
        )

        return {
            "message": response_msg,
            "service_request_id": service_request.service_request_id
            if service_request else None,
            "state": bridge.get_booking_state(),
        }

    except Exception as e:
        logger.exception("Error handling confirmation: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    # In production prefer to run `uvicorn module:app --host 0.0.0.0 --port 8002 --workers 1`
    uvicorn.run("your_module_name:app", host="0.0.0.0", port=8002, log_level="info")
