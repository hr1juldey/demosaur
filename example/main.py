"""
FastAPI integration for the intelligent chatbot.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from config import ConversationState
from chatbot_orchestrator import ChatbotOrchestrator
from dspy_config import dspy_configurator


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    dspy_configurator.configure()
    yield
    # Shutdown (if needed)


# Initialize FastAPI
app = FastAPI(
    title="Yawlit Intelligent Chatbot",
    description="DSPy-powered intelligent layer for car wash chatbot",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize orchestrator
orchestrator = ChatbotOrchestrator()


# Pydantic models
class ChatRequest(BaseModel):
    conversation_id: str
    user_message: str
    current_state: str  # ConversationState value
    
    
class ChatResponse(BaseModel):
    message: str
    should_proceed: bool
    extracted_data: Optional[Dict[str, Any]] = None
    sentiment: Optional[Dict[str, float]] = None
    suggestions: Optional[Dict[str, Any]] = None


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
        "dspy_configured": dspy_configurator.is_configured
    }


@app.post("/chat", response_model=ChatResponse)
async def process_chat(request: ChatRequest):
    """
    Process chat message with intelligence layer.
    
    This endpoint adds sentiment analysis and data extraction
    on top of your existing rule-based flow.
    """
    try:
        # Convert state string to enum
        state = ConversationState(request.current_state)
        
        # Process message
        result = orchestrator.process_message(
            conversation_id=request.conversation_id,
            user_message=request.user_message,
            current_state=state
        )
        
        return ChatResponse(
            message=result.message,
            should_proceed=result.should_proceed,
            extracted_data=result.extracted_data,
            sentiment=result.sentiment,
            suggestions=result.suggestions
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid state: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.post("/sentiment")
async def analyze_sentiment(request: SentimentRequest):
    """Analyze sentiment for a user message."""
    try:
        context = orchestrator.conversation_manager.get_or_create(
            request.conversation_id
        )
        
        history = context.get_history_text(max_messages=10)
        sentiment = orchestrator.sentiment_service.analyze(
            history,
            request.user_message
        )
        
        return {
            "sentiment": sentiment.to_dict(),
            "should_proceed": sentiment.should_proceed(),
            "needs_engagement": sentiment.needs_engagement(),
            "should_disengage": sentiment.should_disengage(),
            "reasoning": sentiment.reasoning
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract")
async def extract_data(request: DataExtractionRequest):
    """Extract structured data from user message."""
    try:
        if request.extraction_type == "name":
            result = orchestrator.data_extractor.extract_name(request.user_message)
            return {"extracted": result.__dict__ if result else None}
        
        elif request.extraction_type == "vehicle":
            result = orchestrator.data_extractor.extract_vehicle_details(request.user_message)
            return {"extracted": result.__dict__ if result else None}
        
        elif request.extraction_type == "date":
            result = orchestrator.data_extractor.parse_date(request.user_message)
            return {"extracted": result.__dict__ if result else None}
        
        else:
            raise HTTPException(status_code=400, detail="Invalid extraction type")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
