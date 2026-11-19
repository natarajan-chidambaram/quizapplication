import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body, File, UploadFile
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from pydantic_classes import *
from sql_alchemy import *
from database import get_db, integrity_error_detail
from bal_stdlib import *
from quiz_workflow import (
    DocumentValidationError,
    UPLOAD_DIR,
    detect_kind,
    parse_document,
    store_document,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/pdfdocument/upload/", response_model=None, tags=["PDFDocument"])
async def upload_pdfdocument(file: UploadFile = File(...), database: Session = Depends(get_db)):
    """Upload a JSON or PDF document of multiple-choice questions (R3-R7).

    The document is parsed and validated (>=2 options, exactly one correct
    answer per question) before anything is stored; an invalid document is
    rejected with 422 so the user cannot proceed (R5).
    """
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=422, detail="The uploaded file is empty")
    size = len(raw)
    if size > 10 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="The file is too large (max 10 MB)")
    try:
        kind = detect_kind(file.filename or "", file.content_type or "")
        parsed = parse_document(kind, raw)
        document, quiz, questions = store_document(database, file.filename or "document", kind, size, raw, parsed)
        database.commit()
    except DocumentValidationError as exc:
        database.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    except HTTPException:
        database.rollback()
        raise
    except Exception:
        database.rollback()
        logger.exception("Upload processing failed")
        raise HTTPException(status_code=500, detail="Upload processing failed")

    return {
        "document": {
            "id": document.id,
            "fileName": document.fileName,
            "contentType": document.contentType,
            "fileSizeBytes": document.fileSizeBytes,
            "storagePath": document.storagePath,
            "uploadDate": document.uploadDate.isoformat() if document.uploadDate else None,
            "pDFDocumentQuiz_id": document.pDFDocumentQuiz_id,
        },
        "quizId": quiz.id,
        "questionCount": len(questions),
    }


@router.get("/pdfdocument/{pdfdocument_id}/questions/", response_model=None, tags=["PDFDocument"])
def get_pdfdocument_questions(pdfdocument_id: str, database: Session = Depends(get_db)):
    """Questions + options extracted from an uploaded document (R6, R13)."""
    document = database.query(PDFDocument).filter(PDFDocument.id == pdfdocument_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="PDFDocument not found")
    questions = (
        database.query(Question)
        .filter(Question.quiz_id == document.pDFDocumentQuiz_id)
        .order_by(Question.orderIndex.asc(), Question.id.asc())
        .all()
    )
    return [
        {
            "id": q.id,
            "text": q.text,
            "explanation": q.explanation,
            "orderIndex": q.orderIndex,
            "options": [
                {
                    "id": o.id,
                    "optionText": o.optionText,
                    "optionOrder": o.optionOrder,
                }
                for o in sorted(
                    database.query(Option).filter(Option.question_id == q.id).all(),
                    key=lambda o: o.optionOrder,
                )
            ],
        }
        for q in questions
    ]



@router.get("/pdfdocument/", response_model=None, tags=["PDFDocument"])
def get_all_pdfdocument(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(PDFDocument)
        query = query.options(joinedload(PDFDocument.pDFDocumentQuiz))
        pdfdocument_list = query.all()

        # Serialize with relationships included
        result = []
        for db_pdfdocument in pdfdocument_list:
            item_dict = db_pdfdocument.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)
            if db_pdfdocument.pDFDocumentQuiz:
                related_obj = db_pdfdocument.pDFDocumentQuiz
                related_dict = related_obj.__dict__.copy()
                related_dict.pop('_sa_instance_state', None)
                item_dict['pDFDocumentQuiz'] = related_dict
            else:
                item_dict['pDFDocumentQuiz'] = None


            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(PDFDocument).all()


@router.get("/pdfdocument/count/", response_model=None, tags=["PDFDocument"])
def get_count_pdfdocument(database: Session = Depends(get_db)) -> dict:
    """Get the total count of PDFDocument entities"""
    count = database.query(PDFDocument).count()
    return {"count": count}


@router.get("/pdfdocument/paginated/", response_model=None, tags=["PDFDocument"])
def get_paginated_pdfdocument(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of PDFDocument entities"""
    total = database.query(PDFDocument).count()
    pdfdocument_list = database.query(PDFDocument).offset(skip).limit(limit).all()
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": pdfdocument_list
    }
@router.get("/pdfdocument/search/", response_model=None, tags=["PDFDocument"])
def search_pdfdocument(
    contentType: str = None,
    fileName: str = None,
    fileSizeBytes: int = None,
    id: str = None,
    storagePath: str = None,
    uploadedByUserId: str = None,
    database: Session = Depends(get_db)
) -> list:
    """Search PDFDocument entities by attributes"""
    query = database.query(PDFDocument)

    if contentType is not None:
        query = query.filter(PDFDocument.contentType.ilike(f"%{contentType}%"))
    if fileName is not None:
        query = query.filter(PDFDocument.fileName.ilike(f"%{fileName}%"))
    if fileSizeBytes is not None:
        query = query.filter(PDFDocument.fileSizeBytes == fileSizeBytes)
    if id is not None:
        query = query.filter(PDFDocument.id.ilike(f"%{id}%"))
    if storagePath is not None:
        query = query.filter(PDFDocument.storagePath.ilike(f"%{storagePath}%"))
    if uploadedByUserId is not None:
        query = query.filter(PDFDocument.uploadedByUserId.ilike(f"%{uploadedByUserId}%"))

    results = query.all()
    return results


@router.get("/pdfdocument/{pdfdocument_id}/", response_model=None, tags=["PDFDocument"])
async def get_pdfdocument(pdfdocument_id: str, database: Session = Depends(get_db)) -> PDFDocument:
    db_pdfdocument = database.query(PDFDocument).filter(PDFDocument.id == pdfdocument_id).first()
    if db_pdfdocument is None:
        raise HTTPException(status_code=404, detail="PDFDocument not found")

    response_data = {
        "pdfdocument": db_pdfdocument,
}
    return response_data



@router.post("/pdfdocument/", response_model=None, tags=["PDFDocument"])
async def create_pdfdocument(pdfdocument_data: PDFDocumentCreate, database: Session = Depends(get_db)) -> PDFDocument:

    if pdfdocument_data.pDFDocumentQuiz :
        related_pDFDocumentQuiz = database.query(Quiz).filter(Quiz.id == pdfdocument_data.pDFDocumentQuiz).first()
        if not related_pDFDocumentQuiz:
            raise HTTPException(status_code=400, detail="Quiz not found")

    db_pdfdocument = PDFDocument(
        contentType=pdfdocument_data.contentType,        fileName=pdfdocument_data.fileName,        fileSizeBytes=pdfdocument_data.fileSizeBytes,        storagePath=pdfdocument_data.storagePath,        uploadDate=pdfdocument_data.uploadDate,        uploadedByUserId=pdfdocument_data.uploadedByUserId,        pDFDocumentQuiz_id=pdfdocument_data.pDFDocumentQuiz        )

    database.add(db_pdfdocument)
    database.flush()
    database.refresh(db_pdfdocument)





    database.commit()
    database.refresh(db_pdfdocument)
    return db_pdfdocument


@router.post("/pdfdocument/bulk/", response_model=None, tags=["PDFDocument"])
async def bulk_create_pdfdocument(items: list[PDFDocumentCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple PDFDocument entities at once"""
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item

            db_pdfdocument = PDFDocument(
                contentType=item_data.contentType,                fileName=item_data.fileName,                fileSizeBytes=item_data.fileSizeBytes,                storagePath=item_data.storagePath,                uploadDate=item_data.uploadDate,                uploadedByUserId=item_data.uploadedByUserId,                pDFDocumentQuiz_id=item_data.pDFDocumentQuiz            )
            database.add(db_pdfdocument)
            database.flush()  # Get ID without committing
            created_items.append(db_pdfdocument.id)
        except ValueError as e:
            errors.append({"index": idx, "error": str(e)})
        except IntegrityError as e:
            # The driver's text goes to the log; a failed flush ends the session's work.
            logger.error("Bulk creation of PDFDocument failed at item %s: %s", idx, e)
            errors.append({"index": idx, "error": integrity_error_detail(e)})
            break

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} PDFDocument entities"
    }


@router.delete("/pdfdocument/bulk/", response_model=None, tags=["PDFDocument"])
async def bulk_delete_pdfdocument(ids: list[str], database: Session = Depends(get_db)) -> dict:
    """Delete multiple PDFDocument entities at once"""
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_pdfdocument = database.query(PDFDocument).filter(PDFDocument.id == item_id).first()
        if db_pdfdocument:
            conflict = pdfdocument_delete_conflict(db_pdfdocument)
            if conflict:
                raise HTTPException(status_code=409, detail="Cannot delete PDFDocument " + str(item_id) + ": " + conflict)
            database.delete(db_pdfdocument)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} PDFDocument entities"
    }

@router.put("/pdfdocument/{pdfdocument_id}/", response_model=None, tags=["PDFDocument"])
async def update_pdfdocument(pdfdocument_id: str, pdfdocument_data: PDFDocumentCreate, database: Session = Depends(get_db)) -> PDFDocument:
    db_pdfdocument = database.query(PDFDocument).filter(PDFDocument.id == pdfdocument_id).first()
    if db_pdfdocument is None:
        raise HTTPException(status_code=404, detail="PDFDocument not found")

    setattr(db_pdfdocument, 'contentType', pdfdocument_data.contentType)
    setattr(db_pdfdocument, 'fileName', pdfdocument_data.fileName)
    setattr(db_pdfdocument, 'fileSizeBytes', pdfdocument_data.fileSizeBytes)
    setattr(db_pdfdocument, 'storagePath', pdfdocument_data.storagePath)
    setattr(db_pdfdocument, 'uploadDate', pdfdocument_data.uploadDate)
    setattr(db_pdfdocument, 'uploadedByUserId', pdfdocument_data.uploadedByUserId)
    if pdfdocument_data.pDFDocumentQuiz is not None:
        related_pDFDocumentQuiz = database.query(Quiz).filter(Quiz.id == pdfdocument_data.pDFDocumentQuiz).first()
        if not related_pDFDocumentQuiz:
            raise HTTPException(status_code=400, detail="Quiz not found")
        setattr(db_pdfdocument, 'pDFDocumentQuiz_id', pdfdocument_data.pDFDocumentQuiz)
    else:
        setattr(db_pdfdocument, 'pDFDocumentQuiz_id', None)
    database.commit()
    database.refresh(db_pdfdocument)

    return db_pdfdocument


def pdfdocument_delete_conflict(db_pdfdocument, deleting=None, wholes=()):
    """Why this PDFDocument cannot be deleted (None when it can): a related record
    would be left without a link it requires. Covers the parts deleted with it;
    ``deleting`` holds every record of the delete, since none of them can block it,
    and ``wholes`` the records on the way down to this part."""
    if deleting is None:
        state = sa_inspect(db_pdfdocument)
        deleting = [db_pdfdocument] + [item[0] for item in state.mapper.cascade_iterator("delete", state)]
    return None


@router.delete("/pdfdocument/{pdfdocument_id}/", response_model=None, tags=["PDFDocument"])
async def delete_pdfdocument(pdfdocument_id: str, database: Session = Depends(get_db)):
    db_pdfdocument = database.query(PDFDocument).filter(PDFDocument.id == pdfdocument_id).first()
    if db_pdfdocument is None:
        raise HTTPException(status_code=404, detail="PDFDocument not found")
    conflict = pdfdocument_delete_conflict(db_pdfdocument)
    if conflict:
        raise HTTPException(status_code=409, detail="Cannot delete PDFDocument " + str(pdfdocument_id) + ": " + conflict)
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_pdfdocument = {
        attr.key: getattr(db_pdfdocument, attr.key)
        for attr in db_pdfdocument.__mapper__.column_attrs
    }
    database.delete(db_pdfdocument)
    database.commit()
    return deleted_pdfdocument



