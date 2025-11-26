"""
Sentiment analysis service for customer emotions.
"""
from typing import Dict
from dataclasses import dataclass
from modules import SentimentAnalyzer
from config import config
from dspy_config import ensure_configured


@dataclass
class SentimentScores:
    """Container for sentiment scores."""
    interest: float
    anger: float
    disgust: float
    boredom: float
    neutral: float
    reasoning: str
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "interest": self.interest,
            "anger": self.anger,
            "disgust": self.disgust,
            "boredom": self.boredom,
            "neutral": self.neutral,
        }
    
    def should_proceed(self) -> bool:
        """Determine if conversation should proceed normally."""
        thresholds = config.SENTIMENT_THRESHOLDS["proceed"]
        
        # Don't proceed if negative emotions are too high
        if (self.anger >= thresholds["anger"] or
            self.disgust >= thresholds["disgust"] or
            self.boredom >= thresholds["boredom"]):
            return False
        
        # Proceed if interest is sufficient
        return self.interest >= thresholds["interest"]
    
    def needs_engagement(self) -> bool:
        """Check if customer needs more engagement."""
        return self.interest >= config.SENTIMENT_THRESHOLDS["engage"]["interest"]
    
    def should_disengage(self) -> bool:
        """Check if we should back off."""
        thresholds = config.SENTIMENT_THRESHOLDS["disengage"]
        return (self.anger >= thresholds["anger"] or
                self.disgust >= thresholds["disgust"] or
                self.boredom >= thresholds["boredom"])


class SentimentAnalysisService:
    """Service for analyzing customer sentiment."""
    
    def __init__(self):
        ensure_configured()
        self.analyzer = SentimentAnalyzer()
    
    def analyze(
        self,
        conversation_history: str,
        current_message: str
    ) -> SentimentScores:
        """Analyze sentiment from conversation."""
        try:
            result = self.analyzer(
                conversation_history=conversation_history,
                current_message=current_message
            )
            
            # Parse scores with fallback
            return SentimentScores(
                interest=self._parse_score(result.interest_score),
                anger=self._parse_score(result.anger_score),
                disgust=self._parse_score(result.disgust_score),
                boredom=self._parse_score(result.boredom_score),
                neutral=self._parse_score(result.neutral_score),
                reasoning=result.reasoning
            )
        except Exception as e:
            # Fallback to neutral sentiment
            return self._neutral_sentiment(str(e))
    
    @staticmethod
    def _parse_score(score_str: str) -> float:
        """Parse score from string, handling various formats."""
        try:
            # Extract first number from string
            import re
            numbers = re.findall(r'\d+\.?\d*', str(score_str))
            if numbers:
                score = float(numbers[0])
                return max(1.0, min(10.0, score))
        except (ValueError, IndexError):
            pass
        return 5.0  # Default neutral
    
    @staticmethod
    def _neutral_sentiment(error_msg: str = "") -> SentimentScores:
        """Return neutral sentiment as fallback."""
        return SentimentScores(
            interest=5.0,
            anger=1.0,
            disgust=1.0,
            boredom=3.0,
            neutral=7.0,
            reasoning=f"Fallback neutral sentiment. {error_msg}"
        )
