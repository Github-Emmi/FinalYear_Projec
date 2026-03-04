"""
Base Repository - Generic CRUD operations for all models
"""

from typing import Generic, TypeVar, Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import DeclarativeBase

T = TypeVar('T', bound=DeclarativeBase)


class BaseRepository(Generic[T]):
    """
    Generic repository for CRUD operations.
    Handles basic Create, Read, Update, Delete operations for any SQLAlchemy model.
    """
    
    def __init__(self, db_session: AsyncSession, model: type[T]):
        self.db_session = db_session
        self.model = model
    
    # ==================== CREATE ====================
    async def create(self, obj_data: dict) -> T:
        """
        Create a new record in database.
        
        Args:
            obj_data: Dictionary with model field values
            
        Returns:
            Created model instance
            
        Example:
            new_student = await repo.create({
                "user_id": uuid123,
                "class_id": uuid456,
                "admission_number": "ADM2024001"
            })
        """
        db_obj = self.model(**obj_data)
        self.db_session.add(db_obj)
        await self.db_session.commit()
        await self.db_session.refresh(db_obj)
        return db_obj
    
    async def create_bulk(self, objects: List[dict]) -> List[T]:
        """
        Create multiple records in one transaction.
        
        Args:
            objects: List of dictionaries with model field values
            
        Returns:
            List of created model instances
        """
        db_objs = [self.model(**obj_data) for obj_data in objects]
        self.db_session.add_all(db_objs)
        await self.db_session.commit()
        
        # Refresh all objects to get IDs and timestamps
        for obj in db_objs:
            await self.db_session.refresh(obj)
        
        return db_objs
    
    # ==================== READ ====================
    async def get_by_id(self, id: UUID) -> Optional[T]:
        """
        Get single record by primary key ID.
        
        Args:
            id: UUID of the record
            
        Returns:
            Model instance or None if not found
            
        Example:
            student = await repo.get_by_id(uuid123)
        """
        return await self.db_session.get(self.model, id)
    
    async def list(self, skip: int = 0, limit: int = 20) -> tuple[List[T], int]:
        """
        Get paginated list of records.
        
        Args:
            skip: Number of records to skip (offset)
            limit: Number of records to return
            
        Returns:
            Tuple of (list of model instances, total count)
            
        Example:
            students, total = await repo.list(skip=0, limit=20)
            # Returns: First 20 students + total count
        """
        # Count total without pagination
        count_query = select(func.count(self.model.id))
        total = await self.db_session.scalar(count_query)
        
        # Get paginated results
        query = select(self.model).offset(skip).limit(limit)
        result = await self.db_session.execute(query)
        items = result.scalars().all()
        
        return items, total or 0
    
    async def get_all(self) -> List[T]:
        """
        Get all records without pagination.
        Use with caution on large tables!
        
        Returns:
            List of all model instances
        """
        query = select(self.model)
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def first(self) -> Optional[T]:
        """
        Get the first record.
        
        Returns:
            First model instance or None
        """
        query = select(self.model).limit(1)
        result = await self.db_session.execute(query)
        return result.scalars().first()
    
    async def count(self) -> int:
        """
        Get total count of records.
        
        Returns:
            Total number of records
        """
        count_query = select(func.count(self.model.id))
        total = await self.db_session.scalar(count_query)
        return total or 0
    
    # ==================== UPDATE ====================
    async def update(self, db_obj: T, obj_data: dict) -> T:
        """
        Update existing record.
        
        Args:
            db_obj: Model instance to update
            obj_data: Dictionary with fields to update
            
        Returns:
            Updated model instance
            
        Example:
            student = await repo.get_by_id(uuid123)
            updated = await repo.update(student, {"gpa": 3.8})
        """
        for key, value in obj_data.items():
            if hasattr(db_obj, key) and value is not None:
                setattr(db_obj, key, value)
        
        await self.db_session.commit()
        await self.db_session.refresh(db_obj)
        return db_obj
    
    async def update_by_id(self, id: UUID, obj_data: dict) -> Optional[T]:
        """
        Update record by ID.
        
        Args:
            id: UUID of record to update
            obj_data: Dictionary with fields to update
            
        Returns:
            Updated model instance or None if not found
        """
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return None
        
        return await self.update(db_obj, obj_data)
    
    # ==================== DELETE ====================
    async def delete(self, id: UUID) -> bool:
        """
        Soft delete - mark record as deleted without removing from DB.
        
        Args:
            id: UUID of record to delete
            
        Returns:
            True if deleted, False if not found
            
        Note:
            Only works if model has 'is_deleted' field.
            If not, falls back to hard delete.
        """
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return False
        
        # Soft delete if field exists
        if hasattr(db_obj, 'is_deleted'):
            db_obj.is_deleted = True
            await self.db_session.commit()
        else:
            # Hard delete if no is_deleted field
            await self.db_session.delete(db_obj)
            await self.db_session.commit()
        
        return True
    
    async def hard_delete(self, id: UUID) -> bool:
        """
        Permanently delete record from database.
        
        Args:
            id: UUID of record to delete
            
        Returns:
            True if deleted, False if not found
        """
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return False
        
        await self.db_session.delete(db_obj)
        await self.db_session.commit()
        return True
    
    async def delete_bulk(self, ids: List[UUID]) -> int:
        """
        Delete multiple records.
        
        Args:
            ids: List of UUIDs to delete
            
        Returns:
            Number of records deleted
        """
        count = 0
        for id in ids:
            if await self.delete(id):
                count += 1
        return count
    
    # ==================== EXISTS ====================
    async def exists(self, id: UUID) -> bool:
        """
        Check if record exists.
        
        Args:
            id: UUID to check
            
        Returns:
            True if exists, False otherwise
        """
        obj = await self.get_by_id(id)
        return obj is not None
    
    # ==================== FLUSH ====================
    async def flush(self) -> None:
        """Flush pending changes without commit"""
        await self.db_session.flush()
    
    async def commit(self) -> None:
        """Commit pending transaction"""
        await self.db_session.commit()
    
    async def rollback(self) -> None:
        """Rollback pending transaction"""
        await self.db_session.rollback()
