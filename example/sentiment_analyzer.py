"""
Sentiment analysis service for customer emotions.
"""
from typing import Dict
from modules import SentimentAnalyzer
from config import config
from dspy_config import ensure_configured
from models import ValidatedSentimentScores, ExtractionMetadata


class SentimentAnalysisService:
    """Service for analyzing customer sentiment."""

    def __init__(self):
        ensure_configured()
        self.analyzer = SentimentAnalyzer()

    def analyze(
        self,
        conversation_history: str,
        current_message: str
    ) -> ValidatedSentimentScores:
        """Analyze sentiment from conversation."""
        try:
            result = self.analyzer(
                conversation_history=conversation_history,
                current_message=current_message
            )

            # Parse scores with fallback
            # Create validated sentiment scores object
            metadata = ExtractionMetadata(
                confidence=0.8,  # Default confidence for LLM analysis
                extraction_method="chain_of_thought",
                extraction_source=f"History: {conversation_history[:100]}... | Message: {current_message}"
            )

            validated_scores = ValidatedSentimentScores(
                interest=self._parse_score(result.interest_score),
                anger=self._parse_score(result.anger_score),
                disgust=self._parse_score(result.disgust_score),
                boredom=self._parse_score(result.boredom_score),
                neutral=self._parse_score(result.neutral_score),
                reasoning=result.reasoning,
                metadata=metadata
            )

            return validated_scores
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
    def _neutral_sentiment(error_msg: str = "") -> ValidatedSentimentScores:
        """Return neutral sentiment as fallback."""
        metadata = ExtractionMetadata(
            confidence=0.3,  # Low confidence for fallback
            extraction_method="fallback",
            extraction_source=error_msg
        )

        return ValidatedSentimentScores(
            interest=5.0,
            anger=1.0,
            disgust=1.0,
            boredom=3.0,
            neutral=7.0,
            reasoning=f"Fallback neutral sentiment. {error_msg}",
            metadata=metadata
        )
