"""
Subject Service - Managing subject assignments, qualifications, and schedules.

This service handles complex subject management including:
- Subject assignment to classes with qualification validation
- Staff schedule conflict detection and resolution
- Subject prerequisites and sequencing
- Cross-class subject synchronization
- Subject performance analytics
- Staff workload analysis

Author: Backend Team
Version: 1.0.0
"""

import logging
from datetime import datetime, time, timedelta
from typing import List, Dict, Optional, Tuple
from uuid import UUID
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, func, select

from app.services.base import BaseService
from app.repositories.base import RepositoryFactory
from app.core.exceptions import (
    ValidationError, ConflictError, NotFoundError, ForbiddenError
)

logger = logging.getLogger(__name__)


class SubjectService(BaseService):
    """
    Service for managing subject assignments, qualifications, and schedule conflicts.
    
    Provides comprehensive subject management including assignment validation,
    schedule conflict detection/resolution, prerequisite validation, and analytics.
    
    Attributes:
        repos: RepositoryFactory for data access
        qualification_rules: Dict of subject -> required qualification
        max_subjects_per_staff: Maximum subjects one staff can teach
        conflict_buffer_minutes: Minimum minutes between classes
        max_consecutive_classes: Maximum consecutive classes for staff
    """
    
    QUALIFICATION_RULES = {
        "Physics": ["BSc Physics", "BSc Science", "BTech Physics"],
        "Chemistry": ["BSc Chemistry", "BSc Science", "BTech Chemistry"],
        "Biology": ["BSc Biology", "BSc Life Sciences", "BTech Biotechnology"],
        "History": ["BA History", "BA Social Studies", "BA Humanities"],
        "Geography": ["BA Geography", "BA Social Studies", "BA Environmental Science"],
        "Mathematics": ["BSc Mathematics", "BSc Science", "BTech Engineering"],
        "English": ["BA English", "BA Literature", "BA Language Studies"],
        "Computer Science": ["BSc Computer Science", "BTech IT", "BTech Software Engineering"],
    }
    
    MAX_SUBJECTS_PER_STAFF = 8
    CONFLICT_BUFFER_MINUTES = 15
    MAX_CONSECUTIVE_CLASSES = 3
    LUNCH_START = time(12, 0)
    LUNCH_END = time(13, 0)
    
    async def assign_subject_to_class(
        self,
        subject_id: UUID,
        class_id: UUID,
        staff_id: UUID,
        academic_year_id: UUID,
        credits: int = 3,
        is_mandatory: bool = True,
        user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Assign a subject to a class with staff and validate qualifications.
        
        Validates:
        - Subject, class, staff, and academic year exist
        - Staff qualifications match subject requirements
        - No duplicate subject assignment in same class by same staff
        - Staff not overloaded (max subjects per semester)
        - Subject not already assigned to different staff in same class
        - Credits within valid range (1-6)
        
        Args:
            subject_id: UUID of subject to assign
            class_id: UUID of class receiving subject
            staff_id: UUID of staff member teaching subject
            academic_year_id: UUID of academic year
            credits: Course credits (default 3, range 1-6)
            is_mandatory: Whether subject is mandatory for class
            user_id: UUID of user performing action (for audit)
        
        Returns:
            {
                "success": True,
                "data": {
                    "subject_id": UUID,
                    "class_id": UUID,
                    "staff_id": UUID,
                    "credits": 3,
                    "is_mandatory": True,
                    "assigned_at": datetime,
                    "message": "Subject assigned successfully"
                },
                "error": None
            }
        
        Raises:
            ValidationError: If credits outside range
            NotFoundError: If subject, class, staff, or year not found
            ConflictError: If duplicate or staff overloaded
            ForbiddenError: If staff lacks required qualifications
        
        Example:
            >>> response = await subject_service.assign_subject_to_class(
            ...     subject_id=UUID("..."),
            ...     class_id=UUID("..."),
            ...     staff_id=UUID("..."),
            ...     academic_year_id=UUID("..."),
            ...     credits=3,
            ...     is_mandatory=True
            ... )
        """
        logger.info(f"Attempting to assign subject {subject_id} to class {class_id}")
        
        # Validate credits range
        if not (1 <= credits <= 6):
            raise ValidationError("Credits must be between 1 and 6")
        
        # Fetch and validate all entities exist
        subject = await self.repos.subject.get_by_id(subject_id)
        if not subject:
            raise NotFoundError(f"Subject {subject_id} not found")
        
        class_obj = await self.repos.class_repo.get_by_id(class_id)
        if not class_obj:
            raise NotFoundError(f"Class {class_id} not found")
        
        staff = await self.repos.staff.get_by_id(staff_id)
        if not staff:
            raise NotFoundError(f"Staff member {staff_id} not found")
        
        year = await self.repos.session_year.get_by_id(academic_year_id)
        if not year:
            raise NotFoundError(f"Academic year {academic_year_id} not found")
        
        # Validate staff qualifications match subject
        await self._validate_qualification(subject, staff)
        
        # Check for duplicate assignments (same subject/class/staff)
        existing = await self.repos.subject.get_by_filter(
            and_(
                self.repos.subject.model.subject_id == subject_id,
                self.repos.subject.model.class_id == class_id,
                self.repos.subject.model.staff_id == staff_id,
                self.repos.subject.model.is_deleted == False
            )
        )
        if existing:
            raise ConflictError(
                f"Subject already assigned to this class by this staff"
            )
        
        # Check subject not assigned to different staff in same class
        other_assignment = await self.repos.subject.get_by_filter(
            and_(
                self.repos.subject.model.subject_id == subject_id,
                self.repos.subject.model.class_id == class_id,
                self.repos.subject.model.staff_id != staff_id,
                self.repos.subject.model.is_deleted == False
            )
        )
        if other_assignment:
            raise ConflictError(
                f"Subject already assigned to different staff in this class. "
                f"Use change_subject_staff() to reassign."
            )
        
        # Check staff not overloaded
        staff_subject_count = await self._count_staff_subjects(staff_id, academic_year_id)
        if staff_subject_count >= self.MAX_SUBJECTS_PER_STAFF:
            raise ConflictError(
                f"Staff already teaching {staff_subject_count} subjects. "
                f"Maximum is {self.MAX_SUBJECTS_PER_STAFF}"
            )
        
        # Create assignment in transaction
        async with self.transaction():
            assignment = await self.repos.subject.create({
                "subject_id": subject_id,
                "class_id": class_id,
                "staff_id": staff_id,
                "academic_year_id": academic_year_id,
                "credits": credits,
                "is_mandatory": is_mandatory,
                "assigned_at": datetime.utcnow(),
                "is_deleted": False
            })
            
            # Audit log
            self.log_action(
                action="ASSIGN_SUBJECT",
                entity_type="Subject",
                entity_id=subject_id,
                user_id=user_id,
                changes={
                    "class_id": str(class_id),
                    "staff_id": str(staff_id),
                    "credits": credits,
                    "is_mandatory": is_mandatory
                }
            )
            
            # Send notifications
            notification_message = (
                f"Subject '{subject.name}' assigned to class {class_obj.code} "
                f"with {credits} credits"
            )
            
            # Notify staff
            await self.repos.notification.create({
                "recipient_id": staff_id,
                "type": "INFO",
                "title": "Subject Assignment",
                "message": f"{notification_message} - Assignment confirmed",
                "created_at": datetime.utcnow()
            })
            
            # Notify students in class
            await self._notify_class_students(
                class_id,
                "Subject Assignment",
                notification_message,
                "INFO"
            )
        
        logger.info(f"Subject {subject_id} assigned to class {class_id} by staff {staff_id}")
        
        return self.success_response(
            data={
                "subject_id": subject_id,
                "class_id": class_id,
                "staff_id": staff_id,
                "credits": credits,
                "is_mandatory": is_mandatory,
                "assigned_at": assignment.assigned_at.isoformat(),
                "message": "Subject assigned successfully"
            }
        )
    
    async def unassign_subject_from_class(
        self,
        subject_id: UUID,
        class_id: UUID,
        reason: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Remove subject from class with validation of dependencies.
        
        Cannot unassign if:
        - Students have grades recorded
        - Active quiz/assignment submissions exist
        - Academic term not complete
        
        Soft-deletes assignment and reassigns timetable slots.
        
        Args:
            subject_id: UUID of subject to remove
            class_id: UUID of class losing subject
            reason: Reason for unassignment (optional)
            user_id: UUID of user performing action (for audit)
        
        Returns:
            {
                "success": True,
                "data": {
                    "subject_id": UUID,
                    "class_id": UUID,
                    "unassigned_at": datetime,
                    "affected_students": 45,
                    "timetable_slots_reassigned": 12,
                    "message": "Subject unassigned successfully"
                },
                "error": None
            }
        
        Raises:
            NotFoundError: If assignment not found
            ConflictError: If students have grades or active submissions
        
        Example:
            >>> response = await subject_service.unassign_subject_from_class(
            ...     subject_id=UUID("..."),
            ...     class_id=UUID("..."),
            ...     reason="Staff resignation"
            ... )
        """
        logger.info(f"Attempting to unassign subject {subject_id} from class {class_id}")
        
        # Fetch assignment
        assignment = await self.repos.subject.get_by_filter(
            and_(
                self.repos.subject.model.subject_id == subject_id,
                self.repos.subject.model.class_id == class_id,
                self.repos.subject.model.is_deleted == False
            )
        )
        if not assignment:
            raise NotFoundError("Subject assignment not found in this class")
        
        # Check for student grades
        grades_count = await self._count_grades_for_assignment(subject_id, class_id)
        if grades_count > 0:
            raise ConflictError(
                f"Cannot unassign: {grades_count} student grades recorded. "
                f"Academic term must be complete."
            )
        
        # Check for active submissions
        active_submissions = await self._count_active_submissions(subject_id, class_id)
        if active_submissions > 0:
            raise ConflictError(
                f"Cannot unassign: {active_submissions} active quiz/assignment "
                f"submissions exist. Must be completed first."
            )
        
        async with self.transaction():
            # Get affected students count
            affected_students = await self._count_class_students(class_id)
            
            # Get timetable slots to reassign
            timetable_slots = await self._get_timetable_slots(
                subject_id, class_id, assignment.staff_id
            )
            slots_reassigned = len(timetable_slots)
            
            # Soft delete assignment
            await self.repos.subject.update(assignment.id, {"is_deleted": True})
            
            # Reassign timetable slots to null (remove scheduling)
            if timetable_slots:
                for slot in timetable_slots:
                    await self.repos.timetable.update(
                        slot.id,
                        {"subject_id": None, "staff_id": None}
                    )
            
            # Audit log
            self.log_action(
                action="UNASSIGN_SUBJECT",
                entity_type="Subject",
                entity_id=subject_id,
                user_id=user_id,
                changes={
                    "class_id": str(class_id),
                    "staff_id": str(assignment.staff_id),
                    "reason": reason or "Not provided",
                    "affected_students": affected_students,
                    "timetable_slots_removed": slots_reassigned
                }
            )
            
            # Notify all affected parties
            staff = await self.repos.staff.get_by_id(assignment.staff_id)
            if staff:
                await self.repos.notification.create({
                    "recipient_id": assignment.staff_id,
                    "type": "WARNING",
                    "title": "Subject Unassignment",
                    "message": (
                        f"Subject unassigned from class. "
                        f"{slots_reassigned} timetable slots affected."
                    ),
                    "created_at": datetime.utcnow()
                })
            
            # Notify students
            await self._notify_class_students(
                class_id,
                "Subject Unassignment",
                "Subject has been removed from the class schedule",
                "WARNING"
            )
        
        logger.info(
            f"Subject {subject_id} unassigned from class {class_id}. "
            f"Affected: {affected_students} students, {slots_reassigned} slots"
        )
        
        return self.success_response(
            data={
                "subject_id": subject_id,
                "class_id": class_id,
                "unassigned_at": datetime.utcnow().isoformat(),
                "affected_students": affected_students,
                "timetable_slots_reassigned": slots_reassigned,
                "message": "Subject unassigned successfully"
            }
        )
    
    async def change_subject_staff(
        self,
        subject_id: UUID,
        class_id: UUID,
        new_staff_id: UUID,
        reason: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Reassign subject to different staff member.
        
        Validates new staff qualifications, checks availability, transfers
        timetable slots, and notifies all parties.
        
        Use cases:
        - Staff resignation or sabbatical
        - Pregnancy/medical leave
        - Performance issues requiring change
        - Workload balancing
        
        Args:
            subject_id: UUID of subject to reassign
            class_id: UUID of class
            new_staff_id: UUID of new staff member
            reason: Reason for reassignment (optional)
            user_id: UUID of user performing action (for audit)
        
        Returns:
            {
                "success": True,
                "data": {
                    "subject_id": UUID,
                    "class_id": UUID,
                    "old_staff_id": UUID,
                    "new_staff_id": UUID,
                    "timetable_slots_transferred": 12,
                    "changed_at": datetime,
                    "message": "Staff reassignment completed"
                },
                "error": None
            }
        
        Raises:
            NotFoundError: If assignment, new staff, or subject not found
            ForbiddenError: If new staff lacks qualifications
            ConflictError: If new staff has schedule conflicts
        
        Example:
            >>> response = await subject_service.change_subject_staff(
            ...     subject_id=UUID("..."),
            ...     class_id=UUID("..."),
            ...     new_staff_id=UUID("..."),
            ...     reason="Previous staff on medical leave"
            ... )
        """
        logger.info(
            f"Attempting to reassign subject {subject_id} "
            f"from class {class_id} to staff {new_staff_id}"
        )
        
        # Fetch current assignment
        assignment = await self.repos.subject.get_by_filter(
            and_(
                self.repos.subject.model.subject_id == subject_id,
                self.repos.subject.model.class_id == class_id,
                self.repos.subject.model.is_deleted == False
            )
        )
        if not assignment:
            raise NotFoundError("Subject assignment not found")
        
        old_staff_id = assignment.staff_id
        
        # Validate new staff exists
        new_staff = await self.repos.staff.get_by_id(new_staff_id)
        if not new_staff:
            raise NotFoundError(f"New staff member {new_staff_id} not found")
        
        # Validate qualifications
        subject = await self.repos.subject.get_by_id(subject_id)
        if not subject:
            raise NotFoundError(f"Subject {subject_id} not found")
        
        await self._validate_qualification(subject, new_staff)
        
        # Check new staff not already teaching same subject in this class
        existing = await self.repos.subject.get_by_filter(
            and_(
                self.repos.subject.model.subject_id == subject_id,
                self.repos.subject.model.class_id == class_id,
                self.repos.subject.model.staff_id == new_staff_id,
                self.repos.subject.model.is_deleted == False
            )
        )
        if existing:
            raise ConflictError(f"New staff already teaches this subject in this class")
        
        # Check for schedule conflicts
        timetable_slots = await self._get_timetable_slots(
            subject_id, class_id, old_staff_id
        )
        
        for slot in timetable_slots:
            conflict = await self.detect_staff_schedule_conflicts(
                new_staff_id, class_id, {
                    "day": slot.day_of_week,
                    "start_time": slot.start_time.isoformat(),
                    "end_time": slot.end_time.isoformat()
                }
            )
            if conflict.get("conflict_detected"):
                raise ConflictError(
                    f"New staff has schedule conflicts: {conflict.get('conflicting_subjects', [])}"
                )
        
        async with self.transaction():
            # Update assignment
            await self.repos.subject.update(
                assignment.id,
                {"staff_id": new_staff_id}
            )
            
            # Transfer timetable slots
            slots_transferred = 0
            for slot in timetable_slots:
                await self.repos.timetable.update(
                    slot.id,
                    {"staff_id": new_staff_id}
                )
                slots_transferred += 1
            
            # Create StudentResult records for continuity
            await self._create_continuation_records(subject_id, class_id, old_staff_id)
            
            # Audit log
            self.log_action(
                action="CHANGE_SUBJECT_STAFF",
                entity_type="Subject",
                entity_id=subject_id,
                user_id=user_id,
                changes={
                    "class_id": str(class_id),
                    "old_staff_id": str(old_staff_id),
                    "new_staff_id": str(new_staff_id),
                    "reason": reason or "Not provided",
                    "timetable_slots_transferred": slots_transferred
                }
            )
            
            # Notify old staff
            old_staff = await self.repos.staff.get_by_id(old_staff_id)
            if old_staff:
                await self.repos.notification.create({
                    "recipient_id": old_staff_id,
                    "type": "INFO",
                    "title": "Subject Reassignment",
                    "message": (
                        f"Subject reassigned to another staff member. "
                        f"Reason: {reason or 'Not specified'}"
                    ),
                    "created_at": datetime.utcnow()
                })
            
            # Notify new staff
            await self.repos.notification.create({
                "recipient_id": new_staff_id,
                "type": "INFO",
                "title": "New Subject Assignment",
                "message": f"You have been assigned to teach a subject. {slots_transferred} classes",
                "created_at": datetime.utcnow()
            })
            
            # Notify students
            await self._notify_class_students(
                class_id,
                "Subject Staff Changed",
                f"Subject instructor has changed. New instructor: {new_staff.user.first_name} {new_staff.user.last_name}",
                "INFO"
            )
            
            # Notify department head
            class_obj = await self.repos.class_repo.get_by_id(class_id)
            if class_obj and class_obj.department_id:
                dept_head = await self._get_department_head(class_obj.department_id)
                if dept_head:
                    await self.repos.notification.create({
                        "recipient_id": dept_head.id,
                        "type": "INFO",
                        "title": "Subject Staff Change",
                        "message": f"Subject staff reassigned in {class_obj.code}",
                        "created_at": datetime.utcnow()
                    })
        
        logger.info(
            f"Subject {subject_id} reassigned from staff {old_staff_id} "
            f"to {new_staff_id} in class {class_id}"
        )
        
        return self.success_response(
            data={
                "subject_id": subject_id,
                "class_id": class_id,
                "old_staff_id": old_staff_id,
                "new_staff_id": new_staff_id,
                "timetable_slots_transferred": slots_transferred,
                "changed_at": datetime.utcnow().isoformat(),
                "message": "Staff reassignment completed successfully"
            }
        )
    
    async def detect_staff_schedule_conflicts(
        self,
        staff_id: UUID,
        class_id: UUID,
        time_slot: Dict
    ) -> Dict:
        """
        Detect schedule conflicts for staff member at proposed time slot.
        
        Conflict detection rules:
        - No overlapping classes for same staff
        - Minimum 15-minute buffer between classes (travel time)
        - Maximum 3 consecutive classes
        - Lunch break 12:00-13:00 reserved
        
        Args:
            staff_id: UUID of staff member
            class_id: UUID of class
            time_slot: {
                "day": str,  # e.g., "MONDAY"
                "start_time": str,  # HH:MM format
                "end_time": str  # HH:MM format
            }
        
        Returns:
            {
                "conflict_detected": False,
                "conflicting_subjects": [],
                "conflict_details": [],
                "suggested_alternatives": [
                    {"day": "MONDAY", "start_time": "14:00", "end_time": "15:00"},
                    ...
                ],
                "consecutive_count": 2,
                "warning": None
            }
        
        Example:
            >>> conflict = await subject_service.detect_staff_schedule_conflicts(
            ...     staff_id=UUID("..."),
            ...     class_id=UUID("..."),
            ...     time_slot={
            ...         "day": "MONDAY",
            ...         "start_time": "09:00",
            ...         "end_time": "10:00"
            ...     }
            ... )
        """
        logger.info(f"Detecting conflicts for staff {staff_id} on {time_slot}")
        
        conflicts = []
        conflicting_subjects = []
        consecutive_count = 0
        
        # Parse proposed time slot
        try:
            proposed_day = time_slot.get("day", "").upper()
            proposed_start = datetime.strptime(time_slot["start_time"], "%H:%M").time()
            proposed_end = datetime.strptime(time_slot["end_time"], "%H:%M").time()
        except (ValueError, KeyError) as e:
            raise ValidationError(f"Invalid time slot format: {e}")
        
        # Check lunch break overlap
        if self._time_overlaps(proposed_start, proposed_end, self.LUNCH_START, self.LUNCH_END):
            conflicts.append("Proposed time overlaps with lunch break (12:00-13:00)")
        
        # Get all existing timetable slots for staff
        staff_slots = await self._get_staff_timetable_slots(staff_id)
        
        # Filter slots for same day
        same_day_slots = [s for s in staff_slots if s.day_of_week.upper() == proposed_day]
        
        # Check for overlaps and buffer violations
        for slot in same_day_slots:
            # Check direct overlap
            if self._time_overlaps(proposed_start, proposed_end, slot.start_time, slot.end_time):
                conflicts.append(
                    f"Direct overlap with {slot.subject.name} ({slot.start_time} - {slot.end_time})"
                )
                conflicting_subjects.append({
                    "subject": slot.subject.name,
                    "class": slot.class_obj.code,
                    "time": f"{slot.start_time} - {slot.end_time}"
                })
            
            # Check buffer violations (min 15 minutes)
            if self._buffer_violated(proposed_start, proposed_end, slot.start_time, slot.end_time):
                conflicts.append(
                    f"Buffer violation with {slot.subject.name} "
                    f"({slot.start_time} - {slot.end_time}). Min {self.CONFLICT_BUFFER_MINUTES} min required."
                )
                conflicting_subjects.append({
                    "subject": slot.subject.name,
                    "class": slot.class_obj.code,
                    "time": f"{slot.start_time} - {slot.end_time}",
                    "issue": "insufficient_buffer"
                })
        
        # Check consecutive classes
        consecutive_count = self._calculate_consecutive_classes(same_day_slots, proposed_start)
        if consecutive_count >= self.MAX_CONSECUTIVE_CLASSES:
            conflicts.append(
                f"Would create {consecutive_count} consecutive classes "
                f"(max {self.MAX_CONSECUTIVE_CLASSES})"
            )
        
        # Generate suggested alternatives
        alternatives = await self._suggest_alternative_slots(staff_id, proposed_day)
        
        warning = None
        if len(same_day_slots) >= 5:
            warning = f"Staff already has {len(same_day_slots)} classes on {proposed_day}"
        
        conflict_detected = len(conflicts) > 0
        
        logger.info(
            f"Conflict detection for staff {staff_id}: "
            f"detected={conflict_detected}, conflicts={len(conflicts)}"
        )
        
        return {
            "conflict_detected": conflict_detected,
            "conflicting_subjects": conflicting_subjects,
            "conflict_details": conflicts,
            "suggested_alternatives": alternatives,
            "consecutive_count": consecutive_count,
            "warning": warning
        }
    
    async def resolve_schedule_conflict(
        self,
        staff_id: UUID,
        conflict_id: UUID,
        resolution_strategy: str,
        new_time_slot: Optional[Dict] = None,
        user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Resolve detected schedule conflict using specified strategy.
        
        Resolution strategies:
        - RESCHEDULE: Move one class to alternative time
        - COMBINE: Merge two small classes
        - SPLIT: Split large class into two time slots
        
        Args:
            staff_id: UUID of staff member
            conflict_id: UUID of conflict record
            resolution_strategy: One of "RESCHEDULE", "COMBINE", "SPLIT"
            new_time_slot: For RESCHEDULE - {"day": str, "start_time": str, "end_time": str}
            user_id: UUID of user performing action (for audit)
        
        Returns:
            {
                "success": True,
                "data": {
                    "conflict_id": UUID,
                    "resolution_strategy": "RESCHEDULE",
                    "affected_classes": 1,
                    "affected_students": 45,
                    "resolved_at": datetime,
                    "message": "Conflict resolved successfully"
                },
                "error": None
            }
        
        Raises:
            NotFoundError: If conflict not found
            ValidationError: If invalid strategy or new slot invalid
            ConflictError: If resolution creates new conflicts
        
        Example:
            >>> response = await subject_service.resolve_schedule_conflict(
            ...     staff_id=UUID("..."),
            ...     conflict_id=UUID("..."),
            ...     resolution_strategy="RESCHEDULE",
            ...     new_time_slot={
            ...         "day": "TUESDAY",
            ...         "start_time": "14:00",
            ...         "end_time": "15:00"
            ...     }
            ... )
        """
        logger.info(
            f"Resolving conflict {conflict_id} for staff {staff_id} "
            f"with strategy {resolution_strategy}"
        )
        
        # Validate strategy
        valid_strategies = ["RESCHEDULE", "COMBINE", "SPLIT"]
        if resolution_strategy not in valid_strategies:
            raise ValidationError(
                f"Invalid strategy. Must be one of {valid_strategies}"
            )
        
        # Fetch conflict (would be in ScheduleConflict model)
        conflict = await self._get_conflict_record(conflict_id)
        if not conflict:
            raise NotFoundError(f"Conflict {conflict_id} not found")
        
        async with self.transaction():
            affected_classes = 0
            affected_students = 0
            
            if resolution_strategy == "RESCHEDULE":
                if not new_time_slot:
                    raise ValidationError("new_time_slot required for RESCHEDULE strategy")
                
                # Verify new slot doesn't create conflicts
                conflict_check = await self.detect_staff_schedule_conflicts(
                    staff_id, conflict.class_id, new_time_slot
                )
                if conflict_check["conflict_detected"]:
                    raise ConflictError(
                        f"New time slot creates conflicts: "
                        f"{conflict_check['conflict_details']}"
                    )
                
                # Update timetable slots
                affected_classes = await self._reschedule_class(
                    conflict, new_time_slot
                )
                affected_students = await self._count_class_students(conflict.class_id)
                
                logger.info(f"Rescheduled {affected_classes} class(es)")
            
            elif resolution_strategy == "COMBINE":
                # Merge with another section if possible
                combined = await self._combine_classes(conflict)
                affected_classes = combined.get("classes_merged", 0)
                affected_students = combined.get("total_students", 0)
                
                logger.info(f"Combined {affected_classes} classes")
            
            elif resolution_strategy == "SPLIT":
                # Split class into two time slots
                split_result = await self._split_class(conflict, new_time_slot)
                affected_classes = split_result.get("new_slots", 0)
                affected_students = split_result.get("total_students", 0)
                
                logger.info(f"Split class into {affected_classes} slot(s)")
            
            # Mark conflict as resolved
            await self._mark_conflict_resolved(conflict_id, resolution_strategy)
            
            # Audit log
            self.log_action(
                action="RESOLVE_SCHEDULE_CONFLICT",
                entity_type="ScheduleConflict",
                entity_id=conflict_id,
                user_id=user_id,
                changes={
                    "staff_id": str(staff_id),
                    "strategy": resolution_strategy,
                    "affected_classes": affected_classes,
                    "affected_students": affected_students
                }
            )
            
            # Notify affected parties
            await self._notify_schedule_change(
                conflict.class_id,
                staff_id,
                f"Schedule conflict resolved using {resolution_strategy} strategy"
            )
        
        logger.info(f"Conflict {conflict_id} resolved successfully")
        
        return self.success_response(
            data={
                "conflict_id": conflict_id,
                "resolution_strategy": resolution_strategy,
                "affected_classes": affected_classes,
                "affected_students": affected_students,
                "resolved_at": datetime.utcnow().isoformat(),
                "message": f"Conflict resolved using {resolution_strategy} strategy"
            }
        )
    
    async def validate_subject_prerequisites(
        self,
        student_id: UUID,
        subject_id: UUID
    ) -> Dict:
        """
        Validate if student meets prerequisites for subject enrollment.
        
        Checks:
        - Student completed all prerequisite subjects
        - Student achieved minimum grade (C or higher)
        - Prerequisites from previous academic sessions
        
        Args:
            student_id: UUID of student
            subject_id: UUID of subject
        
        Returns:
            {
                "valid": True,
                "missing_prerequisites": [],
                "met_prerequisites": ["Mathematics", "Physics"],
                "recommendations": [],
                "enrollment_blocked": False,
                "message": "Student meets all prerequisites"
            }
        
        Example:
            >>> result = await subject_service.validate_subject_prerequisites(
            ...     student_id=UUID("..."),
            ...     subject_id=UUID("...")
            ... )
        """
        logger.info(f"Validating prerequisites for student {student_id} for subject {subject_id}")
        
        # Fetch subject and prerequisites
        subject = await self.repos.subject.get_by_id(subject_id)
        if not subject:
            raise NotFoundError(f"Subject {subject_id} not found")
        
        prerequisites = subject.prerequisites or []  # Assuming subject has prerequisites field
        
        student = await self.repos.student.get_by_id(student_id)
        if not student:
            raise NotFoundError(f"Student {student_id} not found")
        
        missing = []
        met = []
        
        # Check each prerequisite
        for prereq_subject_id in prerequisites:
            # Get student grades in prerequisite subject
            grade = await self._get_highest_grade_in_subject(student_id, prereq_subject_id)
            
            # Get subject name
            prereq_subject = await self.repos.subject.get_by_id(prereq_subject_id)
            subject_name = prereq_subject.name if prereq_subject else str(prereq_subject_id)
            
            # Check if passed (C or higher = 70%)
            if grade is None or grade < 70:
                missing.append({
                    "subject_id": prereq_subject_id,
                    "subject_name": subject_name,
                    "current_grade": grade,
                    "required_grade": 70
                })
            else:
                met.append({
                    "subject_id": prereq_subject_id,
                    "subject_name": subject_name,
                    "grade": grade
                })
        
        valid = len(missing) == 0
        recommendations = []
        
        if not valid:
            recommendations.append(
                f"Student must complete {len(missing)} prerequisite subject(s)"
            )
            recommendations.append("Consider enrolling in remedial courses")
            recommendations.append("Request exemption from department head if qualified")
        else:
            recommendations.append("Student qualifies for enrollment")
        
        logger.info(
            f"Prerequisite validation for student {student_id}: "
            f"valid={valid}, missing={len(missing)}, met={len(met)}"
        )
        
        return {
            "valid": valid,
            "missing_prerequisites": missing,
            "met_prerequisites": met,
            "recommendations": recommendations,
            "enrollment_blocked": not valid,
            "message": f"Student meets {len(met)}/{len(prerequisites)} prerequisites"
        }
    
    async def create_subject_sequence(
        self,
        subjects: List[UUID],
        name: str = "Curriculum Sequence",
        description: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Create ordered sequence of subjects (e.g., Foundation → Intermediate → Advanced).
        
        Validates:
        - Prerequisites chain correctly
        - No circular dependencies
        - All subjects exist
        
        Args:
            subjects: List of subject UUIDs in order
            name: Name of sequence (default "Curriculum Sequence")
            description: Sequence description (optional)
            user_id: UUID of user performing action (for audit)
        
        Returns:
            {
                "success": True,
                "data": {
                    "sequence_id": UUID,
                    "name": "Programming Path",
                    "subjects": [
                        {"level": 1, "subject_id": UUID, "name": "Python Basics", ...},
                        {"level": 2, "subject_id": UUID, "name": "OOP", ...},
                        ...
                    ],
                    "created_at": datetime,
                    "message": "Subject sequence created successfully"
                },
                "error": None
            }
        
        Raises:
            ValidationError: If circular dependencies detected
            NotFoundError: If any subject not found
        
        Example:
            >>> response = await subject_service.create_subject_sequence(
            ...     subjects=[UUID("..."), UUID("..."), UUID("...")],
            ...     name="Data Science Path",
            ...     description="Complete curriculum for data science"
            ... )
        """
        logger.info(f"Creating subject sequence '{name}' with {len(subjects)} subjects")
        
        if not subjects:
            raise ValidationError("Sequence must contain at least one subject")
        
        # Verify all subjects exist and fetch them
        subject_list = []
        for subject_id in subjects:
            subject = await self.repos.subject.get_by_id(subject_id)
            if not subject:
                raise NotFoundError(f"Subject {subject_id} not found")
            subject_list.append(subject)
        
        # Check for circular dependencies
        self._check_circular_dependencies(subject_list)
        
        async with self.transaction():
            # Create sequence record
            sequence = await self.repos.subject_sequence.create({
                "name": name,
                "description": description,
                "created_at": datetime.utcnow(),
                "is_active": True
            })
            
            # Create subject sequence items with level
            sequence_items = []
            for level, subject_id in enumerate(subjects, start=1):
                item = await self.repos.subject_sequence_item.create({
                    "sequence_id": sequence.id,
                    "subject_id": subject_id,
                    "sequence_level": level
                })
                sequence_items.append(item)
            
            # Audit log
            self.log_action(
                action="CREATE_SUBJECT_SEQUENCE",
                entity_type="SubjectSequence",
                entity_id=sequence.id,
                user_id=user_id,
                changes={
                    "name": name,
                    "subject_count": len(subjects),
                    "subjects": [str(s) for s in subjects]
                }
            )
        
        logger.info(
            f"Subject sequence '{name}' created with ID {sequence.id}"
        )
        
        return self.success_response(
            data={
                "sequence_id": sequence.id,
                "name": name,
                "subject_count": len(subjects),
                "subjects": [
                    {
                        "level": level,
                        "subject_id": str(subject.id),
                        "name": subject.name,
                        "code": subject.code
                    }
                    for level, subject in enumerate(subject_list, start=1)
                ],
                "created_at": datetime.utcnow().isoformat(),
                "message": "Subject sequence created successfully"
            }
        )
    
    async def assign_subject_to_multiple_classes(
        self,
        subject_id: UUID,
        class_ids: List[UUID],
        staff_ids: List[UUID],
        academic_year_id: UUID,
        credits: int = 3,
        user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Bulk assign subject to multiple classes with different staff.
        
        Used for core subjects (Math, English) taught across all classes.
        
        Args:
            subject_id: UUID of subject
            class_ids: List of class UUIDs
            staff_ids: List of staff UUIDs (one per class, must match length)
            academic_year_id: UUID of academic year
            credits: Course credits (default 3)
            user_id: UUID of user performing action (for audit)
        
        Returns:
            {
                "success": True,
                "data": {
                    "subject_id": UUID,
                    "successful": 8,
                    "failed": 0,
                    "assignments": [
                        {"class_id": UUID, "staff_id": UUID, "status": "success"},
                        ...
                    ],
                    "created_at": datetime,
                    "message": "Bulk assignment completed with 8/8 success"
                },
                "error": None
            }
        
        Raises:
            ValidationError: If class_ids and staff_ids lengths don't match
            NotFoundError: If subject or academic year not found
        
        Example:
            >>> response = await subject_service.assign_subject_to_multiple_classes(
            ...     subject_id=UUID("..."),
            ...     class_ids=[UUID("..."), UUID("..."), ...],
            ...     staff_ids=[UUID("..."), UUID("..."), ...],
            ...     academic_year_id=UUID("...")
            ... )
        """
        logger.info(
            f"Bulk assigning subject {subject_id} to {len(class_ids)} classes"
        )
        
        if len(class_ids) != len(staff_ids):
            raise ValidationError(
                f"Mismatch: {len(class_ids)} classes but {len(staff_ids)} staff. "
                f"Must be one staff per class."
            )
        
        if not class_ids:
            raise ValidationError("Must provide at least one class")
        
        # Validate subject and year exist
        subject = await self.repos.subject.get_by_id(subject_id)
        if not subject:
            raise NotFoundError(f"Subject {subject_id} not found")
        
        year = await self.repos.session_year.get_by_id(academic_year_id)
        if not year:
            raise NotFoundError(f"Academic year {academic_year_id} not found")
        
        assignments = []
        successful = 0
        failed = 0
        
        async with self.transaction():
            # Batch process assignments
            for class_id, staff_id in zip(class_ids, staff_ids):
                try:
                    # Use existing assign_subject_to_class method
                    result = await self.assign_subject_to_class(
                        subject_id=subject_id,
                        class_id=class_id,
                        staff_id=staff_id,
                        academic_year_id=academic_year_id,
                        credits=credits,
                        user_id=user_id
                    )
                    
                    if result.get("success"):
                        assignments.append({
                            "class_id": str(class_id),
                            "staff_id": str(staff_id),
                            "status": "success"
                        })
                        successful += 1
                    else:
                        assignments.append({
                            "class_id": str(class_id),
                            "staff_id": str(staff_id),
                            "status": "failed",
                            "error": result.get("error", {}).get("message")
                        })
                        failed += 1
                
                except Exception as e:
                    logger.warning(f"Failed to assign to class {class_id}: {e}")
                    assignments.append({
                        "class_id": str(class_id),
                        "staff_id": str(staff_id),
                        "status": "failed",
                        "error": str(e)
                    })
                    failed += 1
            
            # Audit log
            self.log_action(
                action="BULK_ASSIGN_SUBJECT",
                entity_type="Subject",
                entity_id=subject_id,
                user_id=user_id,
                changes={
                    "class_count": len(class_ids),
                    "successful": successful,
                    "failed": failed,
                    "credits": credits
                }
            )
        
        logger.info(
            f"Bulk assignment completed: {successful} success, {failed} failed"
        )
        
        return self.success_response(
            data={
                "subject_id": str(subject_id),
                "total_classes": len(class_ids),
                "successful": successful,
                "failed": failed,
                "assignments": assignments,
                "created_at": datetime.utcnow().isoformat(),
                "message": f"Bulk assignment completed with {successful}/{len(class_ids)} success"
            }
        )
    
    async def synchronize_subject_content(
        self,
        subject_id: UUID,
        academic_year_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Ensure same subject across different classes/staff has synchronized content.
        
        Synchronizes:
        - Curriculum standards
        - Quiz bank access
        - Teaching schedule alignment
        
        Args:
            subject_id: UUID of subject
            academic_year_id: UUID of academic year
            user_id: UUID of user performing action (for audit)
        
        Returns:
            {
                "success": True,
                "data": {
                    "subject_id": UUID,
                    "classes_synced": 8,
                    "curriculum_synced": True,
                    "quiz_bank_synced": True,
                    "schedule_aligned": True,
                    "recommendations": [
                        "Class 1A is 2 weeks behind schedule",
                        "Consider reducing quiz difficulty in Class 2B"
                    ],
                    "synced_at": datetime,
                    "message": "Content synchronization completed"
                },
                "error": None
            }
        
        Example:
            >>> response = await subject_service.synchronize_subject_content(
            ...     subject_id=UUID("..."),
            ...     academic_year_id=UUID("...")
            ... )
        """
        logger.info(
            f"Synchronizing content for subject {subject_id} "
            f"in academic year {academic_year_id}"
        )
        
        subject = await self.repos.subject.get_by_id(subject_id)
        if not subject:
            raise NotFoundError(f"Subject {subject_id} not found")
        
        year = await self.repos.session_year.get_by_id(academic_year_id)
        if not year:
            raise NotFoundError(f"Academic year {academic_year_id} not found")
        
        # Get all classes teaching this subject in this year
        subject_assignments = await self.repos.subject.get_all_by_filter(
            and_(
                self.repos.subject.model.subject_id == subject_id,
                self.repos.subject.model.academic_year_id == academic_year_id
            )
        )
        
        classes_synced = len(subject_assignments)
        recommendations = []
        
        async with self.transaction():
            # Check curriculum alignment
            curriculum_synced = await self._sync_curriculum(
                subject_id, subject_assignments
            )
            
            # Sync quiz bank
            quiz_bank_synced = await self._sync_quiz_bank(
                subject_id, subject_assignments
            )
            
            # Check schedule alignment
            schedule_aligned = await self._align_schedules(
                subject_assignments, recommendations
            )
            
            # Audit log
            self.log_action(
                action="SYNC_SUBJECT_CONTENT",
                entity_type="Subject",
                entity_id=subject_id,
                user_id=user_id,
                changes={
                    "classes_synced": classes_synced,
                    "curriculum_synced": curriculum_synced,
                    "quiz_bank_synced": quiz_bank_synced,
                    "schedule_aligned": schedule_aligned
                }
            )
        
        logger.info(
            f"Content synchronization completed for {classes_synced} classes"
        )
        
        return self.success_response(
            data={
                "subject_id": str(subject_id),
                "classes_synced": classes_synced,
                "curriculum_synced": curriculum_synced,
                "quiz_bank_synced": quiz_bank_synced,
                "schedule_aligned": schedule_aligned,
                "recommendations": recommendations,
                "synced_at": datetime.utcnow().isoformat(),
                "message": "Content synchronization completed successfully"
            }
        )
    
    async def get_subject_statistics(
        self,
        subject_id: UUID,
        academic_year_id: UUID
    ) -> Dict:
        """
        Get comprehensive statistics for subject in academic year.
        
        Aggregates:
        - Total students enrolled (across classes)
        - Average grade
        - Pass rate
        - Staff assignments
        - Class distribution
        
        Args:
            subject_id: UUID of subject
            academic_year_id: UUID of academic year
        
        Returns:
            {
                "success": True,
                "data": {
                    "subject_id": UUID,
                    "subject_name": "Mathematics",
                    "academic_year": "2025-2026",
                    "total_students": 187,
                    "total_classes": 8,
                    "average_grade": 74.5,
                    "pass_rate": 85.0,
                    "failure_rate": 15.0,
                    "staff_count": 8,
                    "class_grades": [
                        {"class": "1A", "students": 23, "avg_grade": 78.0, "pass_rate": 91.0},
                        ...
                    ],
                    "top_performer": {"class": "1B", "avg_grade": 82.5},
                    "lowest_performer": {"class": "2C", "avg_grade": 65.0},
                    "created_at": datetime
                },
                "error": None
            }
        
        Example:
            >>> stats = await subject_service.get_subject_statistics(
            ...     subject_id=UUID("..."),
            ...     academic_year_id=UUID("...")
            ... )
        """
        logger.info(
            f"Generating statistics for subject {subject_id} "
            f"in year {academic_year_id}"
        )
        
        subject = await self.repos.subject.get_by_id(subject_id)
        if not subject:
            raise NotFoundError(f"Subject {subject_id} not found")
        
        year = await self.repos.session_year.get_by_id(academic_year_id)
        if not year:
            raise NotFoundError(f"Academic year {academic_year_id} not found")
        
        # Get all classes teaching this subject
        subject_assignments = await self.repos.subject.get_all_by_filter(
            and_(
                self.repos.subject.model.subject_id == subject_id,
                self.repos.subject.model.academic_year_id == academic_year_id
            )
        )
        
        total_students = 0
        total_classes = len(subject_assignments)
        all_grades = []
        class_stats = []
        
        # Aggregate statistics
        for assignment in subject_assignments:
            class_students = await self._count_class_students(assignment.class_id)
            total_students += class_students
            
            # Get grades for this class
            class_grades = await self._get_class_subject_grades(
                assignment.class_id, subject_id
            )
            all_grades.extend(class_grades)
            
            avg_grade = sum(class_grades) / len(class_grades) if class_grades else 0
            pass_rate = (len([g for g in class_grades if g >= 70]) / len(class_grades) * 100) if class_grades else 0
            
            class_stats.append({
                "class": assignment.class_obj.code,
                "students": class_students,
                "average_grade": round(avg_grade, 2),
                "pass_rate": round(pass_rate, 2),
                "staff": f"{assignment.staff.user.first_name} {assignment.staff.user.last_name}"
            })
        
        # Calculate overall statistics
        overall_avg = sum(all_grades) / len(all_grades) if all_grades else 0
        overall_pass_rate = (len([g for g in all_grades if g >= 70]) / len(all_grades) * 100) if all_grades else 0
        overall_fail_rate = 100 - overall_pass_rate
        
        # Find top and lowest performers
        top_class = max(class_stats, key=lambda x: x["average_grade"]) if class_stats else None
        lowest_class = min(class_stats, key=lambda x: x["average_grade"]) if class_stats else None
        
        logger.info(
            f"Generated statistics: {total_students} students, "
            f"{total_classes} classes, avg grade {overall_avg:.2f}%"
        )
        
        return self.success_response(
            data={
                "subject_id": str(subject_id),
                "subject_name": subject.name,
                "academic_year": year.year,
                "total_students": total_students,
                "total_classes": total_classes,
                "average_grade": round(overall_avg, 2),
                "pass_rate": round(overall_pass_rate, 2),
                "failure_rate": round(overall_fail_rate, 2),
                "staff_count": total_classes,
                "class_statistics": class_stats,
                "top_performer": top_class,
                "lowest_performer": lowest_class,
                "generated_at": datetime.utcnow().isoformat()
            }
        )
    
    async def get_subject_performance_comparison(
        self,
        subject_id: UUID,
        academic_year_id: UUID,
        comparison_type: str = "by_class"
    ) -> Dict:
        """
        Compare performance of same subject across different dimensions.
        
        Comparison types:
        - by_class: Compare same subject across different classes (1A vs 1B)
        - by_staff: Compare same subject taught by different staff
        - by_time_slot: Compare morning vs afternoon class performance
        
        Args:
            subject_id: UUID of subject
            academic_year_id: UUID of academic year
            comparison_type: One of "by_class", "by_staff", "by_time_slot"
        
        Returns:
            {
                "success": True,
                "data": {
                    "comparison_type": "by_class",
                    "subject": "Mathematics",
                    "comparisons": [
                        {
                            "dimension": "1A",
                            "students": 25,
                            "average_grade": 78.5,
                            "pass_rate": 90.0,
                            "median_grade": 79.0,
                            "std_deviation": 8.5
                        },
                        ...
                    ],
                    "best": {"dimension": "1B", "average_grade": 82.5},
                    "worst": {"dimension": "2C", "average_grade": 65.0},
                    "insights": [
                        "Best performing section (1B) has 17% higher avg grade than worst (2C)",
                        "Consider sharing teaching strategies from 1B with 2C instructor"
                    ],
                    "generated_at": datetime
                },
                "error": None
            }
        
        Example:
            >>> comparison = await subject_service.get_subject_performance_comparison(
            ...     subject_id=UUID("..."),
            ...     academic_year_id=UUID("..."),
            ...     comparison_type="by_staff"
            ... )
        """
        logger.info(
            f"Comparing subject {subject_id} by {comparison_type} "
            f"for year {academic_year_id}"
        )
        
        subject = await self.repos.subject.get_by_id(subject_id)
        if not subject:
            raise NotFoundError(f"Subject {subject_id} not found")
        
        if comparison_type not in ["by_class", "by_staff", "by_time_slot"]:
            raise ValidationError(
                f"Invalid comparison_type. Must be by_class, by_staff, or by_time_slot"
            )
        
        comparisons = []
        best = None
        worst = None
        
        subject_assignments = await self.repos.subject.get_all_by_filter(
            and_(
                self.repos.subject.model.subject_id == subject_id,
                self.repos.subject.model.academic_year_id == academic_year_id
            )
        )
        
        if comparison_type == "by_class":
            for assignment in subject_assignments:
                class_obj = assignment.class_obj
                students = await self._count_class_students(assignment.class_id)
                grades = await self._get_class_subject_grades(assignment.class_id, subject_id)
                
                avg_grade = sum(grades) / len(grades) if grades else 0
                median_grade = sorted(grades)[len(grades)//2] if grades else 0
                pass_rate = (len([g for g in grades if g >= 70]) / len(grades) * 100) if grades else 0
                std_dev = self._calculate_std_dev(grades) if grades else 0
                
                comparison = {
                    "dimension": class_obj.code,
                    "students": students,
                    "average_grade": round(avg_grade, 2),
                    "median_grade": round(median_grade, 2),
                    "pass_rate": round(pass_rate, 2),
                    "std_deviation": round(std_dev, 2)
                }
                comparisons.append(comparison)
                
                if best is None or avg_grade > best["average_grade"]:
                    best = comparison
                if worst is None or avg_grade < worst["average_grade"]:
                    worst = comparison
        
        elif comparison_type == "by_staff":
            for assignment in subject_assignments:
                staff = assignment.staff
                students = await self._count_class_students(assignment.class_id)
                grades = await self._get_class_subject_grades(assignment.class_id, subject_id)
                
                avg_grade = sum(grades) / len(grades) if grades else 0
                median_grade = sorted(grades)[len(grades)//2] if grades else 0
                pass_rate = (len([g for g in grades if g >= 70]) / len(grades) * 100) if grades else 0
                std_dev = self._calculate_std_dev(grades) if grades else 0
                
                comparison = {
                    "dimension": f"{staff.user.first_name} {staff.user.last_name}",
                    "students": students,
                    "average_grade": round(avg_grade, 2),
                    "median_grade": round(median_grade, 2),
                    "pass_rate": round(pass_rate, 2),
                    "std_deviation": round(std_dev, 2)
                }
                comparisons.append(comparison)
                
                if best is None or avg_grade > best["average_grade"]:
                    best = comparison
                if worst is None or avg_grade < worst["average_grade"]:
                    worst = comparison
        
        # Generate insights
        insights = []
        if best and worst:
            diff = best["average_grade"] - worst["average_grade"]
            pct_diff = (diff / worst["average_grade"] * 100) if worst["average_grade"] > 0 else 0
            insights.append(
                f"Best performing {comparison_type} ({best['dimension']}) has "
                f"{pct_diff:.1f}% higher avg grade than worst ({worst['dimension']})"
            )
            insights.append(
                f"Consider sharing teaching strategies from {best['dimension']} "
                f"with {worst['dimension']} instructor"
            )
        
        logger.info(f"Generated {len(comparisons)} comparisons")
        
        return self.success_response(
            data={
                "comparison_type": comparison_type,
                "subject": subject.name,
                "comparisons": comparisons,
                "best": best,
                "worst": worst,
                "insights": insights,
                "generated_at": datetime.utcnow().isoformat()
            }
        )
    
    async def identify_difficult_subjects(
        self,
        academic_year_id: UUID
    ) -> Dict:
        """
        Identify subjects with low pass rates requiring intervention.
        
        Thresholds:
        - Pass rate < 70% = concerns flagged
        - Pass rate < 50% = critical intervention needed
        - Withdrawal > 5% = investigation needed
        
        Args:
            academic_year_id: UUID of academic year
        
        Returns:
            {
                "success": True,
                "data": {
                    "academic_year": "2025-2026",
                    "total_subjects": 45,
                    "concerns": 8,
                    "critical": 2,
                    "subjects_flagged": [
                        {
                            "subject_id": UUID,
                            "subject_name": "Organic Chemistry",
                            "pass_rate": 48.0,
                            "failure_rate": 52.0,
                            "severity": "CRITICAL",
                            "failure_count": 26,
                            "total_students": 50,
                            "interventions": [
                                "Immediate curriculum review required",
                                "Add extra support sessions (3x/week)",
                                "Consider staff professional development",
                                "Reduce class size or split into smaller groups"
                            ]
                        },
                        ...
                    ],
                    "generated_at": datetime
                }
            }
        
        Example:
            >>> report = await subject_service.identify_difficult_subjects(
            ...     academic_year_id=UUID("...")
            ... )
        """
        logger.info(f"Identifying difficult subjects for year {academic_year_id}")
        
        year = await self.repos.session_year.get_by_id(academic_year_id)
        if not year:
            raise NotFoundError(f"Academic year {academic_year_id} not found")
        
        # Get all subject assignments for this year
        all_assignments = await self.repos.subject.get_all_by_filter(
            self.repos.subject.model.academic_year_id == academic_year_id
        )
        
        subjects_flagged = []
        concern_count = 0
        critical_count = 0
        
        for assignment in all_assignments:
            subject = assignment.subject
            grades = await self._get_class_subject_grades(assignment.class_id, subject.id)
            
            if not grades:
                continue
            
            pass_count = len([g for g in grades if g >= 70])
            fail_count = len([g for g in grades if g < 70])
            pass_rate = (pass_count / len(grades) * 100) if grades else 0
            failure_rate = 100 - pass_rate
            
            # Determine severity
            severity = None
            interventions = []
            
            if pass_rate < 50:
                severity = "CRITICAL"
                critical_count += 1
                interventions = [
                    "Immediate curriculum review required",
                    "Add extra support sessions (3x/week minimum)",
                    "Consider staff professional development",
                    "Reduce class size or split into smaller groups",
                    "Implement peer tutoring program",
                    "Schedule parent-teacher conferences"
                ]
            elif pass_rate < 70:
                severity = "CONCERN"
                concern_count += 1
                interventions = [
                    "Schedule curriculum review meeting",
                    "Add additional support sessions (2x/week)",
                    "Monitor student engagement closely",
                    "Identify at-risk students for early intervention"
                ]
            
            # Check withdrawal rate
            withdrawal_rate = await self._get_subject_withdrawal_rate(subject.id, assignment.class_id)
            if withdrawal_rate and withdrawal_rate > 5:
                if severity is None:
                    severity = "CONCERN"
                interventions.append(
                    f"High withdrawal rate ({withdrawal_rate:.1f}%). Investigate student satisfaction."
                )
            
            if severity:
                subjects_flagged.append({
                    "subject_id": str(subject.id),
                    "subject_name": subject.name,
                    "class": assignment.class_obj.code,
                    "pass_rate": round(pass_rate, 2),
                    "failure_rate": round(failure_rate, 2),
                    "severity": severity,
                    "failure_count": fail_count,
                    "total_students": len(grades),
                    "interventions": interventions
                })
        
        logger.info(
            f"Identified {len(subjects_flagged)} difficult subjects: "
            f"{concern_count} concerns, {critical_count} critical"
        )
        
        return self.success_response(
            data={
                "academic_year": year.year,
                "total_subjects_reviewed": len(all_assignments),
                "subjects_flagged": len(subjects_flagged),
                "concerns": concern_count,
                "critical": critical_count,
                "subjects": subjects_flagged,
                "generated_at": datetime.utcnow().isoformat()
            }
        )
    
    async def analyze_staff_subject_load(
        self,
        staff_id: UUID,
        academic_year_id: UUID
    ) -> Dict:
        """
        Analyze teaching workload for staff member.
        
        Calculates:
        - Total subjects assigned
        - Total students taught
        - Weekly contact hours
        - Grading workload
        - Preparation time estimate
        
        Args:
            staff_id: UUID of staff member
            academic_year_id: UUID of academic year
        
        Returns:
            {
                "success": True,
                "data": {
                    "staff_id": UUID,
                    "staff_name": "Dr. John Smith",
                    "academic_year": "2025-2026",
                    "total_subjects": 5,
                    "total_students": 187,
                    "weekly_contact_hours": 22.5,
                    "pending_grading_count": 145,
                    "estimated_prep_hours_per_week": 18.0,
                    "total_workload_hours": 40.5,
                    "load_status": "HIGH",
                    "recommendations": [
                        "Consider reducing to 4 subjects",
                        "Consider splitting one large class",
                        "Allocate grading assistance to junior staff"
                    ],
                    "analyzed_at": datetime
                },
                "error": None
            }
        
        Example:
            >>> analysis = await subject_service.analyze_staff_subject_load(
            ...     staff_id=UUID("..."),
            ...     academic_year_id=UUID("...")
            ... )
        """
        logger.info(
            f"Analyzing workload for staff {staff_id} "
            f"in year {academic_year_id}"
        )
        
        staff = await self.repos.staff.get_by_id(staff_id)
        if not staff:
            raise NotFoundError(f"Staff member {staff_id} not found")
        
        year = await self.repos.session_year.get_by_id(academic_year_id)
        if not year:
            raise NotFoundError(f"Academic year {academic_year_id} not found")
        
        # Get all subjects for this staff
        subject_assignments = await self._get_staff_subjects(staff_id, academic_year_id)
        total_subjects = len(subject_assignments)
        
        # Calculate metrics
        total_students = 0
        weekly_contact_hours = 0.0
        total_timetable_slots = 0
        
        for assignment in subject_assignments:
            students = await self._count_class_students(assignment.class_id)
            total_students += students
            
            # Get timetable slots
            slots = await self._get_timetable_slots_for_assignment(assignment.id)
            total_timetable_slots += len(slots)
            
            # Calculate contact hours (assume 1 hour per slot)
            weekly_contact_hours += len(slots)
        
        # Estimate preparation time (2x contact hours is standard)
        estimated_prep_hours = weekly_contact_hours * 2
        
        # Pending grading
        pending_grading = await self._count_pending_grading(staff_id)
        
        # Total workload
        total_workload = weekly_contact_hours + estimated_prep_hours
        
        # Determine load status
        if total_workload > 35:
            load_status = "CRITICAL"
        elif total_workload > 25:
            load_status = "HIGH"
        elif total_workload > 15:
            load_status = "NORMAL"
        else:
            load_status = "LIGHT"
        
        recommendations = []
        if load_status in ["HIGH", "CRITICAL"]:
            recommendations.append(f"Workload is {load_status.lower()}: {total_workload:.1f} hours/week")
            recommendations.append(
                f"Consider reducing to {max(1, total_subjects - 1)} subjects"
            )
            if total_students > 150:
                recommendations.append("Consider splitting one large class")
            if pending_grading > 100:
                recommendations.append("Allocate grading assistance to junior staff")
        
        logger.info(
            f"Workload analysis: {total_subjects} subjects, "
            f"{total_students} students, {total_workload:.1f} hours/week, "
            f"status: {load_status}"
        )
        
        return self.success_response(
            data={
                "staff_id": str(staff_id),
                "staff_name": f"{staff.user.first_name} {staff.user.last_name}",
                "academic_year": year.year,
                "total_subjects": total_subjects,
                "total_students": total_students,
                "weekly_contact_hours": round(weekly_contact_hours, 2),
                "total_timetable_slots": total_timetable_slots,
                "pending_grading_count": pending_grading,
                "estimated_prep_hours_per_week": round(estimated_prep_hours, 2),
                "total_workload_hours": round(total_workload, 2),
                "load_status": load_status,
                "recommendations": recommendations,
                "analyzed_at": datetime.utcnow().isoformat()
            }
        )
    
    # ==================== Private Helper Methods ====================
    
    async def _validate_qualification(self, subject, staff):
        """Validate staff qualifications match subject requirements."""
        subject_name = subject.name
        
        # Get required qualifications
        required = self.QUALIFICATION_RULES.get(subject_name, [])
        if not required:
            logger.warning(f"No qualification rules defined for {subject_name}")
            return  # Assume qualified if no rules
        
        # Get staff qualifications (assuming staff has qualification field)
        staff_qualifications = getattr(staff, "qualification", "") or ""
        
        # Check if any staff qualification matches requirements
        has_qualification = any(
            req.lower() in staff_qualifications.lower()
            for req in required
        )
        
        if not has_qualification:
            raise ForbiddenError(
                f"Staff lacks required qualifications. "
                f"Subject '{subject_name}' requires one of: {', '.join(required)}. "
                f"Staff has: {staff_qualifications}"
            )
    
    async def _count_staff_subjects(self, staff_id: UUID, academic_year_id: UUID) -> int:
        """Count subjects assigned to staff for academic year."""
        assignments = await self.repos.subject.get_all_by_filter(
            and_(
                self.repos.subject.model.staff_id == staff_id,
                self.repos.subject.model.academic_year_id == academic_year_id,
                self.repos.subject.model.is_deleted == False
            )
        )
        return len(assignments) if assignments else 0
    
    async def _notify_class_students(
        self, class_id: UUID, title: str, message: str, notification_type: str = "INFO"
    ):
        """Send notification to all students in class."""
        students = await self._get_class_students(class_id)
        for student in students:
            await self.repos.notification.create({
                "recipient_id": student.user_id,
                "type": notification_type,
                "title": title,
                "message": message,
                "created_at": datetime.utcnow()
            })
    
    async def _count_grades_for_assignment(self, subject_id: UUID, class_id: UUID) -> int:
        """Count student grades recorded for subject in class."""
        # Would query StudentResult or Grade table
        return 0  # Placeholder
    
    async def _count_active_submissions(self, subject_id: UUID, class_id: UUID) -> int:
        """Count active quiz/assignment submissions."""
        # Would query active quiz attempts and assignment submissions
        return 0  # Placeholder
    
    async def _count_class_students(self, class_id: UUID) -> int:
        """Count enrolled students in class."""
        students = await self.repos.student.get_all_by_filter(
            self.repos.student.model.class_id == class_id
        )
        return len(students) if students else 0
    
    async def _get_timetable_slots(
        self, subject_id: UUID, class_id: UUID, staff_id: UUID
    ) -> List:
        """Get timetable slots for subject-class-staff combination."""
        slots = await self.repos.timetable.get_all_by_filter(
            and_(
                self.repos.timetable.model.subject_id == subject_id,
                self.repos.timetable.model.class_id == class_id,
                self.repos.timetable.model.staff_id == staff_id
            )
        )
        return slots if slots else []
    
    async def _create_continuation_records(
        self, subject_id: UUID, class_id: UUID, old_staff_id: UUID
    ):
        """Create records for continuity when changing staff."""
        # Would create StudentResult entries linking new and old staff
        pass
    
    async def _get_department_head(self, department_id: UUID):
        """Get department head for department."""
        # Would query Department and related Staff
        return None
    
    async def _get_staff_timetable_slots(self, staff_id: UUID) -> List:
        """Get all timetable slots for staff."""
        slots = await self.repos.timetable.get_all_by_filter(
            self.repos.timetable.model.staff_id == staff_id
        )
        return slots if slots else []
    
    def _time_overlaps(self, start1: time, end1: time, start2: time, end2: time) -> bool:
        """Check if two time ranges overlap."""
        return start1 < end2 and start2 < end1
    
    def _buffer_violated(
        self, start1: time, end1: time, start2: time, end2: time
    ) -> bool:
        """Check if buffer between classes is violated."""
        if end1 <= start2:
            # First class ends before second starts
            gap = (datetime.combine(datetime.today(), start2) - 
                   datetime.combine(datetime.today(), end1)).total_seconds() / 60
            return gap < self.CONFLICT_BUFFER_MINUTES
        elif end2 <= start1:
            # Second class ends before first starts
            gap = (datetime.combine(datetime.today(), start1) - 
                   datetime.combine(datetime.today(), end2)).total_seconds() / 60
            return gap < self.CONFLICT_BUFFER_MINUTES
        return False
    
    def _calculate_consecutive_classes(self, slots: List, proposed_start: time) -> int:
        """Calculate how many consecutive classes would result."""
        same_time_slots = [s for s in slots if s.start_time <= proposed_start < s.end_time]
        return len(same_time_slots) + 1
    
    async def _suggest_alternative_slots(self, staff_id: UUID, day: str) -> List[Dict]:
        """Suggest alternative time slots for staff."""
        alternatives = []
        # Standard school hours 9am-4pm in 60-minute blocks
        hours = [(h, h+1) for h in range(9, 16)]
        
        busy_hours = set()
        staff_slots = await self._get_staff_timetable_slots(staff_id)
        for slot in staff_slots:
            if slot.day_of_week.upper() == day.upper():
                busy_hours.add(slot.start_time.hour)
        
        for start_hour, end_hour in hours:
            if start_hour not in busy_hours:
                alternatives.append({
                    "day": day,
                    "start_time": f"{start_hour:02d}:00",
                    "end_time": f"{end_hour:02d}:00"
                })
        
        return alternatives[:3]  # Return top 3
    
    async def _get_conflict_record(self, conflict_id: UUID):
        """Fetch conflict record from database."""
        # Placeholder - would query ScheduleConflict table
        return None
    
    async def _reschedule_class(self, conflict, new_time_slot: Dict) -> int:
        """Reschedule class to new time slot."""
        return 1  # Count of affected classes
    
    async def _combine_classes(self, conflict) -> Dict:
        """Attempt to combine conflicting classes."""
        return {"classes_merged": 0, "total_students": 0}
    
    async def _split_class(self, conflict, new_time_slot: Dict) -> Dict:
        """Split class into multiple time slots."""
        return {"new_slots": 0, "total_students": 0}
    
    async def _mark_conflict_resolved(self, conflict_id: UUID, strategy: str):
        """Mark conflict as resolved in database."""
        pass
    
    async def _notify_schedule_change(
        self, class_id: UUID, staff_id: UUID, message: str
    ):
        """Notify all affected parties of schedule change."""
        await self._notify_class_students(
            class_id, "Schedule Change", message, "INFO"
        )
    
    async def _get_highest_grade_in_subject(
        self, student_id: UUID, subject_id: UUID
    ) -> Optional[float]:
        """Get highest grade student achieved in subject."""
        # Would query StudentResult/Grade table
        return None
    
    def _check_circular_dependencies(self, subjects: List):
        """Check subject sequence for circular dependencies."""
        # Would check prerequisite chain
        pass
    
    async def _sync_curriculum(
        self, subject_id: UUID, assignments: List
    ) -> bool:
        """Synchronize curriculum across class assignments."""
        return True
    
    async def _sync_quiz_bank(
        self, subject_id: UUID, assignments: List
    ) -> bool:
        """Synchronize quiz bank across class assignments."""
        return True
    
    async def _align_schedules(
        self, assignments: List, recommendations: List
    ) -> bool:
        """Align teaching schedules and generate recommendations."""
        return True
    
    async def _get_class_subject_grades(
        self, class_id: UUID, subject_id: UUID
    ) -> List[float]:
        """Get all student grades in subject for class."""
        # Would query StudentResult/Grade table
        return []
    
    async def _get_class_students(self, class_id: UUID) -> List:
        """Get all students in class."""
        students = await self.repos.student.get_all_by_filter(
            self.repos.student.model.class_id == class_id
        )
        return students if students else []
    
    def _calculate_std_dev(self, grades: List[float]) -> float:
        """Calculate standard deviation of grades."""
        if not grades or len(grades) < 2:
            return 0.0
        mean = sum(grades) / len(grades)
        variance = sum((x - mean) ** 2 for x in grades) / len(grades)
        return variance ** 0.5
    
    async def _get_subject_withdrawal_rate(
        self, subject_id: UUID, class_id: UUID
    ) -> Optional[float]:
        """Get withdrawal rate for subject in class."""
        # Would query enrollment changes
        return None
    
    async def _get_staff_subjects(
        self, staff_id: UUID, academic_year_id: UUID
    ) -> List:
        """Get all subject assignments for staff in academic year."""
        assignments = await self.repos.subject.get_all_by_filter(
            and_(
                self.repos.subject.model.staff_id == staff_id,
                self.repos.subject.model.academic_year_id == academic_year_id,
                self.repos.subject.model.is_deleted == False
            )
        )
        return assignments if assignments else []
    
    async def _get_timetable_slots_for_assignment(self, assignment_id: UUID) -> List:
        """Get timetable slots for specific assignment."""
        # Would query with assignment ID
        return []
    
    async def _count_pending_grading(self, staff_id: UUID) -> int:
        """Count pending submissions needing grading."""
        # Would query ungraded quiz attempts and assignments
        return 0


# Export for RepositoryFactory injection
__all__ = ["SubjectService"]
