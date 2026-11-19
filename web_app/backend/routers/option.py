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


@router.get("/option/", response_model=None, tags=["Option"])
def get_all_option(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(Option)
        query = query.options(joinedload(Option.question))
        option_list = query.all()

        # Serialize with relationships included
        result = []
        for db_option in option_list:
            item_dict = db_option.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)
            if db_option.question:
                related_obj = db_option.question
                related_dict = related_obj.__dict__.copy()
                related_dict.pop('_sa_instance_state', None)
                item_dict['question'] = related_dict
            else:
                item_dict['question'] = None

            # Add many-to-many and one-to-many relationship objects (full details)
            related_response_list = database.query(Response).filter(Response.option_id == db_option.id).all()
            item_dict['responses'] = []
            for related_response_obj in related_response_list:
                related_response_dict = related_response_obj.__dict__.copy()
                related_response_dict.pop('_sa_instance_state', None)
                item_dict['responses'].append(related_response_dict)

            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(Option).all()


@router.get("/option/count/", response_model=None, tags=["Option"])
def get_count_option(database: Session = Depends(get_db)) -> dict:
    """Get the total count of Option entities"""
    count = database.query(Option).count()
    return {"count": count}


@router.get("/option/paginated/", response_model=None, tags=["Option"])
def get_paginated_option(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of Option entities"""
    total = database.query(Option).count()
    option_list = database.query(Option).offset(skip).limit(limit).all()
    # By default, return flat entities (for charts/widgets)
    # Use detailed=true to get entities with relationships
    if not detailed:
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": option_list
        }

    result = []
    for db_option in option_list:
        responses_ids = database.query(Response.id).filter(Response.option_id == db_option.id).all()
        item_data = {
            "option": db_option,
            "responses_ids": [x[0] for x in responses_ids]        }
        result.append(item_data)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": result
    }
@router.get("/option/search/", response_model=None, tags=["Option"])
def search_option(
    id: str = None,
    isCorrect: bool = None,
    optionOrder: int = None,
    optionText: str = None,
    questionId: str = None,
    database: Session = Depends(get_db)
) -> list:
    """Search Option entities by attributes"""
    query = database.query(Option)

    if id is not None:
        query = query.filter(Option.id.ilike(f"%{id}%"))
    if isCorrect is not None:
        query = query.filter(Option.isCorrect == isCorrect)
    if optionOrder is not None:
        query = query.filter(Option.optionOrder == optionOrder)
    if optionText is not None:
        query = query.filter(Option.optionText.ilike(f"%{optionText}%"))
    if questionId is not None:
        query = query.filter(Option.questionId.ilike(f"%{questionId}%"))

    results = query.all()
    return results


@router.get("/option/{option_id}/", response_model=None, tags=["Option"])
async def get_option(option_id: str, database: Session = Depends(get_db)) -> Option:
    db_option = database.query(Option).filter(Option.id == option_id).first()
    if db_option is None:
        raise HTTPException(status_code=404, detail="Option not found")

    responses_ids = database.query(Response.id).filter(Response.option_id == db_option.id).all()
    response_data = {
        "option": db_option,
        "responses_ids": [x[0] for x in responses_ids]}
    return response_data



@router.post("/option/", response_model=None, tags=["Option"])
async def create_option(option_data: OptionCreate, database: Session = Depends(get_db)) -> Option:

    if option_data.question is not None:
        related_question = database.query(Question).filter(Question.id == option_data.question).first()
        if not related_question:
            raise HTTPException(status_code=400, detail="Question not found")
    else:
        raise HTTPException(status_code=400, detail="Question ID is required")

    db_option = Option(
        isCorrect=option_data.isCorrect,        optionOrder=option_data.optionOrder,        optionText=option_data.optionText,        questionId=option_data.questionId,        question_id=option_data.question        )

    database.add(db_option)
    database.flush()
    database.refresh(db_option)

    if option_data.responses:
        # Validate that all Response IDs exist
        for related_response_id in option_data.responses:
            related_response = database.query(Response).filter(Response.id == related_response_id).first()
            if not related_response:
                raise HTTPException(status_code=400, detail=f"Response with id {related_response_id} not found")

        # Update the related entities with the new foreign key
        database.query(Response).filter(Response.id.in_(option_data.responses)).update(
            {Response.option_id: db_option.id}, synchronize_session=False
        )
        database.flush()




    responses_ids = database.query(Response.id).filter(Response.option_id == db_option.id).all()
    response_data = {
        "option": db_option,
        "responses_ids": [x[0] for x in responses_ids]    }
    database.commit()
    database.refresh(db_option)
    return response_data


@router.post("/option/bulk/", response_model=None, tags=["Option"])
async def bulk_create_option(items: list[OptionCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple Option entities at once"""
    if any(getattr(item, field, None) for item in items for field in ['responses']):
        raise HTTPException(status_code=422, detail="Bulk creation of Option with relationships is not supported; use POST /option/ to validate and persist its relationships")
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item
            if not item_data.question:
                raise ValueError("Question ID is required")

            db_option = Option(
                isCorrect=item_data.isCorrect,                optionOrder=item_data.optionOrder,                optionText=item_data.optionText,                questionId=item_data.questionId,                question_id=item_data.question            )
            database.add(db_option)
            database.flush()  # Get ID without committing
            created_items.append(db_option.id)
        except ValueError as e:
            errors.append({"index": idx, "error": str(e)})
        except IntegrityError as e:
            # The driver's text goes to the log; a failed flush ends the session's work.
            logger.error("Bulk creation of Option failed at item %s: %s", idx, e)
            errors.append({"index": idx, "error": integrity_error_detail(e)})
            break

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} Option entities"
    }


@router.delete("/option/bulk/", response_model=None, tags=["Option"])
async def bulk_delete_option(ids: list[str], database: Session = Depends(get_db)) -> dict:
    """Delete multiple Option entities at once"""
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_option = database.query(Option).filter(Option.id == item_id).first()
        if db_option:
            conflict = option_delete_conflict(db_option)
            if conflict:
                raise HTTPException(status_code=409, detail="Cannot delete Option " + str(item_id) + ": " + conflict)
            database.delete(db_option)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} Option entities"
    }

@router.put("/option/{option_id}/", response_model=None, tags=["Option"])
async def update_option(option_id: str, option_data: OptionCreate, database: Session = Depends(get_db)) -> Option:
    db_option = database.query(Option).filter(Option.id == option_id).first()
    if db_option is None:
        raise HTTPException(status_code=404, detail="Option not found")

    setattr(db_option, 'isCorrect', option_data.isCorrect)
    setattr(db_option, 'optionOrder', option_data.optionOrder)
    setattr(db_option, 'optionText', option_data.optionText)
    setattr(db_option, 'questionId', option_data.questionId)
    if option_data.question is not None:
        related_question = database.query(Question).filter(Question.id == option_data.question).first()
        if not related_question:
            raise HTTPException(status_code=400, detail="Question not found")
        setattr(db_option, 'question_id', option_data.question)
    if option_data.responses is not None:
        requested_responses = set(option_data.responses)
        current_responses = {
            getattr(item, 'id')
            for item in database.query(Response).filter(Response.option_id == db_option.id).all()
        }
        responses_to_detach = current_responses - requested_responses
        if responses_to_detach:
            database.query(Response).filter(Response.id.in_(responses_to_detach)).update(
                {Response.option_id: None}, synchronize_session=False
            )
        responses_to_attach = requested_responses - current_responses
        for related_response_id in responses_to_attach:
            related_response = database.query(Response).filter(Response.id == related_response_id).first()
            if not related_response:
                raise HTTPException(status_code=400, detail="Response with id " + str(related_response_id) + " not found")
        if responses_to_attach:
            database.query(Response).filter(Response.id.in_(responses_to_attach)).update(
                {Response.option_id: db_option.id}, synchronize_session=False
            )
    database.commit()
    database.refresh(db_option)

    responses_ids = database.query(Response.id).filter(Response.option_id == db_option.id).all()
    response_data = {
        "option": db_option,
        "responses_ids": [x[0] for x in responses_ids]    }
    return response_data


def option_delete_conflict(db_option, deleting=None, wholes=()):
    """Why this Option cannot be deleted (None when it can): a related record
    would be left without a link it requires. Covers the parts deleted with it;
    ``deleting`` holds every record of the delete, since none of them can block it,
    and ``wholes`` the records on the way down to this part."""
    if deleting is None:
        state = sa_inspect(db_option)
        deleting = [db_option] + [item[0] for item in state.mapper.cascade_iterator("delete", state)]
    return None


@router.delete("/option/{option_id}/", response_model=None, tags=["Option"])
async def delete_option(option_id: str, database: Session = Depends(get_db)):
    db_option = database.query(Option).filter(Option.id == option_id).first()
    if db_option is None:
        raise HTTPException(status_code=404, detail="Option not found")
    conflict = option_delete_conflict(db_option)
    if conflict:
        raise HTTPException(status_code=409, detail="Cannot delete Option " + str(option_id) + ": " + conflict)
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_option = {
        attr.key: getattr(db_option, attr.key)
        for attr in db_option.__mapper__.column_attrs
    }
    database.delete(db_option)
    database.commit()
    return deleted_option


@router.get("/option/{option_id}/responses/", response_model=None, tags=["Option Relationships"])
async def get_responses_of_option(option_id: str, database: Session = Depends(get_db)):
    """Get all Response entities related to this Option through responses"""
    db_option = database.query(Option).filter(Option.id == option_id).first()
    if db_option is None:
        raise HTTPException(status_code=404, detail="Option not found")

    responses_list = database.query(Response).filter(Response.option_id == option_id).all()

    return {
        "option_id": option_id,
        "responses_count": len(responses_list),
        "responses": responses_list
    }


