import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from pydantic_classes import *
from sql_alchemy import *
from database import get_db, integrity_error_detail
from bal_stdlib import *

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/attempt/", response_model=None, tags=["Attempt"])
def get_all_attempt(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(Attempt)
        query = query.options(joinedload(Attempt.attemptQuiz))
        query = query.options(joinedload(Attempt.user))
        attempt_list = query.all()

        # Serialize with relationships included
        result = []
        for db_attempt in attempt_list:
            item_dict = db_attempt.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)
            if db_attempt.attemptQuiz:
                related_obj = db_attempt.attemptQuiz
                related_dict = related_obj.__dict__.copy()
                related_dict.pop('_sa_instance_state', None)
                item_dict['attemptQuiz'] = related_dict
            else:
                item_dict['attemptQuiz'] = None
            if db_attempt.user:
                related_obj = db_attempt.user
                related_dict = related_obj.__dict__.copy()
                related_dict.pop('_sa_instance_state', None)
                item_dict['user'] = related_dict
            else:
                item_dict['user'] = None

            # Add association class links (target entities and the link rows themselves)
            attemptQuestion_link_rows = database.query(Response).filter(Response.attempts_id == db_attempt.id).all()
            item_dict['attemptQuestion_links'] = []
            for link_row in attemptQuestion_link_rows:
                link_dict = link_row.__dict__.copy()
                link_dict.pop('_sa_instance_state', None)
                item_dict['attemptQuestion_links'].append(link_dict)
            item_dict['attemptQuestion'] = []
            for related_question_obj in database.query(Question).filter(Question.id.in_([getattr(link_row, 'attemptQuestion_id') for link_row in attemptQuestion_link_rows])).all():
                related_question_dict = related_question_obj.__dict__.copy()
                related_question_dict.pop('_sa_instance_state', None)
                item_dict['attemptQuestion'].append(related_question_dict)

            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(Attempt).all()


@router.get("/attempt/count/", response_model=None, tags=["Attempt"])
def get_count_attempt(database: Session = Depends(get_db)) -> dict:
    """Get the total count of Attempt entities"""
    count = database.query(Attempt).count()
    return {"count": count}


@router.get("/attempt/paginated/", response_model=None, tags=["Attempt"])
def get_paginated_attempt(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of Attempt entities"""
    total = database.query(Attempt).count()
    attempt_list = database.query(Attempt).offset(skip).limit(limit).all()
    # By default, return flat entities (for charts/widgets)
    # Use detailed=true to get entities with relationships
    if not detailed:
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": attempt_list
        }

    result = []
    for db_attempt in attempt_list:
        attemptQuestion_ids = database.query(Response.attemptQuestion_id).filter(Response.attempts_id == db_attempt.id).all()
        item_data = {
            "attempt": db_attempt,
            "attemptQuestion_ids": [x[0] for x in attemptQuestion_ids],
        }
        result.append(item_data)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": result
    }
@router.get("/attempt/search/", response_model=None, tags=["Attempt"])
def search_attempt(
    id: str = None,
    quizId: str = None,
    score: float = None,
    status: str = None,
    userId: str = None,
    database: Session = Depends(get_db)
) -> list:
    """Search Attempt entities by attributes"""
    query = database.query(Attempt)

    if id is not None:
        query = query.filter(Attempt.id.ilike(f"%{id}%"))
    if quizId is not None:
        query = query.filter(Attempt.quizId.ilike(f"%{quizId}%"))
    if score is not None:
        query = query.filter(Attempt.score == score)
    if status is not None:
        query = query.filter(Attempt.status.ilike(f"%{status}%"))
    if userId is not None:
        query = query.filter(Attempt.userId.ilike(f"%{userId}%"))

    results = query.all()
    return results


@router.get("/attempt/{attempt_id}/", response_model=None, tags=["Attempt"])
async def get_attempt(attempt_id: str, database: Session = Depends(get_db)) -> Attempt:
    db_attempt = database.query(Attempt).filter(Attempt.id == attempt_id).first()
    if db_attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")

    attemptQuestion_ids = database.query(Response.attemptQuestion_id).filter(Response.attempts_id == db_attempt.id).all()
    response_data = {
        "attempt": db_attempt,
        "attemptQuestion_ids": [x[0] for x in attemptQuestion_ids],
}
    return response_data



@router.post("/attempt/", response_model=None, tags=["Attempt"])
async def create_attempt(attempt_data: AttemptCreate, database: Session = Depends(get_db)) -> Attempt:

    if attempt_data.attemptQuiz is not None:
        related_attemptQuiz = database.query(Quiz).filter(Quiz.id == attempt_data.attemptQuiz).first()
        if not related_attemptQuiz:
            raise HTTPException(status_code=400, detail="Quiz not found")
    else:
        raise HTTPException(status_code=400, detail="Quiz ID is required")
    if attempt_data.user is not None:
        related_user = database.query(User).filter(User.id == attempt_data.user).first()
        if not related_user:
            raise HTTPException(status_code=400, detail="User not found")
    else:
        raise HTTPException(status_code=400, detail="User ID is required")
    attemptQuestion_payload = getattr(attempt_data, 'attemptQuestion', None)
    if attemptQuestion_payload:
        for link in attemptQuestion_payload:
            attemptQuestion_target = link_target(link)
            related_question = database.query(Question).filter(Question.id == attemptQuestion_target).first()
            if not related_question:
                raise HTTPException(status_code=404, detail=f"Question with ID {attemptQuestion_target} not found")
            missing = [name for name in ['attemptId', 'questionId', 'selectedOptionIds', 'answeredAt'] if link_attrs(link, ['attemptId', 'questionId', 'selectedOptionIds', 'answeredAt']).get(name) is None]
            if missing:
                raise HTTPException(status_code=422, detail="Response requires " + ", ".join(missing))

    db_attempt = Attempt(
        finishedAt=attempt_data.finishedAt,        quizId=attempt_data.quizId,        score=attempt_data.score,        startedAt=attempt_data.startedAt,        status=attempt_data.status,        userId=attempt_data.userId,
        mode=attempt_data.mode if attempt_data.mode is not None else "learning",
        questionOrder=attempt_data.questionOrder if attempt_data.questionOrder is not None else "sequential",
        requestedQuestionCount=attempt_data.requestedQuestionCount if attempt_data.requestedQuestionCount is not None else 0,
        attemptQuiz_id=attempt_data.attemptQuiz,        user_id=attempt_data.user        )

    database.add(db_attempt)
    database.flush()
    database.refresh(db_attempt)



    if attemptQuestion_payload:
        for link in attemptQuestion_payload:
            database.add(Response(
                attempts_id=db_attempt.id,
                attemptQuestion_id=link_target(link),
                **link_attrs(link, ('answeredAt', 'attemptId', 'isMarkedCorrect', 'questionId', 'selectedOptionId', 'selectedOptionIds', ))
            ))
        database.flush()


    attemptQuestion_ids = database.query(Response.attemptQuestion_id).filter(Response.attempts_id == db_attempt.id).all()
    response_data = {
        "attempt": db_attempt,
        "attemptQuestion_ids": [x[0] for x in attemptQuestion_ids],
    }
    database.commit()
    database.refresh(db_attempt)
    return response_data


@router.post("/attempt/bulk/", response_model=None, tags=["Attempt"])
async def bulk_create_attempt(items: list[AttemptCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple Attempt entities at once"""
    if any(getattr(item, field, None) for item in items for field in ['attemptQuestion']):
        raise HTTPException(status_code=422, detail="Bulk creation of Attempt with relationships is not supported; use POST /attempt/ to validate and persist its relationships")
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item
            if not item_data.attemptQuiz:
                raise ValueError("Quiz ID is required")
            if not item_data.user:
                raise ValueError("User ID is required")

            db_attempt = Attempt(
                finishedAt=item_data.finishedAt,                quizId=item_data.quizId,                score=item_data.score,                startedAt=item_data.startedAt,                status=item_data.status,                userId=item_data.userId,                attemptQuiz_id=item_data.attemptQuiz,                user_id=item_data.user            )
            database.add(db_attempt)
            database.flush()  # Get ID without committing
            created_items.append(db_attempt.id)
        except ValueError as e:
            errors.append({"index": idx, "error": str(e)})
        except IntegrityError as e:
            # The driver's text goes to the log; a failed flush ends the session's work.
            logger.error("Bulk creation of Attempt failed at item %s: %s", idx, e)
            errors.append({"index": idx, "error": integrity_error_detail(e)})
            break

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} Attempt entities"
    }


@router.delete("/attempt/bulk/", response_model=None, tags=["Attempt"])
async def bulk_delete_attempt(ids: list[str], database: Session = Depends(get_db)) -> dict:
    """Delete multiple Attempt entities at once"""
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_attempt = database.query(Attempt).filter(Attempt.id == item_id).first()
        if db_attempt:
            conflict = attempt_delete_conflict(db_attempt)
            if conflict:
                raise HTTPException(status_code=409, detail="Cannot delete Attempt " + str(item_id) + ": " + conflict)
            database.delete(db_attempt)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} Attempt entities"
    }

@router.put("/attempt/{attempt_id}/", response_model=None, tags=["Attempt"])
async def update_attempt(attempt_id: str, attempt_data: AttemptCreate, database: Session = Depends(get_db)) -> Attempt:
    db_attempt = database.query(Attempt).filter(Attempt.id == attempt_id).first()
    if db_attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")

    setattr(db_attempt, 'finishedAt', attempt_data.finishedAt)
    setattr(db_attempt, 'quizId', attempt_data.quizId)
    setattr(db_attempt, 'score', attempt_data.score)
    setattr(db_attempt, 'startedAt', attempt_data.startedAt)
    setattr(db_attempt, 'status', attempt_data.status)
    setattr(db_attempt, 'userId', attempt_data.userId)
    if attempt_data.mode is not None:
        setattr(db_attempt, 'mode', attempt_data.mode)
    if attempt_data.questionOrder is not None:
        setattr(db_attempt, 'questionOrder', attempt_data.questionOrder)
    if attempt_data.requestedQuestionCount is not None:
        setattr(db_attempt, 'requestedQuestionCount', attempt_data.requestedQuestionCount)
    if attempt_data.attemptQuiz is not None:
        related_attemptQuiz = database.query(Quiz).filter(Quiz.id == attempt_data.attemptQuiz).first()
        if not related_attemptQuiz:
            raise HTTPException(status_code=400, detail="Quiz not found")
        setattr(db_attempt, 'attemptQuiz_id', attempt_data.attemptQuiz)
    if attempt_data.user is not None:
        related_user = database.query(User).filter(User.id == attempt_data.user).first()
        if not related_user:
            raise HTTPException(status_code=400, detail="User not found")
        setattr(db_attempt, 'user_id', attempt_data.user)
    attemptQuestion_payload = getattr(attempt_data, 'attemptQuestion', None)
    if attemptQuestion_payload is not None:
        existing_attemptQuestion_links = {getattr(link_row, 'attemptQuestion_id'): link_row for link_row in database.query(Response).filter(
            Response.attempts_id == db_attempt.id).all()}
        incoming_attemptQuestion_links = {}
        for link in attemptQuestion_payload:
            attemptQuestion_target = link_target(link)
            related_question = database.query(Question).filter(Question.id == attemptQuestion_target).first()
            if related_question is None:
                raise HTTPException(status_code=404, detail=f"Question with ID {attemptQuestion_target} not found")
            incoming_attemptQuestion_links[attemptQuestion_target] = link

        for attemptQuestion_target, link_row in existing_attemptQuestion_links.items():
            if attemptQuestion_target not in incoming_attemptQuestion_links:
                database.delete(link_row)

        for attemptQuestion_target, link in incoming_attemptQuestion_links.items():
            link_row = existing_attemptQuestion_links.get(attemptQuestion_target)
            if link_row is None:
                missing = [name for name in ['attemptId', 'questionId', 'selectedOptionIds', 'answeredAt'] if link_attrs(link, ['attemptId', 'questionId', 'selectedOptionIds', 'answeredAt']).get(name) is None]
                if missing:
                    raise HTTPException(status_code=422, detail="Response requires " + ", ".join(missing))
                database.add(Response(
                    attempts_id=db_attempt.id,
                    attemptQuestion_id=attemptQuestion_target,
                    **link_attrs(link, ('answeredAt', 'attemptId', 'isMarkedCorrect', 'questionId', 'selectedOptionId', 'selectedOptionIds', ))
                ))
            else:
                # R14: an already-given answer cannot be changed. Ignore link
                # attribute updates for an existing Response (the link row itself
                # was confirmed as wanted by the caller); only additions and
                # removals are honoured.
                pass
    database.commit()
    database.refresh(db_attempt)

    attemptQuestion_ids = database.query(Response.attemptQuestion_id).filter(Response.attempts_id == db_attempt.id).all()
    response_data = {
        "attempt": db_attempt,
        "attemptQuestion_ids": [x[0] for x in attemptQuestion_ids],
    }
    return response_data


def attempt_delete_conflict(db_attempt, deleting=None, wholes=()):
    """Why this Attempt cannot be deleted (None when it can): a related record
    would be left without a link it requires. Covers the parts deleted with it;
    ``deleting`` holds every record of the delete, since none of them can block it,
    and ``wholes`` the records on the way down to this part."""
    if deleting is None:
        state = sa_inspect(db_attempt)
        deleting = [db_attempt] + [item[0] for item in state.mapper.cascade_iterator("delete", state)]
    return None


@router.delete("/attempt/{attempt_id}/", response_model=None, tags=["Attempt"])
async def delete_attempt(attempt_id: str, database: Session = Depends(get_db)):
    db_attempt = database.query(Attempt).filter(Attempt.id == attempt_id).first()
    if db_attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    conflict = attempt_delete_conflict(db_attempt)
    if conflict:
        raise HTTPException(status_code=409, detail="Cannot delete Attempt " + str(attempt_id) + ": " + conflict)
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_attempt = {
        attr.key: getattr(db_attempt, attr.key)
        for attr in db_attempt.__mapper__.column_attrs
    }
    database.delete(db_attempt)
    database.commit()
    return deleted_attempt

@router.post("/attempt/{attempt_id}/attemptQuestion/{question_id}/", response_model=None, tags=["Attempt Relationships"])
async def add_attemptQuestion_to_attempt(attempt_id: str, question_id: str, link: dict = Body(default=None), database: Session = Depends(get_db)):
    """Add a Question to this Attempt's attemptQuestion relationship.

    The request body carries the Response attributes (answeredAt, attemptId, isMarkedCorrect, questionId, selectedOptionId, selectedOptionIds).
    A `target` field in the body is ignored: the target is taken from the path.
    """
    db_attempt = database.query(Attempt).filter(Attempt.id == attempt_id).first()
    if db_attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")

    related_question = database.query(Question).filter(Question.id == question_id).first()
    if related_question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    # Check if relationship already exists
    existing = database.query(Response).filter(
        (Response.attempts_id == attempt_id) &
        (Response.attemptQuestion_id == question_id)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Relationship already exists")
    missing = [name for name in ['attemptId', 'questionId', 'selectedOptionIds', 'answeredAt'] if link_attrs(link, ['attemptId', 'questionId', 'selectedOptionIds', 'answeredAt']).get(name) is None]
    if missing:
        raise HTTPException(status_code=422, detail="Response requires " + ", ".join(missing))

    # Create the association class row
    database.add(Response(
        attempts_id=attempt_id,
        attemptQuestion_id=question_id,
        **link_attrs(link, ('answeredAt', 'attemptId', 'isMarkedCorrect', 'questionId', 'selectedOptionId', 'selectedOptionIds', ))
    ))
    database.commit()

    return {"message": "Question added to attemptQuestion successfully"}


@router.delete("/attempt/{attempt_id}/attemptQuestion/{question_id}/", response_model=None, tags=["Attempt Relationships"])
async def remove_attemptQuestion_from_attempt(attempt_id: str, question_id: str, database: Session = Depends(get_db)):
    """Remove a Question from this Attempt's attemptQuestion relationship"""
    db_attempt = database.query(Attempt).filter(Attempt.id == attempt_id).first()
    if db_attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")

    # Check if relationship exists
    existing = database.query(Response).filter(
        (Response.attempts_id == attempt_id) &
        (Response.attemptQuestion_id == question_id)
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Relationship not found")


    # Delete the association class row
    database.delete(existing)
    database.commit()

    return {"message": "Question removed from attemptQuestion successfully"}


@router.get("/attempt/{attempt_id}/attemptQuestion/", response_model=None, tags=["Attempt Relationships"])
async def get_attemptQuestion_of_attempt(attempt_id: str, database: Session = Depends(get_db)):
    """Get all Question entities related to this Attempt through attemptQuestion, with their Response links"""
    db_attempt = database.query(Attempt).filter(Attempt.id == attempt_id).first()
    if db_attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")

    attemptQuestion_link_rows = database.query(Response).filter(Response.attempts_id == attempt_id).all()
    question_list = database.query(Question).filter(Question.id.in_(
        [getattr(link_row, 'attemptQuestion_id') for link_row in attemptQuestion_link_rows])).all()

    return {
        "attempt_id": attempt_id,
        "attemptQuestion_count": len(question_list),
        "attemptQuestion": question_list,
        "attemptQuestion_links": attemptQuestion_link_rows
    }


############################################
# Document-based quiz workflow (R6, R9-R24)
############################################

import json as _json
import random as _random
from datetime import datetime as _datetime
from pydantic_classes import QuizStartCreate, AnswerSubmitCreate
from quiz_workflow import (
    get_or_create_quiz_user,
    load_question_ids,
    select_questions,
)


@router.post("/attempt/start/", response_model=None, tags=["Attempt"])
async def start_quiz(config: QuizStartCreate, database: Session = Depends(get_db)):
    """Start a quiz session from an uploaded document (R6, R9-R11).

    Creates the Attempt (mode, order, question count) and selects the
    question subset in sequential or random order for the session.
    """
    document = database.query(PDFDocument).filter(PDFDocument.id == config.documentId).first()
    if document is None:
        raise HTTPException(status_code=404, detail=f"Uploaded document with ID {config.documentId} not found")
    if document.pDFDocumentQuiz_id is None:
        raise HTTPException(status_code=422, detail="This document has no extracted questions")

    available = (
        database.query(Question)
        .filter(Question.quiz_id == document.pDFDocumentQuiz_id)
        .count()
    )
    if available == 0:
        raise HTTPException(status_code=422, detail="This document has no extracted questions")

    # R10: questionCount may be None (not provided) -- default it to all
    # available questions instead of comparing None > int (TypeError).
    requested = (
        config.questionCount
        if config.questionCount is not None and config.questionCount > 0
        else available
    )
    # R11: requesting more than the document has must not crash -- clamp the
    # selection to all available questions and proceed with the quiz.
    selected_count = min(requested, available)

    selected = select_questions(
        database,
        document.pDFDocumentQuiz_id,
        config.questionOrder,
        selected_count,
        difficulty=config.difficulty,
        question_type=config.questionType,
    )
    if not selected:
        raise HTTPException(
            status_code=422,
            detail=(
                "No questions match the selected filters"
                + (f" (difficulty: {config.difficulty})" if config.difficulty else "")
                + (f" (type: audio)" if config.questionType == "audio" else "")
                + " — choose different settings or upload another document"
            ),
        )
    user = get_or_create_quiz_user(database)

    db_attempt = Attempt(
        quizId=document.pDFDocumentQuiz_id,
        userId=user.id,
        startedAt=_datetime.now(),
        status="in_progress",
        mode=config.mode,
        questionOrder=config.questionOrder,
        requestedQuestionCount=selected_count,
        selectedDifficulty=config.difficulty,
        selectedQuestionType=config.questionType,
        timerEnabled=config.timerEnabled,
        timerScope=config.timerScope,
        timerDurationSeconds=config.timerDurationSeconds,
        selectedQuestionIds=_json.dumps([question.id for question in selected]),
        attemptQuiz_id=document.pDFDocumentQuiz_id,
        user_id=user.id,
    )
    database.add(db_attempt)
    database.commit()
    database.refresh(db_attempt)

    return {
        "attempt": db_attempt,
        "documentId": document.id,
        "documentName": document.fileName,
        "mode": db_attempt.mode,
        "questionOrder": db_attempt.questionOrder,
        "questionIds": [question.id for question in selected],
        "timer": {
            "enabled": db_attempt.timerEnabled,
            "scope": db_attempt.timerScope,
            "durationSeconds": db_attempt.timerDurationSeconds,
        },
    }


def _attempt_or_404(database: Session, attempt_id: str) -> Attempt:
    db_attempt = database.query(Attempt).filter(Attempt.id == attempt_id).first()
    if db_attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return db_attempt


def _question_dict(q: Question, reveal: bool, database: Session) -> dict:
    options = sorted(
        database.query(Option).filter(Option.question_id == q.id).all(),
        key=lambda o: o.optionOrder,
    )
    option_payload = [
        {"id": o.id, "optionText": o.optionText, "optionOrder": o.optionOrder}
        for o in options
    ]
    payload = {
        "id": q.id,
        "text": q.text,
        # R27: the explanation is feedback, so it stays hidden in Testing
        # Mode until the quiz is completed (Results reveals it there).
        "explanation": q.explanation if reveal else None,
        "difficulty": getattr(q, "difficulty", None),
        "audioSentence": getattr(q, "audioSentence", None),
        "questionType": getattr(q, "questionType", None),
        "options": option_payload,
    }
    if reveal:
        correct = [o for o in options if o.isCorrect]
        payload["correctOptionId"] = correct[0].id if correct else None
    return payload


@router.get("/attempt/{attempt_id}/session/", response_model=None, tags=["Attempt"])
async def get_session(attempt_id: str, index: int = None, database: Session = Depends(get_db)):
    """The session's current question, one question per page (R12, R13, R15, R20).

    In Testing Mode the correct answer is never sent to the client (R20).
    `answered` tells the client whether the question already has its
    single, immutable answer (R14).
    """
    db_attempt = _attempt_or_404(database, attempt_id)
    question_ids = load_question_ids(db_attempt)
    if not question_ids:
        raise HTTPException(status_code=422, detail="This attempt has no questions")
    index = index if index is not None else 0
    if index < 0 or index >= len(question_ids):
        raise HTTPException(status_code=422, detail=f"Question index out of range (0..{len(question_ids) - 1})")

    question = database.query(Question).filter(Question.id == question_ids[index]).first()
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    existing = (
        database.query(Response)
        .filter((Response.attempts_id == attempt_id) & (Response.attemptQuestion_id == question.id))
        .first()
    )

    reveal = db_attempt.mode == "learning"
    answered = existing is not None and existing.selectedOptionId is not None
    payload = _question_dict(question, reveal=reveal, database=database)
    if answered and existing.selectedOptionId:
        selected_option = database.query(Option).filter(Option.id == existing.selectedOptionId).first()
        payload["selectedOptionId"] = existing.selectedOptionId
        payload["selectedOptionText"] = selected_option.optionText if selected_option else None
        if reveal:
            payload["isMarkedCorrect"] = bool(existing.isMarkedCorrect)

    return {
        "attempt": {
            "id": db_attempt.id,
            "mode": db_attempt.mode,
            "selectedQuestionType": getattr(db_attempt, "selectedQuestionType", None),
            "selectedDifficulty": getattr(db_attempt, "selectedDifficulty", None),
        },
        "mode": db_attempt.mode,
        "totalQuestions": len(question_ids),
        "currentIndex": index,
        "answeredCount": database.query(Response).filter(Response.attempts_id == attempt_id).count(),
        "answered": answered,
        "timer": {
            "enabled": db_attempt.timerEnabled,
            "scope": db_attempt.timerScope,
            "durationSeconds": db_attempt.timerDurationSeconds,
        },
        "question": payload,
    }


@router.post("/attempt/{attempt_id}/answer/", response_model=None, tags=["Attempt"])
async def submit_answer(attempt_id: str, answer: AnswerSubmitCreate, database: Session = Depends(get_db)):
    """Record the single, immutable answer for one question (R14, R15, R17).

    Rejects a second answer for the same question+attempt, an option that
    does not belong to the question, and marks correctness from
    Option.isCorrect (never from the client).
    """
    db_attempt = _attempt_or_404(database, attempt_id)
    question_ids = load_question_ids(db_attempt)
    if answer.questionId not in question_ids:
        raise HTTPException(status_code=422, detail="This question is not part of the current quiz session")
    question = database.query(Question).filter(Question.id == answer.questionId).first()
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    selected_option = database.query(Option).filter(Option.id == answer.selectedOptionId).first()
    if selected_option is None or selected_option.question_id != question.id:
        raise HTTPException(status_code=422, detail="The selected option does not belong to this question")

    existing = (
        database.query(Response)
        .filter((Response.attempts_id == attempt_id) & (Response.attemptQuestion_id == question.id))
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="This question has already been answered; answers cannot be changed (R14)",
        )

    db_response = Response(
        attempts_id=attempt_id,
        attemptQuestion_id=question.id,
        attemptId=attempt_id,
        questionId=question.id,
        selectedOptionId=selected_option.id,
        selectedOptionIds=selected_option.id,
        answeredAt=_datetime.now(),
        isMarkedCorrect=bool(selected_option.isCorrect),
    )
    database.add(db_response)
    database.commit()
    database.refresh(db_response)

    answered_count = database.query(Response).filter(Response.attempts_id == attempt_id).count()
    result = {
        "response": db_response,
        "answeredCount": answered_count,
        "totalQuestions": len(question_ids),
        "quizCompleted": answered_count >= len(question_ids),
    }
    if db_attempt.mode == "learning":
        # R21: correctness is only revealed in Learning Mode; Testing Mode
        # answers are withheld until the quiz is completed (Results screen).
        result["isMarkedCorrect"] = bool(selected_option.isCorrect)
        # Learning Mode feedback (R17-R18): correct answer + explanation immediately
        correct_option = (
            database.query(Option)
            .filter((Option.question_id == question.id) & (Option.isCorrect.is_(True)))
            .first()
        )
        result["correctOptionId"] = correct_option.id if correct_option else None
        result["correctOptionText"] = correct_option.optionText if correct_option else None
        result["explanation"] = question.explanation
    return result


def _finish_attempt(db_attempt: Attempt, database: Session) -> float:
    responses = database.query(Response).filter(Response.attempts_id == db_attempt.id).all()
    question_ids = load_question_ids(db_attempt)
    total = len(question_ids)
    correct = sum(1 for response in responses if response.isMarkedCorrect)
    score = round(100.0 * correct / total, 2) if total > 0 else 0.0
    if db_attempt.status != "completed":
        db_attempt.status = "completed"
        db_attempt.finishedAt = _datetime.now()
        db_attempt.score = score
        database.commit()
        database.refresh(db_attempt)
    return score


@router.get("/attempt/{attempt_id}/results/", response_model=None, tags=["Attempt"])
async def get_results(attempt_id: str, database: Session = Depends(get_db)):
    """The Results screen data (R21-R24).

    Locked with 403 until every question of the session has an answer.
    The score is computed from the recorded Responses (R23), never typed in.
    In Testing Mode the correct answers are revealed here only (R24).
    """
    db_attempt = _attempt_or_404(database, attempt_id)
    question_ids = load_question_ids(db_attempt)
    responses = database.query(Response).filter(Response.attempts_id == attempt_id).all()
    answered_count = len(responses)
    if answered_count < len(question_ids):
        raise HTTPException(
            status_code=403,
            detail=f"Results are locked: {answered_count} of {len(question_ids)} questions answered",
        )

    score = _finish_attempt(db_attempt, database)
    responses_by_question = {response.attemptQuestion_id: response for response in responses}
    # Elapsed-time measurement (R-extra): always derived from startedAt /
    # answeredAt / finishedAt, so it works even when the countdown timer is
    # switched off. Per-question time is the gap between consecutive answers
    # (first question measured from startedAt); total is finishedAt-startedAt.
    _started = db_attempt.startedAt
    _finished = db_attempt.finishedAt or _datetime.now()
    try:
        _total_elapsed = int((_finished - _started).total_seconds()) if _started and _finished else 0
    except Exception:
        _total_elapsed = 0
    _total_elapsed = max(0, _total_elapsed)
    _ordered = sorted(responses, key=lambda r: (r.answeredAt or _finished))
    _elapsed_by_qid: dict = {}
    _prev = _started
    for _resp in _ordered:
        _cur = _resp.answeredAt or _finished
        try:
            _delta = int((_cur - _prev).total_seconds()) if _cur and _prev else 0
        except Exception:
            _delta = 0
        _elapsed_by_qid[_resp.attemptQuestion_id] = max(0, _delta)
        _prev = _cur
    correct = 0
    details = []
    for qid in question_ids:
        question = database.query(Question).filter(Question.id == qid).first()
        response = responses_by_question.get(qid)
        selected_option = (
            database.query(Option).filter(Option.id == response.selectedOptionId).first()
            if response and response.selectedOptionId
            else None
        )
        correct_option = (
            database.query(Option)
            .filter((Option.question_id == qid) & (Option.isCorrect.is_(True)))
            .first()
        )
        was_correct = bool(response.isMarkedCorrect) if response else False
        if was_correct:
            correct += 1
        details.append(
            {
                "questionId": qid,
                "questionText": question.text if question else None,
                "explanation": question.explanation if question else None,
                "selectedOptionId": response.selectedOptionId if response else None,
                "selectedOptionText": selected_option.optionText if selected_option else None,
                "correctOptionId": correct_option.id if correct_option else None,
                "correctOptionText": correct_option.optionText if correct_option else None,
                "isCorrect": was_correct,
                "elapsedSeconds": _elapsed_by_qid.get(qid, 0),
            }
        )

    return {
        "attempt": db_attempt,
        "mode": db_attempt.mode,
        "totalQuestions": len(question_ids),
        "correctCount": correct,
        "incorrectCount": len(question_ids) - correct,
        "percentageScore": score,
        "details": details,
        "timer": {
            "enabled": db_attempt.timerEnabled,
            "scope": db_attempt.timerScope,
            "durationSeconds": db_attempt.timerDurationSeconds,
        },
        "totalElapsedSeconds": _total_elapsed,
    }



