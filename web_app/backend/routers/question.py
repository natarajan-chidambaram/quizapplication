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


@router.get("/question/", response_model=None, tags=["Question"])
def get_all_question(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(Question)
        query = query.options(joinedload(Question.quiz))
        query = query.options(joinedload(Question.quizPage))
        question_list = query.all()

        # Serialize with relationships included
        result = []
        for db_question in question_list:
            item_dict = db_question.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)
            if db_question.quiz:
                related_obj = db_question.quiz
                related_dict = related_obj.__dict__.copy()
                related_dict.pop('_sa_instance_state', None)
                item_dict['quiz'] = related_dict
            else:
                item_dict['quiz'] = None
            if db_question.quizPage:
                related_obj = db_question.quizPage
                related_dict = related_obj.__dict__.copy()
                related_dict.pop('_sa_instance_state', None)
                item_dict['quizPage'] = related_dict
            else:
                item_dict['quizPage'] = None

            # Add many-to-many and one-to-many relationship objects (full details)
            related_option_list = database.query(Option).filter(Option.question_id == db_question.id).all()
            item_dict['options'] = []
            for related_option_obj in related_option_list:
                related_option_dict = related_option_obj.__dict__.copy()
                related_option_dict.pop('_sa_instance_state', None)
                item_dict['options'].append(related_option_dict)
            # Add association class links (target entities and the link rows themselves)
            attempts_link_rows = database.query(Response).filter(Response.attemptQuestion_id == db_question.id).all()
            item_dict['attempts_links'] = []
            for link_row in attempts_link_rows:
                link_dict = link_row.__dict__.copy()
                link_dict.pop('_sa_instance_state', None)
                item_dict['attempts_links'].append(link_dict)
            item_dict['attempts'] = []
            for related_attempt_obj in database.query(Attempt).filter(Attempt.id.in_([getattr(link_row, 'attempts_id') for link_row in attempts_link_rows])).all():
                related_attempt_dict = related_attempt_obj.__dict__.copy()
                related_attempt_dict.pop('_sa_instance_state', None)
                item_dict['attempts'].append(related_attempt_dict)

            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(Question).all()


@router.get("/question/count/", response_model=None, tags=["Question"])
def get_count_question(database: Session = Depends(get_db)) -> dict:
    """Get the total count of Question entities"""
    count = database.query(Question).count()
    return {"count": count}


@router.get("/question/paginated/", response_model=None, tags=["Question"])
def get_paginated_question(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of Question entities"""
    total = database.query(Question).count()
    question_list = database.query(Question).offset(skip).limit(limit).all()
    # By default, return flat entities (for charts/widgets)
    # Use detailed=true to get entities with relationships
    if not detailed:
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": question_list
        }

    result = []
    for db_question in question_list:
        attempts_ids = database.query(Response.attempts_id).filter(Response.attemptQuestion_id == db_question.id).all()
        options_ids = database.query(Option.id).filter(Option.question_id == db_question.id).all()
        item_data = {
            "question": db_question,
            "attempts_ids": [x[0] for x in attempts_ids],
            "options_ids": [x[0] for x in options_ids]        }
        result.append(item_data)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": result
    }
@router.get("/question/search/", response_model=None, tags=["Question"])
def search_question(
    id: str = None,
    instructions: str = None,
    orderIndex: int = None,
    points: float = None,
    questionType: str = None,
    quizId: str = None,
    text: str = None,
    database: Session = Depends(get_db)
) -> list:
    """Search Question entities by attributes"""
    query = database.query(Question)

    if id is not None:
        query = query.filter(Question.id.ilike(f"%{id}%"))
    if instructions is not None:
        query = query.filter(Question.instructions.ilike(f"%{instructions}%"))
    if orderIndex is not None:
        query = query.filter(Question.orderIndex == orderIndex)
    if points is not None:
        query = query.filter(Question.points == points)
    if questionType is not None:
        query = query.filter(Question.questionType.ilike(f"%{questionType}%"))
    if quizId is not None:
        query = query.filter(Question.quizId.ilike(f"%{quizId}%"))
    if text is not None:
        query = query.filter(Question.text.ilike(f"%{text}%"))

    results = query.all()
    return results


@router.get("/question/{question_id}/", response_model=None, tags=["Question"])
async def get_question(question_id: str, database: Session = Depends(get_db)) -> Question:
    db_question = database.query(Question).filter(Question.id == question_id).first()
    if db_question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    attempts_ids = database.query(Response.attempts_id).filter(Response.attemptQuestion_id == db_question.id).all()
    options_ids = database.query(Option.id).filter(Option.question_id == db_question.id).all()
    response_data = {
        "question": db_question,
        "attempts_ids": [x[0] for x in attempts_ids],
        "options_ids": [x[0] for x in options_ids]}
    return response_data



@router.post("/question/", response_model=None, tags=["Question"])
async def create_question(question_data: QuestionCreate, database: Session = Depends(get_db)) -> Question:

    if question_data.quiz is not None:
        related_quiz = database.query(Quiz).filter(Quiz.id == question_data.quiz).first()
        if not related_quiz:
            raise HTTPException(status_code=400, detail="Quiz not found")
    else:
        raise HTTPException(status_code=400, detail="Quiz ID is required")
    attempts_payload = getattr(question_data, 'attempts', None)
    if attempts_payload:
        for link in attempts_payload:
            attempts_target = link_target(link)
            related_attempt = database.query(Attempt).filter(Attempt.id == attempts_target).first()
            if not related_attempt:
                raise HTTPException(status_code=404, detail=f"Attempt with ID {attempts_target} not found")
            missing = [name for name in ['attemptId', 'questionId', 'selectedOptionIds', 'answeredAt'] if link_attrs(link, ['attemptId', 'questionId', 'selectedOptionIds', 'answeredAt']).get(name) is None]
            if missing:
                raise HTTPException(status_code=422, detail="Response requires " + ", ".join(missing))

    db_question = Question(
        instructions=question_data.instructions,        orderIndex=question_data.orderIndex,        points=question_data.points,        questionType=question_data.questionType,        quizId=question_data.quizId,        text=question_data.text,        explanation=question_data.explanation,        quiz_id=question_data.quiz        )

    database.add(db_question)
    database.flush()
    database.refresh(db_question)

    if question_data.options:
        # Validate that all Option IDs exist
        for related_option_id in question_data.options:
            related_option = database.query(Option).filter(Option.id == related_option_id).first()
            if not related_option:
                raise HTTPException(status_code=400, detail=f"Option with id {related_option_id} not found")

        # Update the related entities with the new foreign key
        database.query(Option).filter(Option.id.in_(question_data.options)).update(
            {Option.question_id: db_question.id}, synchronize_session=False
        )
        database.flush()


    if attempts_payload:
        for link in attempts_payload:
            database.add(Response(
                attemptQuestion_id=db_question.id,
                attempts_id=link_target(link),
                **link_attrs(link, ('answeredAt', 'attemptId', 'isMarkedCorrect', 'questionId', 'selectedOptionId', 'selectedOptionIds', ))
            ))
        database.flush()


    attempts_ids = database.query(Response.attempts_id).filter(Response.attemptQuestion_id == db_question.id).all()
    options_ids = database.query(Option.id).filter(Option.question_id == db_question.id).all()
    response_data = {
        "question": db_question,
        "attempts_ids": [x[0] for x in attempts_ids],
        "options_ids": [x[0] for x in options_ids]    }
    database.commit()
    database.refresh(db_question)
    return response_data


@router.post("/question/bulk/", response_model=None, tags=["Question"])
async def bulk_create_question(items: list[QuestionCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple Question entities at once"""
    if any(getattr(item, field, None) for item in items for field in ['attempts', 'options']):
        raise HTTPException(status_code=422, detail="Bulk creation of Question with relationships is not supported; use POST /question/ to validate and persist its relationships")
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item
            if not item_data.quiz:
                raise ValueError("Quiz ID is required")

            db_question = Question(
                instructions=item_data.instructions,                orderIndex=item_data.orderIndex,                points=item_data.points,                questionType=item_data.questionType,                quizId=item_data.quizId,                text=item_data.text,                quiz_id=item_data.quiz            )
            database.add(db_question)
            database.flush()  # Get ID without committing
            created_items.append(db_question.id)
        except ValueError as e:
            errors.append({"index": idx, "error": str(e)})
        except IntegrityError as e:
            # The driver's text goes to the log; a failed flush ends the session's work.
            logger.error("Bulk creation of Question failed at item %s: %s", idx, e)
            errors.append({"index": idx, "error": integrity_error_detail(e)})
            break

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} Question entities"
    }


@router.delete("/question/bulk/", response_model=None, tags=["Question"])
async def bulk_delete_question(ids: list[str], database: Session = Depends(get_db)) -> dict:
    """Delete multiple Question entities at once"""
    # Aggregate deletion must account for every related lower bound. Until it
    # shares that validation, use the guarded individual delete endpoint.
    if ids:
        raise HTTPException(status_code=409, detail="Bulk deletion of Question can violate required relationships and is not supported; use the individual DELETE /question/ endpoint")
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_question = database.query(Question).filter(Question.id == item_id).first()
        if db_question:
            conflict = question_delete_conflict(db_question)
            if conflict:
                raise HTTPException(status_code=409, detail="Cannot delete Question " + str(item_id) + ": " + conflict)
            database.delete(db_question)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} Question entities"
    }

@router.put("/question/{question_id}/", response_model=None, tags=["Question"])
async def update_question(question_id: str, question_data: QuestionCreate, database: Session = Depends(get_db)) -> Question:
    db_question = database.query(Question).filter(Question.id == question_id).first()
    if db_question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    setattr(db_question, 'instructions', question_data.instructions)
    setattr(db_question, 'orderIndex', question_data.orderIndex)
    setattr(db_question, 'points', question_data.points)
    setattr(db_question, 'questionType', question_data.questionType)
    setattr(db_question, 'quizId', question_data.quizId)
    setattr(db_question, 'text', question_data.text)
    setattr(db_question, 'explanation', question_data.explanation)
    if question_data.quiz is not None:
        related_quiz = database.query(Quiz).filter(Quiz.id == question_data.quiz).first()
        if not related_quiz:
            raise HTTPException(status_code=400, detail="Quiz not found")
        setattr(db_question, 'quiz_id', question_data.quiz)
    if question_data.options is not None:
        requested_options = set(question_data.options)
        current_options = {
            getattr(item, 'id')
            for item in database.query(Option).filter(Option.question_id == db_question.id).all()
        }
        options_to_detach = current_options - requested_options
        if options_to_detach:
            raise HTTPException(status_code=409, detail="Option " + ", ".join(str(item) for item in sorted(options_to_detach)) + " requires a question: reassign it instead of removing it")
        options_to_attach = requested_options - current_options
        for related_option_id in options_to_attach:
            related_option = database.query(Option).filter(Option.id == related_option_id).first()
            if not related_option:
                raise HTTPException(status_code=400, detail="Option with id " + str(related_option_id) + " not found")
        if options_to_attach:
            database.query(Option).filter(Option.id.in_(options_to_attach)).update(
                {Option.question_id: db_question.id}, synchronize_session=False
            )
    attempts_payload = getattr(question_data, 'attempts', None)
    if attempts_payload is not None:
        existing_attempts_links = {getattr(link_row, 'attempts_id'): link_row for link_row in database.query(Response).filter(
            Response.attemptQuestion_id == db_question.id).all()}
        incoming_attempts_links = {}
        for link in attempts_payload:
            attempts_target = link_target(link)
            related_attempt = database.query(Attempt).filter(Attempt.id == attempts_target).first()
            if related_attempt is None:
                raise HTTPException(status_code=404, detail=f"Attempt with ID {attempts_target} not found")
            incoming_attempts_links[attempts_target] = link

        for attempts_target, link_row in existing_attempts_links.items():
            if attempts_target not in incoming_attempts_links:
                database.delete(link_row)

        for attempts_target, link in incoming_attempts_links.items():
            link_row = existing_attempts_links.get(attempts_target)
            if link_row is None:
                missing = [name for name in ['attemptId', 'questionId', 'selectedOptionIds', 'answeredAt'] if link_attrs(link, ['attemptId', 'questionId', 'selectedOptionIds', 'answeredAt']).get(name) is None]
                if missing:
                    raise HTTPException(status_code=422, detail="Response requires " + ", ".join(missing))
                database.add(Response(
                    attemptQuestion_id=db_question.id,
                    attempts_id=attempts_target,
                    **link_attrs(link, ('answeredAt', 'attemptId', 'isMarkedCorrect', 'questionId', 'selectedOptionId', 'selectedOptionIds', ))
                ))
            else:
                for link_attr_name, link_attr_value in link_attrs(link, ('answeredAt', 'attemptId', 'isMarkedCorrect', 'questionId', 'selectedOptionId', 'selectedOptionIds', )).items():
                    setattr(link_row, link_attr_name, link_attr_value)
    database.commit()
    database.refresh(db_question)

    attempts_ids = database.query(Response.attempts_id).filter(Response.attemptQuestion_id == db_question.id).all()
    options_ids = database.query(Option.id).filter(Option.question_id == db_question.id).all()
    response_data = {
        "question": db_question,
        "attempts_ids": [x[0] for x in attempts_ids],
        "options_ids": [x[0] for x in options_ids]    }
    return response_data


def question_delete_conflict(db_question, deleting=None, wholes=()):
    """Why this Question cannot be deleted (None when it can): a related record
    would be left without a link it requires. Covers the parts deleted with it;
    ``deleting`` holds every record of the delete, since none of them can block it,
    and ``wholes`` the records on the way down to this part."""
    if deleting is None:
        state = sa_inspect(db_question)
        deleting = [db_question] + [item[0] for item in state.mapper.cascade_iterator("delete", state)]
    related_quizPage = db_question.quizPage
    for related in (list(related_quizPage) if isinstance(related_quizPage, list) else [item for item in [related_quizPage] if item is not None]):
        remaining = 0
        if related not in deleting and remaining < 1:
            return "QuizPage " + str(getattr(related, 'id')) + " requires at least 1 quizPageQuestion"
    if any(whole is db_question for whole in wholes):
        return "Question " + str(getattr(db_question, 'id')) + " is one of its own parts"
    from routers.option import option_delete_conflict
    parts_options = db_question.options
    for part in (list(parts_options) if isinstance(parts_options, list) else [item for item in [parts_options] if item is not None]):
        conflict = option_delete_conflict(part, deleting, wholes + (db_question,))
        if conflict:
            return "Option " + str(getattr(part, 'id')) + " would be deleted with it, and " + conflict
    return None


@router.delete("/question/{question_id}/", response_model=None, tags=["Question"])
async def delete_question(question_id: str, database: Session = Depends(get_db)):
    db_question = database.query(Question).filter(Question.id == question_id).first()
    if db_question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    conflict = question_delete_conflict(db_question)
    if conflict:
        raise HTTPException(status_code=409, detail="Cannot delete Question " + str(question_id) + ": " + conflict)
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_question = {
        attr.key: getattr(db_question, attr.key)
        for attr in db_question.__mapper__.column_attrs
    }
    database.delete(db_question)
    database.commit()
    return deleted_question

@router.post("/question/{question_id}/attempts/{attempt_id}/", response_model=None, tags=["Question Relationships"])
async def add_attempts_to_question(question_id: str, attempt_id: str, link: dict = Body(default=None), database: Session = Depends(get_db)):
    """Add a Attempt to this Question's attempts relationship.

    The request body carries the Response attributes (answeredAt, attemptId, isMarkedCorrect, questionId, selectedOptionId, selectedOptionIds).
    A `target` field in the body is ignored: the target is taken from the path.
    """
    db_question = database.query(Question).filter(Question.id == question_id).first()
    if db_question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    related_attempt = database.query(Attempt).filter(Attempt.id == attempt_id).first()
    if related_attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")

    # Check if relationship already exists
    existing = database.query(Response).filter(
        (Response.attemptQuestion_id == question_id) &
        (Response.attempts_id == attempt_id)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Relationship already exists")
    missing = [name for name in ['attemptId', 'questionId', 'selectedOptionIds', 'answeredAt'] if link_attrs(link, ['attemptId', 'questionId', 'selectedOptionIds', 'answeredAt']).get(name) is None]
    if missing:
        raise HTTPException(status_code=422, detail="Response requires " + ", ".join(missing))

    # Create the association class row
    database.add(Response(
        attemptQuestion_id=question_id,
        attempts_id=attempt_id,
        **link_attrs(link, ('answeredAt', 'attemptId', 'isMarkedCorrect', 'questionId', 'selectedOptionId', 'selectedOptionIds', ))
    ))
    database.commit()

    return {"message": "Attempt added to attempts successfully"}


@router.delete("/question/{question_id}/attempts/{attempt_id}/", response_model=None, tags=["Question Relationships"])
async def remove_attempts_from_question(question_id: str, attempt_id: str, database: Session = Depends(get_db)):
    """Remove a Attempt from this Question's attempts relationship"""
    db_question = database.query(Question).filter(Question.id == question_id).first()
    if db_question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    # Check if relationship exists
    existing = database.query(Response).filter(
        (Response.attemptQuestion_id == question_id) &
        (Response.attempts_id == attempt_id)
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Relationship not found")


    # Delete the association class row
    database.delete(existing)
    database.commit()

    return {"message": "Attempt removed from attempts successfully"}


@router.get("/question/{question_id}/attempts/", response_model=None, tags=["Question Relationships"])
async def get_attempts_of_question(question_id: str, database: Session = Depends(get_db)):
    """Get all Attempt entities related to this Question through attempts, with their Response links"""
    db_question = database.query(Question).filter(Question.id == question_id).first()
    if db_question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    attempts_link_rows = database.query(Response).filter(Response.attemptQuestion_id == question_id).all()
    attempt_list = database.query(Attempt).filter(Attempt.id.in_(
        [getattr(link_row, 'attempts_id') for link_row in attempts_link_rows])).all()

    return {
        "question_id": question_id,
        "attempts_count": len(attempt_list),
        "attempts": attempt_list,
        "attempts_links": attempts_link_rows
    }


@router.get("/question/{question_id}/options/", response_model=None, tags=["Question Relationships"])
async def get_options_of_question(question_id: str, database: Session = Depends(get_db)):
    """Get all Option entities related to this Question through options"""
    db_question = database.query(Question).filter(Question.id == question_id).first()
    if db_question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    options_list = database.query(Option).filter(Option.question_id == question_id).all()

    return {
        "question_id": question_id,
        "options_count": len(options_list),
        "options": options_list
    }


