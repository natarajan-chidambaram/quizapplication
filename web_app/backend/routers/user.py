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


@router.get("/user/", response_model=None, tags=["User"])
def get_all_user(detailed: bool = False, database: Session = Depends(get_db)) -> list:
    # Use detailed=true to get entities with eagerly loaded relationships (for tables with lookup columns)
    if detailed:
        # Eagerly load all relationships to avoid N+1 queries
        query = database.query(User)
        user_list = query.all()

        # Serialize with relationships included
        result = []
        for db_user in user_list:
            item_dict = db_user.__dict__.copy()
            item_dict.pop('_sa_instance_state', None)

            # Add many-to-one relationships (foreign keys for lookup columns)

            # Add many-to-many and one-to-many relationship objects (full details)
            related_attempt_list = database.query(Attempt).filter(Attempt.user_id == db_user.id).all()
            item_dict['attempts'] = []
            for related_attempt_obj in related_attempt_list:
                related_attempt_dict = related_attempt_obj.__dict__.copy()
                related_attempt_dict.pop('_sa_instance_state', None)
                item_dict['attempts'].append(related_attempt_dict)

            result.append(item_dict)
        return result
    else:
        # Default: return flat entities (faster for charts/widgets without lookup columns)
        return database.query(User).all()


@router.get("/user/count/", response_model=None, tags=["User"])
def get_count_user(database: Session = Depends(get_db)) -> dict:
    """Get the total count of User entities"""
    count = database.query(User).count()
    return {"count": count}


@router.get("/user/paginated/", response_model=None, tags=["User"])
def get_paginated_user(skip: int = 0, limit: int = 100, detailed: bool = False, database: Session = Depends(get_db)) -> dict:
    """Get paginated list of User entities"""
    total = database.query(User).count()
    user_list = database.query(User).offset(skip).limit(limit).all()
    # By default, return flat entities (for charts/widgets)
    # Use detailed=true to get entities with relationships
    if not detailed:
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": user_list
        }

    result = []
    for db_user in user_list:
        attempts_ids = database.query(Attempt.id).filter(Attempt.user_id == db_user.id).all()
        item_data = {
            "user": db_user,
            "attempts_ids": [x[0] for x in attempts_ids]        }
        result.append(item_data)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": result
    }
@router.get("/user/search/", response_model=None, tags=["User"])
def search_user(
    displayName: str = None,
    email: str = None,
    id: str = None,
    role: str = None,
    username: str = None,
    database: Session = Depends(get_db)
) -> list:
    """Search User entities by attributes"""
    query = database.query(User)

    if displayName is not None:
        query = query.filter(User.displayName.ilike(f"%{displayName}%"))
    if email is not None:
        query = query.filter(User.email.ilike(f"%{email}%"))
    if id is not None:
        query = query.filter(User.id.ilike(f"%{id}%"))
    if role is not None:
        query = query.filter(User.role.ilike(f"%{role}%"))
    if username is not None:
        query = query.filter(User.username.ilike(f"%{username}%"))

    results = query.all()
    return results


@router.get("/user/{user_id}/", response_model=None, tags=["User"])
async def get_user(user_id: str, database: Session = Depends(get_db)) -> User:
    db_user = database.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    attempts_ids = database.query(Attempt.id).filter(Attempt.user_id == db_user.id).all()
    response_data = {
        "user": db_user,
        "attempts_ids": [x[0] for x in attempts_ids]}
    return response_data



@router.post("/user/", response_model=None, tags=["User"])
async def create_user(user_data: UserCreate, database: Session = Depends(get_db)) -> User:


    db_user = User(
        displayName=user_data.displayName,        email=user_data.email,        role=user_data.role,        username=user_data.username        )

    database.add(db_user)
    database.flush()
    database.refresh(db_user)

    if user_data.attempts:
        # Validate that all Attempt IDs exist
        for related_attempt_id in user_data.attempts:
            related_attempt = database.query(Attempt).filter(Attempt.id == related_attempt_id).first()
            if not related_attempt:
                raise HTTPException(status_code=400, detail=f"Attempt with id {related_attempt_id} not found")

        # Update the related entities with the new foreign key
        database.query(Attempt).filter(Attempt.id.in_(user_data.attempts)).update(
            {Attempt.user_id: db_user.id}, synchronize_session=False
        )
        database.flush()




    attempts_ids = database.query(Attempt.id).filter(Attempt.user_id == db_user.id).all()
    response_data = {
        "user": db_user,
        "attempts_ids": [x[0] for x in attempts_ids]    }
    database.commit()
    database.refresh(db_user)
    return response_data


@router.post("/user/bulk/", response_model=None, tags=["User"])
async def bulk_create_user(items: list[UserCreate], database: Session = Depends(get_db)) -> dict:
    """Create multiple User entities at once"""
    if any(getattr(item, field, None) for item in items for field in ['attempts']):
        raise HTTPException(status_code=422, detail="Bulk creation of User with relationships is not supported; use POST /user/ to validate and persist its relationships")
    created_items = []
    errors = []

    for idx, item_data in enumerate(items):
        try:
            # Basic validation for each item

            db_user = User(
                displayName=item_data.displayName,                email=item_data.email,                role=item_data.role,                username=item_data.username            )
            database.add(db_user)
            database.flush()  # Get ID without committing
            created_items.append(db_user.id)
        except ValueError as e:
            errors.append({"index": idx, "error": str(e)})
        except IntegrityError as e:
            # The driver's text goes to the log; a failed flush ends the session's work.
            logger.error("Bulk creation of User failed at item %s: %s", idx, e)
            errors.append({"index": idx, "error": integrity_error_detail(e)})
            break

    if errors:
        database.rollback()
        raise HTTPException(status_code=400, detail={"message": "Bulk creation failed", "errors": errors})

    database.commit()
    return {
        "created_count": len(created_items),
        "created_ids": created_items,
        "message": f"Successfully created {len(created_items)} User entities"
    }


@router.delete("/user/bulk/", response_model=None, tags=["User"])
async def bulk_delete_user(ids: list[str], database: Session = Depends(get_db)) -> dict:
    """Delete multiple User entities at once"""
    # Aggregate deletion must account for every related lower bound. Until it
    # shares that validation, use the guarded individual delete endpoint.
    if ids:
        raise HTTPException(status_code=409, detail="Bulk deletion of User can violate required relationships and is not supported; use the individual DELETE /user/ endpoint")
    deleted_count = 0
    not_found = []

    for item_id in ids:
        db_user = database.query(User).filter(User.id == item_id).first()
        if db_user:
            conflict = user_delete_conflict(db_user)
            if conflict:
                raise HTTPException(status_code=409, detail="Cannot delete User " + str(item_id) + ": " + conflict)
            database.delete(db_user)
            deleted_count += 1
        else:
            not_found.append(item_id)

    database.commit()

    return {
        "deleted_count": deleted_count,
        "not_found": not_found,
        "message": f"Successfully deleted {deleted_count} User entities"
    }

@router.put("/user/{user_id}/", response_model=None, tags=["User"])
async def update_user(user_id: str, user_data: UserCreate, database: Session = Depends(get_db)) -> User:
    db_user = database.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    setattr(db_user, 'displayName', user_data.displayName)
    setattr(db_user, 'email', user_data.email)
    setattr(db_user, 'role', user_data.role)
    setattr(db_user, 'username', user_data.username)
    if user_data.attempts is not None:
        requested_attempts = set(user_data.attempts)
        current_attempts = {
            getattr(item, 'id')
            for item in database.query(Attempt).filter(Attempt.user_id == db_user.id).all()
        }
        attempts_to_detach = current_attempts - requested_attempts
        if attempts_to_detach:
            raise HTTPException(status_code=409, detail="Attempt " + ", ".join(str(item) for item in sorted(attempts_to_detach)) + " requires a user: reassign it instead of removing it")
        attempts_to_attach = requested_attempts - current_attempts
        for related_attempt_id in attempts_to_attach:
            related_attempt = database.query(Attempt).filter(Attempt.id == related_attempt_id).first()
            if not related_attempt:
                raise HTTPException(status_code=400, detail="Attempt with id " + str(related_attempt_id) + " not found")
        if attempts_to_attach:
            database.query(Attempt).filter(Attempt.id.in_(attempts_to_attach)).update(
                {Attempt.user_id: db_user.id}, synchronize_session=False
            )
    database.commit()
    database.refresh(db_user)

    attempts_ids = database.query(Attempt.id).filter(Attempt.user_id == db_user.id).all()
    response_data = {
        "user": db_user,
        "attempts_ids": [x[0] for x in attempts_ids]    }
    return response_data


def user_delete_conflict(db_user, deleting=None, wholes=()):
    """Why this User cannot be deleted (None when it can): a related record
    would be left without a link it requires. Covers the parts deleted with it;
    ``deleting`` holds every record of the delete, since none of them can block it,
    and ``wholes`` the records on the way down to this part."""
    if deleting is None:
        state = sa_inspect(db_user)
        deleting = [db_user] + [item[0] for item in state.mapper.cascade_iterator("delete", state)]
    related_attempts = db_user.attempts
    for related in (list(related_attempts) if isinstance(related_attempts, list) else [item for item in [related_attempts] if item is not None]):
        remaining = 0
        if related not in deleting and remaining < 1:
            return "Attempt " + str(getattr(related, 'id')) + " requires at least 1 user"
    return None


@router.delete("/user/{user_id}/", response_model=None, tags=["User"])
async def delete_user(user_id: str, database: Session = Depends(get_db)):
    db_user = database.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    conflict = user_delete_conflict(db_user)
    if conflict:
        raise HTTPException(status_code=409, detail="Cannot delete User " + str(user_id) + ": " + conflict)
    # Snapshot the columns before deleting: cascading the association-class
    # links loads relationship collections whose back-references would make
    # the JSON encoder recurse endlessly on the live object.
    deleted_user = {
        attr.key: getattr(db_user, attr.key)
        for attr in db_user.__mapper__.column_attrs
    }
    database.delete(db_user)
    database.commit()
    return deleted_user


@router.get("/user/{user_id}/attempts/", response_model=None, tags=["User Relationships"])
async def get_attempts_of_user(user_id: str, database: Session = Depends(get_db)):
    """Get all Attempt entities related to this User through attempts"""
    db_user = database.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    attempts_list = database.query(Attempt).filter(Attempt.user_id == user_id).all()

    return {
        "user_id": user_id,
        "attempts_count": len(attempts_list),
        "attempts": attempts_list
    }


