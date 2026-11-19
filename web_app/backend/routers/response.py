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


@router.get("/response/", response_model=None, tags=["Response"])
def get_all_response(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(Response)
        query = query.options(joinedload(Response.option))
        response_list = query.all()

        # Serialize with relationships included
        result = []
        for db_response in response_list:
            item_dict = db_response.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)
            if db_response.option:
                related_obj = db_response.option
                related_dict = related_obj.__dict__.copy()
                related_dict.pop('_sa_instance_state', None)
                item_dict['option'] = related_dict
            else:
                item_dict['option'] = None


            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(Response).all()


@router.get("/response/count/", response_model=None, tags=["Response"])
def get_count_response(database: Session = Depends(get_db)) -> dict:
    """Get the total count of Response entities"""
    count = database.query(Response).count()
    return {"count": count}


@router.get("/response/paginated/", response_model=None, tags=["Response"])
def get_paginated_response(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of Response entities"""
    total = database.query(Response).count()
    response_list = database.query(Response).offset(skip).limit(limit).all()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": response_list
    }
@router.get("/response/search/", response_model=None, tags=["Response"])
def search_response(
    attemptId: str = None,
    id: str = None,
    isMarkedCorrect: bool = None,
    questionId: str = None,
    selectedOptionId: str = None,
    selectedOptionIds: str = None,
    database: Session = Depends(get_db)
) -> list:
    """Search Response entities by attributes"""
    query = database.query(Response)

    if attemptId is not None:
        query = query.filter(Response.attemptId.ilike(f"%{attemptId}%"))
    if id is not None:
        query = query.filter(Response.id.ilike(f"%{id}%"))
    if isMarkedCorrect is not None:
        query = query.filter(Response.isMarkedCorrect == isMarkedCorrect)
    if questionId is not None:
        query = query.filter(Response.questionId.ilike(f"%{questionId}%"))
    if selectedOptionId is not None:
        query = query.filter(Response.selectedOptionId.ilike(f"%{selectedOptionId}%"))
    if selectedOptionIds is not None:
        query = query.filter(Response.selectedOptionIds.ilike(f"%{selectedOptionIds}%"))

    results = query.all()
    return results


@router.get("/response/{attemptQuestion_id}/{attempts_id}/", response_model=None, tags=["Response"])
async def get_response(attemptQuestion_id: str, attempts_id: str, database: Session = Depends(get_db)) -> Response:
    """Get the Response link between a Question and a Attempt"""
    db_response = database.query(Response).filter(
        (Response.attemptQuestion_id == attemptQuestion_id) &
        (Response.attempts_id == attempts_id)
    ).first()
    if db_response is None:
        raise HTTPException(status_code=404, detail="Response not found")
    return db_response



@router.post("/response/", response_model=None, tags=["Response"])
async def create_response(response_data: ResponseCreate, database: Session = Depends(get_db)) -> Response:
    """Create a Response link.

    The Create model carries one field per association end (`attemptQuestion`, `attempts`) holding
    the id of the linked entity, plus the attributes of the association class.
    """
    attemptQuestion_target = link_target(getattr(response_data, 'attemptQuestion', None))
    if attemptQuestion_target is None:
        raise HTTPException(status_code=400, detail="Question ID is required")
    related_attemptQuestion = database.query(Question).filter(Question.id == attemptQuestion_target).first()
    if related_attemptQuestion is None:
        raise HTTPException(status_code=404, detail=f"Question with ID {attemptQuestion_target} not found")
    attempts_target = link_target(getattr(response_data, 'attempts', None))
    if attempts_target is None:
        raise HTTPException(status_code=400, detail="Attempt ID is required")
    related_attempts = database.query(Attempt).filter(Attempt.id == attempts_target).first()
    if related_attempts is None:
        raise HTTPException(status_code=404, detail=f"Attempt with ID {attempts_target} not found")

    # R13: exactly one answer per question. Even if a multi-option payload
    # slips past schema validation, it is refused here before being stored.
    selected_tokens = [
        token
        for token in re.split(r"[,;\s]+", str(response_data.selectedOptionIds or ""))
        if token
    ]
    if len(selected_tokens) > 1:
        raise HTTPException(
            status_code=400,
            detail="selectedOptionIds must contain exactly one option id (one answer per question is allowed)",
        )

    # The chosen option must be one of the question's own options (R12/R13):
    # the app never accepts an option invented outside the uploaded document.
    if response_data.selectedOptionId:
        matching_option = (
            database.query(Option)
            .filter(
                (Option.id == response_data.selectedOptionId)
                & (Option.question_id == attemptQuestion_target)
            )
            .first()
        )
        if matching_option is None:
            raise HTTPException(
                status_code=400,
                detail="The selected option does not belong to this question",
            )

    db_response = Response(
        attemptQuestion_id=attemptQuestion_target,
        attempts_id=attempts_target,
        answeredAt=response_data.answeredAt,        attemptId=response_data.attemptId,        isMarkedCorrect=response_data.isMarkedCorrect,        questionId=response_data.questionId,        selectedOptionId=response_data.selectedOptionId,        selectedOptionIds=response_data.selectedOptionIds        )

    database.add(db_response)
    database.commit()
    database.refresh(db_response)
    return db_response



@router.put("/response/{attemptQuestion_id}/{attempts_id}/", response_model=None, tags=["Response"])
async def update_response(attemptQuestion_id: str, attempts_id: str, response_data: ResponseCreate, database: Session = Depends(get_db)) -> Response:
    """Update the attributes of the Response link identified by both foreign keys"""
    db_response = database.query(Response).filter(
        (Response.attemptQuestion_id == attemptQuestion_id) &
        (Response.attempts_id == attempts_id)
    ).first()
    if db_response is None:
        raise HTTPException(status_code=404, detail="Response not found")

    # R14: an already-given answer cannot be changed. This route only lets
    # metadata about the record (like isMarkedCorrect) be touched; the chosen
    # option itself must never be rewritten after submission.
    if response_data.selectedOptionId is not None and response_data.selectedOptionId != db_response.selectedOptionId:
        raise HTTPException(status_code=400, detail="The answer to this question cannot be changed")
    if response_data.selectedOptionIds not in (None, "") and response_data.selectedOptionIds != db_response.selectedOptionIds:
        raise HTTPException(status_code=400, detail="The answer to this question cannot be changed")

    setattr(db_response, 'answeredAt', response_data.answeredAt)
    setattr(db_response, 'attemptId', response_data.attemptId)
    setattr(db_response, 'isMarkedCorrect', response_data.isMarkedCorrect)
    setattr(db_response, 'questionId', response_data.questionId)
    database.commit()
    database.refresh(db_response)
    return db_response




@router.delete("/response/{attemptQuestion_id}/{attempts_id}/", response_model=None, tags=["Response"])
async def delete_response(attemptQuestion_id: str, attempts_id: str, database: Session = Depends(get_db)):
    """Delete the Response link identified by both foreign keys"""
    db_response = database.query(Response).filter(
        (Response.attemptQuestion_id == attemptQuestion_id) &
        (Response.attempts_id == attempts_id)
    ).first()
    if db_response is None:
        raise HTTPException(status_code=404, detail="Response not found")
    # Snapshot the columns before deleting: the live object may carry loaded
    # back-references, which would make the JSON encoder recurse endlessly.
    deleted_response = {
        attr.key: getattr(db_response, attr.key)
        for attr in db_response.__mapper__.column_attrs
    }
    database.delete(db_response)
    database.commit()
    return deleted_response



