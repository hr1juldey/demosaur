"""
Question schemas for requirement gathering.

Defines the structure of questions asked to Claude.
Follows SRP: Question definition only.
"""

from dataclasses import dataclass
from typing import List, Optional, Literal


@dataclass
class Question:
    """Single question in requirement gathering"""
    id: str
    text: str
    field_name: str  # Maps to Requirements field
    question_type: Literal["text", "list", "dict", "optional"]
    help_text: Optional[str] = None
    examples: Optional[List[str]] = None


# Question sequence for requirement gathering
REQUIREMENT_QUESTIONS: List[Question] = [
    Question(
        id="goal",
        text="What do you want to achieve?",
        field_name="goal",
        question_type="text",
        help_text="Describe the main goal or feature you want to build",
        examples=[
            "Build a REST API for user management",
            "Create an email validation system",
            "Implement a caching layer for database queries"
        ]
    ),

    Question(
        id="approach",
        text="What's your algorithmic/architectural approach?",
        field_name="approach",
        question_type="text",
        help_text="Describe the high-level approach or algorithm",
        examples=[
            "Use regex for email validation with RFC 5322 compliance",
            "Event-driven architecture with pub/sub",
            "LRU cache with TTL expiration"
        ]
    ),

    Question(
        id="technologies",
        text="Which technologies/frameworks do you want to use?",
        field_name="technologies",
        question_type="list",
        help_text="Comma-separated list of technologies",
        examples=[
            "FastAPI, PostgreSQL, Redis",
            "Flask, SQLAlchemy, Celery",
            "Django, MySQL"
        ]
    ),

    Question(
        id="libraries",
        text="Which libraries and their specific features?",
        field_name="libraries",
        question_type="dict",
        help_text="Format: library: feature1, feature2",
        examples=[
            "FastAPI: dependency_injection, async_routes, websockets",
            "Pydantic: EmailStr, validators, BaseModel",
            "Redis: pub/sub, caching, rate_limiting"
        ]
    ),

    Question(
        id="docs",
        text="Any documentation URLs to reference? (optional)",
        field_name="docs",
        question_type="optional",
        help_text="URLs to official docs or references",
        examples=[
            "https://fastapi.tiangolo.com/tutorial/",
            "https://docs.pydantic.dev/"
        ]
    )
]


def get_question_by_id(question_id: str) -> Optional[Question]:
    """Get question by ID"""
    for q in REQUIREMENT_QUESTIONS:
        if q.id == question_id:
            return q
    return None


def get_next_question(current_id: Optional[str] = None) -> Optional[Question]:
    """Get next question in sequence"""
    if current_id is None:
        return REQUIREMENT_QUESTIONS[0]

    for i, q in enumerate(REQUIREMENT_QUESTIONS):
        if q.id == current_id and i < len(REQUIREMENT_QUESTIONS) - 1:
            return REQUIREMENT_QUESTIONS[i + 1]

    return None
