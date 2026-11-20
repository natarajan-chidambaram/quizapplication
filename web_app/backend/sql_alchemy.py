import enum
import os
# Both spellings are bound on purpose. Generated code uses the trailing-
# underscore aliases so a modelled class named List, Optional or DateTime
# cannot shadow them. The PLAIN names are imported too because this file is
# routinely edited afterwards by an LLM, which writes ordinary Python and has
# no reason to know about the aliasing convention; without the plain names
# such edits fail to import:
#
#     Mapped_[Optional[int]]        undefined name 'Optional'
#     mapped_column(DateTime())     undefined name 'DateTime'
#
# so every aliased name below is bound both ways.
from typing import List, Optional, List as List_, Optional as Optional_
from sqlalchemy import (
    create_engine, Enum, UniqueConstraint as _UniqueConstraint, event as _sa_event,
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, Interval,
    PickleType, String, Table, Text, Time,
    Column as Column_, ForeignKey as ForeignKey_, Table as Table_,
    Text as Text_, Boolean as Boolean_, String as String_, Date as Date_,
    Time as Time_, DateTime as DateTime_, Float as Float_, Integer as Integer_,
    Interval as Interval_, PickleType as PickleType_,
)
from sqlalchemy.orm import (
    column_property, DeclarativeBase, Mapped, Mapped as Mapped_, mapped_column,
    relationship
)
from datetime import datetime as dt_datetime, time as dt_time, date as dt_date, timedelta as dt_timedelta
from uuid import uuid4 as _uuid4


def _new_str_id() -> str:
    """Server-side surrogate for string primary keys named ``id``.

    A string PK has no autoincrement; without a default every INSERT dies
    on NOT NULL (the id is in nobody's hands: create schemas rightly
    exclude the server-owned ``id``, so the server must mint it).
    """
    return _uuid4().hex


def _configure_sqlite_engine(engine):
    """Enforce declared foreign keys on every SQLite connection."""
    if engine.dialect.name == "sqlite":
        @_sa_event.listens_for(engine, "connect")
        def _enable_foreign_keys(connection, _record):
            previous_autocommit = getattr(connection, "autocommit", None)
            if previous_autocommit is not None:
                connection.autocommit = True
            cursor = connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
            finally:
                cursor.close()
                if previous_autocommit is not None:
                    connection.autocommit = previous_autocommit


class Base(DeclarativeBase):
    pass



# Tables definition for many-to-many relationships

# Tables definition
class User(Base):
    __tablename__ = "user"
    id: Mapped_[str] = mapped_column(String_(100), primary_key=True, default=_new_str_id)
    username: Mapped_[str] = mapped_column(String_(100))
    displayName: Mapped_[str] = mapped_column(String_(100))
    email: Mapped_[str] = mapped_column(String_(100))
    role: Mapped_[Optional_[str]] = mapped_column(String_(100), nullable=True)
    createdAt: Mapped_[dt_datetime] = mapped_column(DateTime_, default=dt_datetime.now)

class QuizPage(Base):
    __tablename__ = "quizpage"
    id: Mapped_[str] = mapped_column(String_(100), primary_key=True, default=_new_str_id)
    quizId: Mapped_[str] = mapped_column(String_(100))
    pageNumber: Mapped_[int] = mapped_column(Integer_)
    questionId: Mapped_[str] = mapped_column(String_(100))
    layoutHint: Mapped_[Optional_[str]] = mapped_column(String_(100), nullable=True)
    isVisible: Mapped_[bool] = mapped_column(Boolean_)
    quizPageQuestion_id: Mapped_[str] = mapped_column(ForeignKey_("question.id"), unique=True)
    quizPageQuiz_id: Mapped_[str] = mapped_column(ForeignKey_("quiz.id"))

class Quiz(Base):
    __tablename__ = "quiz"
    id: Mapped_[str] = mapped_column(String_(100), primary_key=True, default=_new_str_id)
    title: Mapped_[str] = mapped_column(String_(100))
    description: Mapped_[str] = mapped_column(String_(100))
    createdByUserId: Mapped_[str] = mapped_column(String_(100))
    createdAt: Mapped_[dt_datetime] = mapped_column(DateTime_, default=dt_datetime.now)
    isPublished: Mapped_[bool] = mapped_column(Boolean_)

class Question(Base):
    __tablename__ = "question"
    id: Mapped_[str] = mapped_column(String_(100), primary_key=True, default=_new_str_id)
    quizId: Mapped_[str] = mapped_column(String_(100))
    text: Mapped_[str] = mapped_column(String_(100))
    instructions: Mapped_[str] = mapped_column(String_(100))
    questionType: Mapped_[str] = mapped_column(String_(100))
    points: Mapped_[Optional_[float]] = mapped_column(Float_, nullable=True)
    orderIndex: Mapped_[int] = mapped_column(Integer_)
    # Explanation extracted from the uploaded document (R18: shown in Learning Mode when present)
    explanation: Mapped_[Optional_[str]] = mapped_column(Text_, nullable=True)
    # Word-document extras (R5, R11-R13): optional difficulty tag and the audio
    # sentence read out loud for listening exercises (R26-R27).
    difficulty: Mapped_[Optional_[str]] = mapped_column(String_(100), nullable=True)
    audioSentence: Mapped_[Optional_[str]] = mapped_column(Text_, nullable=True)
    quiz_id: Mapped_[str] = mapped_column(ForeignKey_("quiz.id"))

class PDFDocument(Base):
    __tablename__ = "pdfdocument"
    id: Mapped_[str] = mapped_column(String_(100), primary_key=True, default=_new_str_id)
    fileName: Mapped_[str] = mapped_column(String_(100))
    contentType: Mapped_[str] = mapped_column(String_(100))
    fileSizeBytes: Mapped_[int] = mapped_column(Integer_)
    uploadDate: Mapped_[dt_datetime] = mapped_column(DateTime_)
    uploadedByUserId: Mapped_[str] = mapped_column(String_(100))
    storagePath: Mapped_[str] = mapped_column(String_(100))
    pDFDocumentQuiz_id: Mapped_[str] = mapped_column(ForeignKey_("quiz.id"), nullable=True)

class Option(Base):
    __tablename__ = "option"
    id: Mapped_[str] = mapped_column(String_(100), primary_key=True, default=_new_str_id)
    questionId: Mapped_[str] = mapped_column(String_(100))
    optionText: Mapped_[str] = mapped_column(String_(100))
    optionOrder: Mapped_[int] = mapped_column(Integer_)
    isCorrect: Mapped_[bool] = mapped_column(Boolean_)
    question_id: Mapped_[str] = mapped_column(ForeignKey_("question.id"))

class Attempt(Base):
    __tablename__ = "attempt"
    id: Mapped_[str] = mapped_column(String_(100), primary_key=True, default=_new_str_id)
    quizId: Mapped_[str] = mapped_column(String_(100))
    userId: Mapped_[str] = mapped_column(String_(100))
    startedAt: Mapped_[dt_datetime] = mapped_column(DateTime_)
    finishedAt: Mapped_[Optional_[dt_datetime]] = mapped_column(DateTime_, nullable=True)
    status: Mapped_[str] = mapped_column(String_(100))
    score: Mapped_[Optional_[float]] = mapped_column(Float_, nullable=True)
    # Quiz configuration (R8-R10): chosen on the Quiz Configuration screen
    mode: Mapped_[str] = mapped_column(String_(20), default="learning")
    questionOrder: Mapped_[str] = mapped_column(String_(20), default="sequential")
    requestedQuestionCount: Mapped_[int] = mapped_column(Integer_, default=0)
    # Word-document extras (R5, R11-R13): the configuration chosen at start
    selectedDifficulty: Mapped_[Optional_[str]] = mapped_column(String_(100), nullable=True)
    selectedQuestionType: Mapped_[Optional_[str]] = mapped_column(String_(20), nullable=True)
    # Timer option (R13, R29-R33): chosen on the Quiz Configuration screen
    timerEnabled: Mapped_[bool] = mapped_column(Boolean_, default=True)
    timerScope: Mapped_[str] = mapped_column(String_(20), default="per_question")
    timerDurationSeconds: Mapped_[int] = mapped_column(Integer_, default=60)
    # The ordered question subset selected for this session (R26: the session's question sequence)
    selectedQuestionIds: Mapped_[str] = mapped_column(Text_, default="")
    attemptQuiz_id: Mapped_[str] = mapped_column(ForeignKey_("quiz.id"))
    user_id: Mapped_[str] = mapped_column(ForeignKey_("user.id"))

class Response(Base):
    __tablename__ = "response"
    # A modeled identifier (or, when another association points here, a
    # surrogate id) is the primary key; the endpoint pair remains unique
    # because the generated relationship API addresses links by that pair.
    __table_args__ = (_UniqueConstraint("attemptQuestion_id", "attempts_id"),)
    attemptQuestion_id: Mapped_[str] = mapped_column(ForeignKey_("question.id"))
    attempts_id: Mapped_[str] = mapped_column(ForeignKey_("attempt.id"))
    option_id: Mapped_[Optional_[str]] = mapped_column(ForeignKey_("option.id"), nullable=True)
    id: Mapped_[str] = mapped_column(String_(100), primary_key=True, default=_new_str_id)
    attemptId: Mapped_[str] = mapped_column(String_(100))
    questionId: Mapped_[str] = mapped_column(String_(100))
    selectedOptionId: Mapped_[Optional_[str]] = mapped_column(String_(100), nullable=True)
    selectedOptionIds: Mapped_[str] = mapped_column(String_(100))
    answeredAt: Mapped_[dt_datetime] = mapped_column(DateTime_)
    isMarkedCorrect: Mapped_[Optional_[bool]] = mapped_column(Boolean_, nullable=True)


#--- Relationships of the user table
User.attempts: Mapped_[List_["Attempt"]] = relationship("Attempt", back_populates="user", foreign_keys=[Attempt.user_id])

#--- Relationships of the quizpage table

QuizPage.quizPageQuestion: Mapped_["Question"] = relationship("Question", back_populates="quizPage", uselist=False, foreign_keys=[QuizPage.quizPageQuestion_id])

QuizPage.quizPageQuiz: Mapped_["Quiz"] = relationship("Quiz", back_populates="pages", uselist=False, foreign_keys=[QuizPage.quizPageQuiz_id])

#--- Relationships of the quiz table
Quiz.attempts: Mapped_[List_["Attempt"]] = relationship("Attempt", back_populates="attemptQuiz", foreign_keys=[Attempt.attemptQuiz_id])
Quiz.documents: Mapped_[List_["PDFDocument"]] = relationship("PDFDocument", back_populates="pDFDocumentQuiz", foreign_keys=[PDFDocument.pDFDocumentQuiz_id])
Quiz.pages: Mapped_[List_["QuizPage"]] = relationship("QuizPage", back_populates="quizPageQuiz", foreign_keys=[QuizPage.quizPageQuiz_id], cascade="all, delete-orphan")
Quiz.questions: Mapped_[List_["Question"]] = relationship("Question", back_populates="quiz", foreign_keys=[Question.quiz_id], cascade="all, delete-orphan")
Question.options: Mapped_[List_["Option"]] = relationship("Option", back_populates="question", foreign_keys=[Option.question_id], cascade="all, delete-orphan")

Question.quiz: Mapped_["Quiz"] = relationship("Quiz", back_populates="questions", uselist=False, foreign_keys=[Question.quiz_id])

Question.quizPage: Mapped_["QuizPage"] = relationship("QuizPage", back_populates="quizPageQuestion", uselist=False, foreign_keys=[QuizPage.quizPageQuestion_id])

#--- Relationships of the pdfdocument table

PDFDocument.pDFDocumentQuiz: Mapped_["Quiz"] = relationship("Quiz", back_populates="documents", uselist=False, foreign_keys=[PDFDocument.pDFDocumentQuiz_id])

#--- Relationships of the option table

Option.question: Mapped_["Question"] = relationship("Question", back_populates="options", uselist=False, foreign_keys=[Option.question_id])
Option.responses: Mapped_[List_["Response"]] = relationship("Response", back_populates="option", foreign_keys=[Response.option_id])

Attempt.attemptQuiz: Mapped_["Quiz"] = relationship("Quiz", back_populates="attempts", uselist=False, foreign_keys=[Attempt.attemptQuiz_id])

Attempt.user: Mapped_["User"] = relationship("User", back_populates="attempts", uselist=False, foreign_keys=[Attempt.user_id])
#--- Relationships for association class Response
Response.attemptQuestion: Mapped_["Question"] = relationship("Question", back_populates="responses", foreign_keys=[Response.attemptQuestion_id])
Question.responses: Mapped_[List_["Response"]] = relationship("Response", back_populates="attemptQuestion", cascade="all, delete-orphan", foreign_keys=[Response.attemptQuestion_id])
Response.attempts: Mapped_["Attempt"] = relationship("Attempt", back_populates="responses", foreign_keys=[Response.attempts_id])
Attempt.responses: Mapped_[List_["Response"]] = relationship("Response", back_populates="attempts", cascade="all, delete-orphan", foreign_keys=[Response.attempts_id])
Attempt.attemptQuestion: Mapped_[List_["Question"]] = relationship("Question", secondary=Response.__table__, viewonly=True, primaryjoin=Attempt.id == Response.attempts_id, secondaryjoin=Question.id == Response.attemptQuestion_id)
Question.attempts: Mapped_[List_["Attempt"]] = relationship("Attempt", secondary=Response.__table__, viewonly=True, primaryjoin=Question.id == Response.attemptQuestion_id, secondaryjoin=Attempt.id == Response.attempts_id)

Response.option: Mapped_["Option"] = relationship("Option", back_populates="responses", uselist=False, foreign_keys=[Response.option_id])

# Database connection (override the default with the DATABASE_URL environment variable)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/Class_Diagram_3.db")  # SQLite connection
engine = create_engine(DATABASE_URL)
_configure_sqlite_engine(engine)

if __name__ == "__main__":
    # Create tables in the database only when this module is executed directly,
    # so importing it never touches the database as a side effect.
    if DATABASE_URL.startswith("sqlite"):
        os.makedirs("data", exist_ok=True)  # folder for the default SQLite database
    Base.metadata.create_all(engine, checkfirst=True)