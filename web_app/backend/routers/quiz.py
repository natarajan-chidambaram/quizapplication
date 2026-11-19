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


@router.get("/quiz/", response_model=None, tags=["Quiz"])
def get_all_quiz(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(Quiz)
        quiz_list = query.all()

        # Serialize with relationships included
        result = []
        for db_quiz in quiz_list:
            item_dict = db_quiz.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)

            # Add many-to-many and one-to-many relationship objects (full details)
            related_attempt_list = database.query(Attempt).filter(Attempt.attemptQuiz_id == db_quiz.id).all()
            item_dict['attempts'] = []
            for related_attempt_obj in related_attempt_list:
                related_attempt_dict = related_attempt_obj.__dict__.copy()
                related_attempt_dict.pop('_sa_instance_state', None)
                item_dict['attempts'].append(related_attempt_dict)
            related_pdfdocument_list = database.query(PDFDocument).filter(PDFDocument.pDFDocumentQuiz_id == db_quiz.id).all()
            item_dict['documents'] = []
            for related_pdfdocument_obj in related_pdfdocument_list:
                related_pdfdocument_dict = related_pdfdocument_obj.__dict__.copy()
                related_pdfdocument_dict.pop('_sa_instance_state', None)
                item_dict['documents'].append(related_pdfdocument_dict)
            related_question_list = database.query(Question).filter(Question.quiz_id == db_quiz.id).all()
            item_dict['questions'] = []
            for related_question_obj in related_question_list:
                related_question_dict = related_question_obj.__dict__.copy()
                related_question_dict.pop('_sa_instance_state', None)
                item_dict['questions'].append(related_question_dict)
            related_quizpage_list = database.query(QuizPage).filter(QuizPage.quizPageQuiz_id == db_quiz.id).all()
            item_dict['pages'] = []
            for related_quizpage_obj in related_quizpage_list:
                related_quizpage_dict = related_quizpage_obj.__dict__.copy()
                related_quizpage_dict.pop('_sa_instance_state', None)
                item_dict['pages'].append(related_quizpage_dict)

            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(Quiz).all()


@router.get("/quiz/count/", response_model=None, tags=["Quiz"])
def get_count_quiz(database: Session = Depends(get_db)) -> dict:
    """Get the total count of Quiz entities"""
    count = database.query(Quiz).count()
    return {"count": count}


@router.get("/quiz/paginated/", response_model=None, tags=["Quiz"])
def get_paginated_quiz(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of Quiz entities"""
    total = database.query(Quiz).count()
    quiz_list = database.query(Quiz).offset(skip).limit(limit).all()
    # By default, return flat entities (for charts/widgets)
    # Use detailed=true to get entities with relationships
    if not detailed:
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": quiz_list
        }

    result = []
    for db_quiz in quiz_list:
        attempts_ids = database.query(Attempt.id).filter(Attempt.attemptQuiz_id == db_quiz.id).all()
        documents_ids = database.query(PDFDocument.id).filter(PDFDocument.pDFDocumentQuiz_id == db_quiz.id).all()
        questions_ids = database.query(Question.id).filter(Question.quiz_id == db_quiz.id).all()
        pages_ids = database.query(QuizPage.id).filter(QuizPage.quizPageQuiz_id == db_quiz.id).all()
        item_data = {
            "quiz": db_quiz,
            "attempts_ids": [x[0] for x in attempts_ids],            "documents_ids": [x[0] for x in documents_ids],            "questions_ids": [x[0] for x in questions_ids],            "pages_ids": [x[0] for x in pages_ids]        }
        result.append(item_data)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": result
    }
@router.get("/quiz/search/", response_model=None, tags=["Quiz"])
def search_quiz(
    createdByUserId: str = None,
    description: str = None,
    id: str = None,
    isPublished: bool = None,
    title: str = None,
    database: Session = Depends(get_db)
) -> list:
    """Search Quiz entities by attributes"""
    query = database.query(Quiz)

    if createdByUserId is not None:
        query = query.filter(Quiz.createdByUserId.ilike(f"%{createdByUserId}%"))
    if description is not None:
        query = query.filter(Quiz.description.ilike(f"%{description}%"))
    if id is not None:
        query = query.filter(Quiz.id.ilike(f"%{id}%"))
    if isPublished is not None:
        query = query.filter(Quiz.isPublished == isPublished)
    if title is not None:
        query = query.filter(Quiz.title.ilike(f"%{title}%"))

    results = query.all()
    return results


@router.get("/quiz/{quiz_id}/", response_model=None, tags=["Quiz"])
async def get_quiz(quiz_id: str, database: Session = Depends(get_db)) -> Quiz:
    db_quiz = database.query(Quiz).filter(Quiz.id == quiz_id).first()
    if db_quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")

    attempts_ids = database.query(Attempt.id).filter(Attempt.attemptQuiz_id == db_quiz.id).all()
    documents_ids = database.query(PDFDocument.id).filter(PDFDocument.pDFDocumentQuiz_id == db_quiz.id).all()
    questions_ids = database.query(Question.id).filter(Question.quiz_id == db_quiz.id).all()
    pages_ids = database.query(QuizPage.id).filter(QuizPage.quizPageQuiz_id == db_quiz.id).all()
    response_data = {
        "quiz": db_quiz,
        "attempts_ids": [x[0] for x in attempts_ids],        "documents_ids": [x[0] for x in documents_ids],        "questions_ids": [x[0] for x in questions_ids],        "pages_ids": [x[0] for x in pages_ids]}
    return response_data



@router.post("/quiz/", response_model=None, tags=["Quiz"])
async def create_quiz(quiz_data: QuizCreate, database: Session = Depends(get_db)) -> Quiz:


    db_quiz = Quiz(
        createdByUserId=quiz_data.createdByUserId,        description=quiz_data.description,        isPublished=quiz_data.isPublished,        title=quiz_data.title        )

    database.add(db_quiz)
    database.flush()
    database.refresh(db_quiz)

    if quiz_data.attempts:
        # Validate that all Attempt IDs exist
        for related_attempt_id in quiz_data.attempts:
            related_attempt = database.query(Attempt).filter(Attempt.id == related_attempt_id).first()
            if not related_attempt:
                raise HTTPException(status_code=400, detail=f"Attempt with id {related_attempt_id} not found")

        # Update the related entities with the new foreign key
        database.query(Attempt).filter(Attempt.id.in_(quiz_data.attempts)).update(
            {Attempt.attemptQuiz_id: db_quiz.id}, synchronize_session=False
        )
        database.flush()
    if quiz_data.documents:
        # Validate that all PDFDocument IDs exist
        for related_pdfdocument_id in quiz_data.documents:
            related_pdfdocument = database.query(PDFDocument).filter(PDFDocument.id == related_pdfdocument_id).first()
            if not related_pdfdocument:
                raise HTTPException(status_code=400, detail=f"PDFDocument with id {related_pdfdocument_id} not found")

        # Update the related entities with the new foreign key
        database.query(PDFDocument).filter(PDFDocument.id.in_(quiz_data.documents)).update(
            {PDFDocument.pDFDocumentQuiz_id: db_quiz.id}, synchronize_session=False
        )
        database.flush()
    if quiz_data.questions:
        # Validate that all Question IDs exist
        for related_question_id in quiz_data.questions:
            related_question = database.query(Question).filter(Question.id == related_question_id).first()
            if not related_question:
                raise HTTPException(status_code=400, detail=f"Question with id {related_question_id} not found")

        # Update the related entities with the new foreign key
        database.query(Question).filter(Question.id.in_(quiz_data.questions)).update(
            {Question.quiz_id: db_quiz.id}, synchronize_session=False
        )
        database.flush()
    if quiz_data.pages:
        # Validate that all QuizPage IDs exist
        for related_quizpage_id in quiz_data.pages:
            related_quizpage = database.query(QuizPage).filter(QuizPage.id == related_quizpage_id).first()
            if not related_quizpage:
                raise HTTPException(status_code=400, detail=f"QuizPage with id {related_quizpage_id} not found")

        # Update the related entities with the new foreign key
        database.query(QuizPage).filter(QuizPage.id.in_(quiz_data.pages)).update(
            {QuizPage.quizPageQuiz_id: db_quiz.id}, synchronize_session=False
        )
        database.flush()




    attempts_ids = database.query(Attempt.id).filter(Attempt.attemptQuiz_id == db_quiz.id).all()
    documents_ids = database.query(PDFDocument.id).filter(PDFDocument.pDFDocumentQuiz_id == db_quiz.id).all()
    questions_ids = database.query(Question.id).filter(Question.quiz_id == db_quiz.id).all()
    pages_ids = database.query(QuizPage.id).filter(QuizPage.quizPageQuiz_id == db_quiz.id).all()
    response_data = {
        "quiz": db_quiz,
        "attempts_ids": [x[0] for x in attempts_ids],        "documents_ids": [x[0] for x in documents_ids],        "questions_ids": [x[0] for x in questions_ids],        "pages_ids": [x[0] for x in pages_ids]    }
    database.commit()
    database.refresh(db_quiz)
    return response_data


@router.post("/quiz/bulk/", response_model=None, tags=["Quiz"])
async def bulk_create_quiz(items: list[QuizCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple Quiz entities at once"""
    if any(getattr(item, field, None) for item in items for field in ['attempts', 'documents', 'questions', 'pages']):
        raise HTTPException(status_code=422, detail="Bulk creation of Quiz with relationships is not supported; use POST /quiz/ to validate and persist its relationships")
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item

            db_quiz = Quiz(
                createdByUserId=item_data.createdByUserId,                description=item_data.description,                isPublished=item_data.isPublished,                title=item_data.title            )
            database.add(db_quiz)
            database.flush()  # Get ID without committing
            created_items.append(db_quiz.id)
        except ValueError as e:
            errors.append({"index": idx, "error": str(e)})
        except IntegrityError as e:
            # The driver's text goes to the log; a failed flush ends the session's work.
            logger.error("Bulk creation of Quiz failed at item %s: %s", idx, e)
            errors.append({"index": idx, "error": integrity_error_detail(e)})
            break

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} Quiz entities"
    }


@router.delete("/quiz/bulk/", response_model=None, tags=["Quiz"])
async def bulk_delete_quiz(ids: list[str], database: Session = Depends(get_db)) -> dict:
    """Delete multiple Quiz entities at once"""
    # Aggregate deletion must account for every related lower bound. Until it
    # shares that validation, use the guarded individual delete endpoint.
    if ids:
        raise HTTPException(status_code=409, detail="Bulk deletion of Quiz can violate required relationships and is not supported; use the individual DELETE /quiz/ endpoint")
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_quiz = database.query(Quiz).filter(Quiz.id == item_id).first()
        if db_quiz:
            conflict = quiz_delete_conflict(db_quiz)
            if conflict:
                raise HTTPException(status_code=409, detail="Cannot delete Quiz " + str(item_id) + ": " + conflict)
            database.delete(db_quiz)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} Quiz entities"
    }

@router.put("/quiz/{quiz_id}/", response_model=None, tags=["Quiz"])
async def update_quiz(quiz_id: str, quiz_data: QuizCreate, database: Session = Depends(get_db)) -> Quiz:
    db_quiz = database.query(Quiz).filter(Quiz.id == quiz_id).first()
    if db_quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")

    setattr(db_quiz, 'createdByUserId', quiz_data.createdByUserId)
    setattr(db_quiz, 'description', quiz_data.description)
    setattr(db_quiz, 'isPublished', quiz_data.isPublished)
    setattr(db_quiz, 'title', quiz_data.title)
    if quiz_data.attempts is not None:
        requested_attempts = set(quiz_data.attempts)
        current_attempts = {
            getattr(item, 'id')
            for item in database.query(Attempt).filter(Attempt.attemptQuiz_id == db_quiz.id).all()
        }
        attempts_to_detach = current_attempts - requested_attempts
        if attempts_to_detach:
            raise HTTPException(status_code=409, detail="Attempt " + ", ".join(str(item) for item in sorted(attempts_to_detach)) + " requires a attemptQuiz: reassign it instead of removing it")
        attempts_to_attach = requested_attempts - current_attempts
        for related_attempt_id in attempts_to_attach:
            related_attempt = database.query(Attempt).filter(Attempt.id == related_attempt_id).first()
            if not related_attempt:
                raise HTTPException(status_code=400, detail="Attempt with id " + str(related_attempt_id) + " not found")
        if attempts_to_attach:
            database.query(Attempt).filter(Attempt.id.in_(attempts_to_attach)).update(
                {Attempt.attemptQuiz_id: db_quiz.id}, synchronize_session=False
            )
    if quiz_data.documents is not None:
        requested_documents = set(quiz_data.documents)
        current_documents = {
            getattr(item, 'id')
            for item in database.query(PDFDocument).filter(PDFDocument.pDFDocumentQuiz_id == db_quiz.id).all()
        }
        documents_to_detach = current_documents - requested_documents
        if documents_to_detach:
            database.query(PDFDocument).filter(PDFDocument.id.in_(documents_to_detach)).update(
                {PDFDocument.pDFDocumentQuiz_id: None}, synchronize_session=False
            )
        documents_to_attach = requested_documents - current_documents
        for related_pdfdocument_id in documents_to_attach:
            related_pdfdocument = database.query(PDFDocument).filter(PDFDocument.id == related_pdfdocument_id).first()
            if not related_pdfdocument:
                raise HTTPException(status_code=400, detail="PDFDocument with id " + str(related_pdfdocument_id) + " not found")
        if documents_to_attach:
            database.query(PDFDocument).filter(PDFDocument.id.in_(documents_to_attach)).update(
                {PDFDocument.pDFDocumentQuiz_id: db_quiz.id}, synchronize_session=False
            )
    if quiz_data.questions is not None:
        requested_questions = set(quiz_data.questions)
        current_questions = {
            getattr(item, 'id')
            for item in database.query(Question).filter(Question.quiz_id == db_quiz.id).all()
        }
        questions_to_detach = current_questions - requested_questions
        if questions_to_detach:
            raise HTTPException(status_code=409, detail="Question " + ", ".join(str(item) for item in sorted(questions_to_detach)) + " requires a quiz: reassign it instead of removing it")
        questions_to_attach = requested_questions - current_questions
        for related_question_id in questions_to_attach:
            related_question = database.query(Question).filter(Question.id == related_question_id).first()
            if not related_question:
                raise HTTPException(status_code=400, detail="Question with id " + str(related_question_id) + " not found")
        if questions_to_attach:
            database.query(Question).filter(Question.id.in_(questions_to_attach)).update(
                {Question.quiz_id: db_quiz.id}, synchronize_session=False
            )
    if quiz_data.pages is not None:
        requested_pages = set(quiz_data.pages)
        current_pages = {
            getattr(item, 'id')
            for item in database.query(QuizPage).filter(QuizPage.quizPageQuiz_id == db_quiz.id).all()
        }
        pages_to_detach = current_pages - requested_pages
        if pages_to_detach:
            raise HTTPException(status_code=409, detail="QuizPage " + ", ".join(str(item) for item in sorted(pages_to_detach)) + " requires a quizPageQuiz: reassign it instead of removing it")
        pages_to_attach = requested_pages - current_pages
        for related_quizpage_id in pages_to_attach:
            related_quizpage = database.query(QuizPage).filter(QuizPage.id == related_quizpage_id).first()
            if not related_quizpage:
                raise HTTPException(status_code=400, detail="QuizPage with id " + str(related_quizpage_id) + " not found")
        if pages_to_attach:
            database.query(QuizPage).filter(QuizPage.id.in_(pages_to_attach)).update(
                {QuizPage.quizPageQuiz_id: db_quiz.id}, synchronize_session=False
            )
    database.commit()
    database.refresh(db_quiz)

    attempts_ids = database.query(Attempt.id).filter(Attempt.attemptQuiz_id == db_quiz.id).all()
    documents_ids = database.query(PDFDocument.id).filter(PDFDocument.pDFDocumentQuiz_id == db_quiz.id).all()
    questions_ids = database.query(Question.id).filter(Question.quiz_id == db_quiz.id).all()
    pages_ids = database.query(QuizPage.id).filter(QuizPage.quizPageQuiz_id == db_quiz.id).all()
    response_data = {
        "quiz": db_quiz,
        "attempts_ids": [x[0] for x in attempts_ids],        "documents_ids": [x[0] for x in documents_ids],        "questions_ids": [x[0] for x in questions_ids],        "pages_ids": [x[0] for x in pages_ids]    }
    return response_data


def quiz_delete_conflict(db_quiz, deleting=None, wholes=()):
    """Why this Quiz cannot be deleted (None when it can): a related record
    would be left without a link it requires. Covers the parts deleted with it;
    ``deleting`` holds every record of the delete, since none of them can block it,
    and ``wholes`` the records on the way down to this part."""
    if deleting is None:
        state = sa_inspect(db_quiz)
        deleting = [db_quiz] + [item[0] for item in state.mapper.cascade_iterator("delete", state)]
    related_attempts = db_quiz.attempts
    for related in (list(related_attempts) if isinstance(related_attempts, list) else [item for item in [related_attempts] if item is not None]):
        remaining = 0
        if related not in deleting and remaining < 1:
            return "Attempt " + str(getattr(related, 'id')) + " requires at least 1 attemptQuiz"
    if any(whole is db_quiz for whole in wholes):
        return "Quiz " + str(getattr(db_quiz, 'id')) + " is one of its own parts"
    from routers.question import question_delete_conflict
    parts_questions = db_quiz.questions
    for part in (list(parts_questions) if isinstance(parts_questions, list) else [item for item in [parts_questions] if item is not None]):
        conflict = question_delete_conflict(part, deleting, wholes + (db_quiz,))
        if conflict:
            return "Question " + str(getattr(part, 'id')) + " would be deleted with it, and " + conflict
    from routers.quizpage import quizpage_delete_conflict
    parts_pages = db_quiz.pages
    for part in (list(parts_pages) if isinstance(parts_pages, list) else [item for item in [parts_pages] if item is not None]):
        conflict = quizpage_delete_conflict(part, deleting, wholes + (db_quiz,))
        if conflict:
            return "QuizPage " + str(getattr(part, 'id')) + " would be deleted with it, and " + conflict
    return None


@router.delete("/quiz/{quiz_id}/", response_model=None, tags=["Quiz"])
async def delete_quiz(quiz_id: str, database: Session = Depends(get_db)):
    db_quiz = database.query(Quiz).filter(Quiz.id == quiz_id).first()
    if db_quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    conflict = quiz_delete_conflict(db_quiz)
    if conflict:
        raise HTTPException(status_code=409, detail="Cannot delete Quiz " + str(quiz_id) + ": " + conflict)
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_quiz = {
        attr.key: getattr(db_quiz, attr.key)
        for attr in db_quiz.__mapper__.column_attrs
    }
    database.delete(db_quiz)
    database.commit()
    return deleted_quiz


@router.get("/quiz/{quiz_id}/attempts/", response_model=None, tags=["Quiz Relationships"])
async def get_attempts_of_quiz(quiz_id: str, database: Session = Depends(get_db)):
    """Get all Attempt entities related to this Quiz through attempts"""
    db_quiz = database.query(Quiz).filter(Quiz.id == quiz_id).first()
    if db_quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")

    attempts_list = database.query(Attempt).filter(Attempt.attemptQuiz_id == quiz_id).all()

    return {
        "quiz_id": quiz_id,
        "attempts_count": len(attempts_list),
        "attempts": attempts_list
    }

@router.get("/quiz/{quiz_id}/documents/", response_model=None, tags=["Quiz Relationships"])
async def get_documents_of_quiz(quiz_id: str, database: Session = Depends(get_db)):
    """Get all PDFDocument entities related to this Quiz through documents"""
    db_quiz = database.query(Quiz).filter(Quiz.id == quiz_id).first()
    if db_quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")

    documents_list = database.query(PDFDocument).filter(PDFDocument.pDFDocumentQuiz_id == quiz_id).all()

    return {
        "quiz_id": quiz_id,
        "documents_count": len(documents_list),
        "documents": documents_list
    }

@router.get("/quiz/{quiz_id}/questions/", response_model=None, tags=["Quiz Relationships"])
async def get_questions_of_quiz(quiz_id: str, database: Session = Depends(get_db)):
    """Get all Question entities related to this Quiz through questions"""
    db_quiz = database.query(Quiz).filter(Quiz.id == quiz_id).first()
    if db_quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions_list = database.query(Question).filter(Question.quiz_id == quiz_id).all()

    return {
        "quiz_id": quiz_id,
        "questions_count": len(questions_list),
        "questions": questions_list
    }

@router.get("/quiz/{quiz_id}/pages/", response_model=None, tags=["Quiz Relationships"])
async def get_pages_of_quiz(quiz_id: str, database: Session = Depends(get_db)):
    """Get all QuizPage entities related to this Quiz through pages"""
    db_quiz = database.query(Quiz).filter(Quiz.id == quiz_id).first()
    if db_quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")

    pages_list = database.query(QuizPage).filter(QuizPage.quizPageQuiz_id == quiz_id).all()

    return {
        "quiz_id": quiz_id,
        "pages_count": len(pages_list),
        "pages": pages_list
    }


