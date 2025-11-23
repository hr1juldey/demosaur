"""
Requirement gathering orchestrator.

Manages interactive Q&A process with Claude.
Follows SRP: Requirement gathering workflow only.
"""

from typing import Optional, Dict, Any
from dataclasses import asdict

from src.common.types import Requirements
from src.requirements.schema import (
    REQUIREMENT_QUESTIONS,
    get_next_question,
    Question
)
from src.requirements.validator import validate_answer, parse_answer


class RequirementGatherer:
    """Manages interactive requirement gathering process"""

    def __init__(self):
        self.current_question: Optional[Question] = None
        self.answers: Dict[str, Any] = {}
        self.is_complete: bool = False

    def start(self) -> Dict[str, Any]:
        """
        Start requirement gathering.

        Returns: Initial question info
        """
        self.current_question = REQUIREMENT_QUESTIONS[0]
        self.answers = {}
        self.is_complete = False

        return self._format_question(self.current_question)

    def answer(self, answer_text: str) -> Dict[str, Any]:
        """
        Process answer and get next question.

        Args:
            answer_text: User's answer

        Returns: Dict with status, next question, or completion
        """
        if self.is_complete:
            return {
                "status": "complete",
                "message": "Requirement gathering already complete"
            }

        if self.current_question is None:
            return {
                "status": "error",
                "message": "No active question. Call start() first"
            }

        # Validate answer
        is_valid, error_msg = validate_answer(
            answer_text,
            self.current_question.question_type
        )

        if not is_valid:
            return {
                "status": "invalid",
                "error": error_msg,
                "question": self._format_question(self.current_question)
            }

        # Parse and store answer
        parsed_answer = parse_answer(
            answer_text,
            self.current_question.question_type
        )
        self.answers[self.current_question.field_name] = parsed_answer

        # Get next question
        next_question = get_next_question(self.current_question.id)

        if next_question is None:
            # All questions answered
            self.is_complete = True
            requirements = self._build_requirements()

            return {
                "status": "complete",
                "requirements": asdict(requirements)
            }

        # Continue to next question
        self.current_question = next_question
        return {
            "status": "in_progress",
            "question": self._format_question(self.current_question),
            "progress": len(self.answers) / len(REQUIREMENT_QUESTIONS)
        }

    def _format_question(self, question: Question) -> Dict[str, Any]:
        """Format question for MCP response"""
        return {
            "id": question.id,
            "text": question.text,
            "type": question.question_type,
            "help": question.help_text,
            "examples": question.examples
        }

    def _build_requirements(self) -> Requirements:
        """Build Requirements object from answers"""
        return Requirements(
            goal=self.answers.get("goal", ""),
            approach=self.answers.get("approach", ""),
            technologies=self.answers.get("technologies", []),
            libraries=self.answers.get("libraries", {}),
            docs=self.answers.get("docs")
        )
