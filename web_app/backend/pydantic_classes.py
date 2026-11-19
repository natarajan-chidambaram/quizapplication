from datetime import datetime, date, time
from typing import Any, List, Optional, Union, Set
from enum import Enum
from pydantic import BaseModel, field_validator
import re


############################################
# Enumerations are defined here
############################################

############################################
# Association-class link payloads
############################################

class ResponseLinkCreate(BaseModel):
    target: str  # primary key of the linked entity
    attemptId: str
    questionId: str
    selectedOptionId: Optional[str] = None
    selectedOptionIds: str
    answeredAt: datetime
    isMarkedCorrect: Optional[bool] = None

    @field_validator("selectedOptionIds")
    @classmethod
    def _single_answer(cls, v: str) -> str:
        """R13: one answer per question — at most one option id."""
        tokens = [token for token in re.split(r"[,;\s]+", str(v or "")) if token]
        if len(tokens) > 1:
            raise ValueError(
                "selectedOptionIds must contain exactly one option id "
                "(one answer per question is allowed)"
            )
        return tokens[0] if tokens else v

############################################
# Classes are defined here
############################################
class UserCreate(BaseModel):
    displayName: str
    email: str
    role: Optional[str] = None
    username: str
    attempts: Optional[List[str]] = None  # 1:N Relationship


class ResponseCreate(BaseModel):
    answeredAt: datetime
    attemptId: str
    isMarkedCorrect: Optional[bool] = None
    questionId: str
    selectedOptionId: Optional[str] = None
    selectedOptionIds: str
    attemptQuestion: str  # association end -> Question primary key
    attempts: str  # association end -> Attempt primary key
    option: Optional[str] = None  # N:1 Relationship (optional)

    @field_validator("selectedOptionIds")
    @classmethod
    def _single_answer(cls, v: str) -> str:
        """R13/R14: exactly one answer per question.

        selectedOptionIds must reference AT MOST ONE option id. A payload
        holding several option references (comma / semicolon / whitespace
        separated) is the reported Option-feature bug and is rejected with a
        validation error instead of being stored.
        """
        if v is None:
            return v
        tokens = [token for token in re.split(r"[,;\s]+", str(v)) if token]
        if len(tokens) > 1:
            raise ValueError(
                "selectedOptionIds must contain exactly one option id "
                "(one answer per question is allowed)"
            )
        return tokens[0] if tokens else v


class QuizPageCreate(BaseModel):
    isVisible: bool
    layoutHint: Optional[str] = None
    pageNumber: int
    questionId: str
    quizId: str
    quizPageQuestion: str  # 1:1 Relationship (mandatory)
    quizPageQuiz: str  # N:1 Relationship (mandatory)


class QuizCreate(BaseModel):
    createdByUserId: str
    description: str
    isPublished: bool
    title: str
    attempts: Optional[List[str]] = None  # 1:N Relationship
    documents: Optional[List[str]] = None  # 1:N Relationship
    questions: Optional[List[str]] = None  # 1:N Relationship
    pages: Optional[List[str]] = None  # 1:N Relationship


class QuestionCreate(BaseModel):
    instructions: str
    orderIndex: int
    points: Optional[float] = None
    questionType: str
    quizId: str
    text: str
    explanation: Optional[str] = None
    attempts: Optional[List[Union["ResponseLinkCreate", str]]] = None  # via association class (optional)
    options: Optional[List[str]] = None  # 1:N Relationship
    quiz: str  # N:1 Relationship (mandatory)


class PDFDocumentCreate(BaseModel):
    contentType: str
    fileName: str
    fileSizeBytes: int
    storagePath: str
    uploadDate: datetime
    uploadedByUserId: str
    pDFDocumentQuiz: Optional[str] = None  # N:1 Relationship (optional)


class OptionCreate(BaseModel):
    isCorrect: bool
    optionOrder: int
    optionText: str
    questionId: str
    responses: Optional[List[str]] = None  # 1:N Relationship
    question: str  # N:1 Relationship (mandatory)


class AttemptCreate(BaseModel):
    finishedAt: Optional[datetime] = None
    quizId: str
    score: Optional[float] = None
    startedAt: datetime
    status: str
    userId: str
    mode: Optional[str] = None
    questionOrder: Optional[str] = None
    requestedQuestionCount: Optional[int] = None
    attemptQuestion: Optional[List[Union["ResponseLinkCreate", str]]] = None  # via association class (optional)
    attemptQuiz: str  # N:1 Relationship (mandatory)
    user: str  # N:1 Relationship (mandatory)


class QuizStartCreate(BaseModel):
    """Quiz Configuration screen payload (R8-R11)."""
    documentId: str
    mode: str  # 'learning' | 'testing'
    questionOrder: str  # 'sequential' | 'random'
    questionCount: int

    @field_validator("mode")
    @classmethod
    def _mode_valid(cls, v: str) -> str:
        if v not in ("learning", "testing"):
            raise ValueError("mode must be 'learning' or 'testing'")
        return v

    @field_validator("questionOrder")
    @classmethod
    def _order_valid(cls, v: str) -> str:
        if v not in ("sequential", "random"):
            raise ValueError("questionOrder must be 'sequential' or 'random'")
        return v

    @field_validator("questionCount")
    @classmethod
    def _count_valid(cls, v: int) -> int:
        if v < 1:
            raise ValueError("questionCount must be at least 1")
        return v


class AnswerSubmitCreate(BaseModel):
    """One answer for one question of an attempt (R14-R15)."""
    questionId: str
    selectedOptionId: str


