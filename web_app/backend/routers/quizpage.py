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


@router.get("/quizpage/", response_model=None, tags=["QuizPage"])
def get_all_quizpage(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(QuizPage)
        query = query.options(joinedload(QuizPage.quizPageQuestion))
        query = query.options(joinedload(QuizPage.quizPageQuiz))
        quizpage_list = query.all()

        # Serialize with relationships included
        result = []
        for db_quizpage in quizpage_list:
            item_dict = db_quizpage.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)
            if db_quizpage.quizPageQuestion:
                related_obj = db_quizpage.quizPageQuestion
                related_dict = related_obj.__dict__.copy()
                related_dict.pop('_sa_instance_state', None)
                item_dict['quizPageQuestion'] = related_dict
            else:
                item_dict['quizPageQuestion'] = None
            if db_quizpage.quizPageQuiz:
                related_obj = db_quizpage.quizPageQuiz
                related_dict = related_obj.__dict__.copy()
                related_dict.pop('_sa_instance_state', None)
                item_dict['quizPageQuiz'] = related_dict
            else:
                item_dict['quizPageQuiz'] = None


            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(QuizPage).all()


@router.get("/quizpage/count/", response_model=None, tags=["QuizPage"])
def get_count_quizpage(database: Session = Depends(get_db)) -> dict:
    """Get the total count of QuizPage entities"""
    count = database.query(QuizPage).count()
    return {"count": count}


@router.get("/quizpage/paginated/", response_model=None, tags=["QuizPage"])
def get_paginated_quizpage(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of QuizPage entities"""
    total = database.query(QuizPage).count()
    quizpage_list = database.query(QuizPage).offset(skip).limit(limit).all()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": quizpage_list
    }
@router.get("/quizpage/search/", response_model=None, tags=["QuizPage"])
def search_quizpage(
    id: str = None,
    isVisible: bool = None,
    layoutHint: str = None,
    pageNumber: int = None,
    questionId: str = None,
    quizId: str = None,
    database: Session = Depends(get_db)
) -> list:
    """Search QuizPage entities by attributes"""
    query = database.query(QuizPage)

    if id is not None:
        query = query.filter(QuizPage.id.ilike(f"%{id}%"))
    if isVisible is not None:
        query = query.filter(QuizPage.isVisible == isVisible)
    if layoutHint is not None:
        query = query.filter(QuizPage.layoutHint.ilike(f"%{layoutHint}%"))
    if pageNumber is not None:
        query = query.filter(QuizPage.pageNumber == pageNumber)
    if questionId is not None:
        query = query.filter(QuizPage.questionId.ilike(f"%{questionId}%"))
    if quizId is not None:
        query = query.filter(QuizPage.quizId.ilike(f"%{quizId}%"))

    results = query.all()
    return results


@router.get("/quizpage/{quizpage_id}/", response_model=None, tags=["QuizPage"])
async def get_quizpage(quizpage_id: str, database: Session = Depends(get_db)) -> QuizPage:
    db_quizpage = database.query(QuizPage).filter(QuizPage.id == quizpage_id).first()
    if db_quizpage is None:
        raise HTTPException(status_code=404, detail="QuizPage not found")

    response_data = {
        "quizpage": db_quizpage,
}
    return response_data



@router.post("/quizpage/", response_model=None, tags=["QuizPage"])
async def create_quizpage(quizpage_data: QuizPageCreate, database: Session = Depends(get_db)) -> QuizPage:

    if quizpage_data.quizPageQuestion is not None:
        related_quizPageQuestion = database.query(Question).filter(Question.id == quizpage_data.quizPageQuestion).first()
        if not related_quizPageQuestion:
            raise HTTPException(status_code=400, detail="Question not found")
    else:
        raise HTTPException(status_code=400, detail="Question ID is required")
    if quizpage_data.quizPageQuiz is not None:
        related_quizPageQuiz = database.query(Quiz).filter(Quiz.id == quizpage_data.quizPageQuiz).first()
        if not related_quizPageQuiz:
            raise HTTPException(status_code=400, detail="Quiz not found")
    else:
        raise HTTPException(status_code=400, detail="Quiz ID is required")

    db_quizpage = QuizPage(
        isVisible=quizpage_data.isVisible,        layoutHint=quizpage_data.layoutHint,        pageNumber=quizpage_data.pageNumber,        questionId=quizpage_data.questionId,        quizId=quizpage_data.quizId,        quizPageQuestion_id=quizpage_data.quizPageQuestion,        quizPageQuiz_id=quizpage_data.quizPageQuiz        )

    database.add(db_quizpage)
    database.flush()
    database.refresh(db_quizpage)





    database.commit()
    database.refresh(db_quizpage)
    return db_quizpage


@router.post("/quizpage/bulk/", response_model=None, tags=["QuizPage"])
async def bulk_create_quizpage(items: list[QuizPageCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple QuizPage entities at once"""
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item
            if not item_data.quizPageQuestion:
                raise ValueError("Question ID is required")
            if not item_data.quizPageQuiz:
                raise ValueError("Quiz ID is required")

            db_quizpage = QuizPage(
                isVisible=item_data.isVisible,                layoutHint=item_data.layoutHint,                pageNumber=item_data.pageNumber,                questionId=item_data.questionId,                quizId=item_data.quizId,                quizPageQuestion_id=item_data.quizPageQuestion,                quizPageQuiz_id=item_data.quizPageQuiz            )
            database.add(db_quizpage)
            database.flush()  # Get ID without committing
            created_items.append(db_quizpage.id)
        except ValueError as e:
            errors.append({"index": idx, "error": str(e)})
        except IntegrityError as e:
            # The driver's text goes to the log; a failed flush ends the session's work.
            logger.error("Bulk creation of QuizPage failed at item %s: %s", idx, e)
            errors.append({"index": idx, "error": integrity_error_detail(e)})
            break

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} QuizPage entities"
    }


@router.delete("/quizpage/bulk/", response_model=None, tags=["QuizPage"])
async def bulk_delete_quizpage(ids: list[str], database: Session = Depends(get_db)) -> dict:
    """Delete multiple QuizPage entities at once"""
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_quizpage = database.query(QuizPage).filter(QuizPage.id == item_id).first()
        if db_quizpage:
            conflict = quizpage_delete_conflict(db_quizpage)
            if conflict:
                raise HTTPException(status_code=409, detail="Cannot delete QuizPage " + str(item_id) + ": " + conflict)
            database.delete(db_quizpage)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} QuizPage entities"
    }

@router.put("/quizpage/{quizpage_id}/", response_model=None, tags=["QuizPage"])
async def update_quizpage(quizpage_id: str, quizpage_data: QuizPageCreate, database: Session = Depends(get_db)) -> QuizPage:
    db_quizpage = database.query(QuizPage).filter(QuizPage.id == quizpage_id).first()
    if db_quizpage is None:
        raise HTTPException(status_code=404, detail="QuizPage not found")

    setattr(db_quizpage, 'isVisible', quizpage_data.isVisible)
    setattr(db_quizpage, 'layoutHint', quizpage_data.layoutHint)
    setattr(db_quizpage, 'pageNumber', quizpage_data.pageNumber)
    setattr(db_quizpage, 'questionId', quizpage_data.questionId)
    setattr(db_quizpage, 'quizId', quizpage_data.quizId)
    if quizpage_data.quizPageQuestion is not None:
        related_quizPageQuestion = database.query(Question).filter(Question.id == quizpage_data.quizPageQuestion).first()
        if not related_quizPageQuestion:
            raise HTTPException(status_code=400, detail="Question not found")
        setattr(db_quizpage, 'quizPageQuestion_id', quizpage_data.quizPageQuestion)
    if quizpage_data.quizPageQuiz is not None:
        related_quizPageQuiz = database.query(Quiz).filter(Quiz.id == quizpage_data.quizPageQuiz).first()
        if not related_quizPageQuiz:
            raise HTTPException(status_code=400, detail="Quiz not found")
        setattr(db_quizpage, 'quizPageQuiz_id', quizpage_data.quizPageQuiz)
    database.commit()
    database.refresh(db_quizpage)

    return db_quizpage


def quizpage_delete_conflict(db_quizpage, deleting=None, wholes=()):
    """Why this QuizPage cannot be deleted (None when it can): a related record
    would be left without a link it requires. Covers the parts deleted with it;
    ``deleting`` holds every record of the delete, since none of them can block it,
    and ``wholes`` the records on the way down to this part."""
    if deleting is None:
        state = sa_inspect(db_quizpage)
        deleting = [db_quizpage] + [item[0] for item in state.mapper.cascade_iterator("delete", state)]
    return None


@router.delete("/quizpage/{quizpage_id}/", response_model=None, tags=["QuizPage"])
async def delete_quizpage(quizpage_id: str, database: Session = Depends(get_db)):
    db_quizpage = database.query(QuizPage).filter(QuizPage.id == quizpage_id).first()
    if db_quizpage is None:
        raise HTTPException(status_code=404, detail="QuizPage not found")
    conflict = quizpage_delete_conflict(db_quizpage)
    if conflict:
        raise HTTPException(status_code=409, detail="Cannot delete QuizPage " + str(quizpage_id) + ": " + conflict)
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_quizpage = {
        attr.key: getattr(db_quizpage, attr.key)
        for attr in db_quizpage.__mapper__.column_attrs
    }
    database.delete(db_quizpage)
    database.commit()
    return deleted_quizpage



