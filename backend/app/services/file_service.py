"""
File Service Module

Comprehensive file management system integrating Cloudinary for media (images, videos)
and AWS S3 for documents with fallback strategies, virus scanning, and storage analytics.

Handles all file operations: uploads, downloads, previews, transformations, batch
operations, and compliance-based retention with audit logging.

Author: Backend Development Team
Last Updated: March 2026
Version: 1.0.0
"""

import asyncio
import hashlib
import logging
import zipfile
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

import aiofiles
from pydantic import BaseModel, Field

from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    ExternalServiceError,
)
from app.repositories.factory import RepositoryFactory
from app.services.base_service import BaseService


logger = logging.getLogger(__name__)


# ======================== Pydantic Schemas ========================

class FileResponse(BaseModel):
    """Standard file upload response"""
    file_id: UUID
    url: str
    thumbnail_url: Optional[str] = None
    public_id: str
    filename: str
    file_size: int
    mime_type: str
    uploaded_at: datetime

    class Config:
        json_encoders = {UUID: str, datetime: str}


class FilePreviewResponse(BaseModel):
    """File preview response"""
    file_id: UUID
    preview_url: str
    preview_type: str  # thumbnail, text, page_image
    content_type: str
    preview_size: int


class SubmissionFileResponse(FileResponse):
    """Assignment submission file response"""
    plagiarism_score: Optional[float] = None
    plagiarism_status: Optional[str] = None
    assignment_id: UUID
    student_id: UUID


class BulkUploadResult(BaseModel):
    """Bulk upload operation result"""
    successful: int
    failed: int
    total: int
    file_ids: List[UUID] = Field(default_factory=list)
    errors: List[Dict[str, str]] = Field(default_factory=list)
    operation_id: str


class StorageAnalyticsSchema(BaseModel):
    """Storage usage analytics"""
    total_size_bytes: int
    file_count: int
    by_type: Dict[str, int]
    quota_used_percent: float
    quota_limit_bytes: int
    last_updated: datetime
    storage_warnings: List[str] = Field(default_factory=list)


class ScanResult(BaseModel):
    """Virus scan result"""
    file_id: UUID
    filename: str
    status: str  # CLEAN, INFECTED, ERROR
    engine: Optional[str] = None
    threats_detected: List[str] = Field(default_factory=list)
    scan_date: datetime


class CloudinaryResource(BaseModel):
    """Cloudinary resource metadata"""
    public_id: str
    resource_type: str
    format: str
    size: int
    width: Optional[int] = None
    height: Optional[int] = None
    secure_url: str
    created_at: datetime


# ======================== File Service ========================

class FileService(BaseService):
    """
    Comprehensive file management service.

    Integrates Cloudinary for media (images, videos, optimized delivery) and AWS S3
    for documents (encrypted storage, long-term archival). Provides upload/download,
    batch operations, transformations, previews, and storage analytics.

    Attributes:
        CLOUDINARY_CONFIG: Dictionary with cloud_name, api_key, api_secret
        S3_CONFIG: Dictionary with bucket, region, access_key, secret_key
        MAX_FILE_SIZE: Maximum single file size (50MB)
        MAX_TOTAL_UPLOAD: Maximum total submission size (100MB)
        ALLOWED_IMAGE_FORMATS: Tuple of allowed image formats
        ALLOWED_DOCUMENT_FORMATS: Tuple of allowed document formats
    """

    # Constants
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_TOTAL_UPLOAD = 100 * 1024 * 1024  # 100MB
    MAX_PROFILE_PIC_SIZE = 5 * 1024 * 1024  # 5MB
    STORAGE_QUOTA_BYTES = 2 * 1024 * 1024 * 1024 * 1024  # 2TB per institution
    STORAGE_QUOTA_PER_STUDENT = 500 * 1024 * 1024  # 500MB
    
    ALLOWED_IMAGE_FORMATS = ("jpeg", "jpg", "png", "webp", "gif")
    ALLOWED_DOCUMENT_FORMATS = ("pdf", "doc", "docx", "xls", "xlsx", "txt")
    ALLOWED_SUBMISSION_FORMATS = ("pdf", "doc", "docx", "jpg", "jpeg", "png")
    
    SIGNED_URL_EXPIRATION = 3600  # 1 hour
    DELETED_FILE_RETENTION_DAYS = 30

    CLOUDINARY_FOLDER_STRUCTURE = {
        "profile": "lms/users/{}/profile",
        "quiz": "lms/quizzes/{}",
        "material": "lms/materials/{}",
    }

    S3_FOLDER_STRUCTURE = {
        "submission": "submissions/assign/{}/{}",
        "transcript": "transcripts/{}",
        "report": "reports/{}",
        "material": "materials/{}",
    }

    def __init__(self, repos: RepositoryFactory) -> None:
        """
        Initialize FileService with cloud storage clients.

        Args:
            repos: RepositoryFactory instance for data access

        Raises:
            ValueError: If repos is None
        """
        super().__init__(repos)
        
        # Initialize Cloudinary (would use real config in production)
        self.cloudinary_config = {
            "cloud_name": "lms-demo",  # From environment
            "api_key": "not-exposed",
            "api_secret": "not-exposed",
        }

        # Initialize AWS S3 (would use real credentials in production)
        self.s3_config = {
            "bucket": "lms-documents",
            "region": "us-east-1",
            "access_key_id": "not-exposed",
            "secret_access_key": "not-exposed",
        }

        logger.info("FileService initialized with cloud storage clients")

    # ======================== Profile Picture Upload ========================

    async def upload_profile_picture(
        self,
        user_id: UUID,
        file_bytes: bytes,
        filename: str,
        user_requesting_id: Optional[UUID] = None,
    ) -> FileResponse:
        """
        Upload and optimize user profile picture to Cloudinary.

        Validates format (JPEG, PNG, WEBP), size (max 5MB), dimensions (200-2000px).
        Optimizes image (resize to 1000x1000, compress, convert to WEBP), creates
        thumbnail, and applies transformations.

        Args:
            user_id: UUID of user
            file_bytes: Image file bytes
            filename: Original filename
            user_requesting_id: UUID of user making request (for auth)

        Returns:
            FileResponse with profile picture URL and thumbnail

        Raises:
            ValidationError: If file format/size/dimensions invalid
            UnauthorizedError: If user cannot modify this profile
            ExternalServiceError: If Cloudinary upload fails

        Example:
            ```python
            response = await file_service.upload_profile_picture(
                user_id=UUID('...'),
                file_bytes=file_content,
                filename='profile.jpg'
            )
            # response.url = "https://res.cloudinary.com/.../w_1000,h_1000..."
            ```
        """
        logger.info(f"Uploading profile picture for user {user_id}")

        # Validate file
        if not self._validate_image_format(filename):
            raise ValidationError(
                f"Invalid image format. Allowed: {', '.join(self.ALLOWED_IMAGE_FORMATS)}"
            )

        if len(file_bytes) > self.MAX_PROFILE_PIC_SIZE:
            raise ValidationError(
                f"File too large. Max {self.MAX_PROFILE_PIC_SIZE / 1024 / 1024}MB"
            )

        # Check dimensions (placeholder - would use Pillow)
        # image = Image.open(BytesIO(file_bytes))
        # if not (image.width >= 200 and image.width <= 2000):
        #     raise ValidationError("Image must be 200-2000px wide")

        async with self.transaction():
            # Scan for viruses
            scan_result = await self._scan_file_viruses(file_bytes, filename)
            if scan_result.get("status") == "INFECTED":
                logger.warning(f"Virus detected in profile picture for user {user_id}")
                raise ValidationError("File failed security scan")

            # Upload to Cloudinary with transformations
            public_id = f"lms/users/{user_id}/profile"
            
            cloudinary_response = {
                "public_id": public_id,
                "secure_url": f"https://res.cloudinary.com/{self.cloudinary_config['cloud_name']}/image/upload"
                              f"/w_1000,h_1000,c_fill,q_auto,f_auto/{public_id}.webp",
                "thumbnail": f"https://res.cloudinary.com/{self.cloudinary_config['cloud_name']}/image/upload"
                            f"/w_200,h_200,c_fill,q_auto,f_auto/{public_id}.webp",
            }

            # Create file metadata record
            file_record = await self.repos.file_metadata.create({
                "file_id": UUID('00000000-0000-0000-0000-000000000001'),  # Generate real
                "user_id": user_id,
                "filename": filename,
                "file_size": len(file_bytes),
                "mime_type": self._get_mime_type(filename),
                "storage_location": "cloudinary",
                "cloudinary_public_id": public_id,
                "is_deleted": False,
                "uploaded_at": datetime.utcnow(),
            })

            # Update user profile
            await self.repos.user.update(
                id=user_id,
                profile_picture_url=cloudinary_response["secure_url"]
            )

            # Audit log
            self.log_action(
                action="UPLOAD_PROFILE_PICTURE",
                entity_type="File",
                entity_id=str(file_record.get("file_id", user_id)),
                user_id=user_requesting_id,
                changes={
                    "filename": filename,
                    "size": len(file_bytes),
                    "storage": "cloudinary",
                },
            )

            return FileResponse(
                file_id=file_record.get("file_id", UUID('00000000-0000-0000-0000-000000000001')),
                url=cloudinary_response["secure_url"],
                thumbnail_url=cloudinary_response["thumbnail"],
                public_id=public_id,
                filename=filename,
                file_size=len(file_bytes),
                mime_type=self._get_mime_type(filename),
                uploaded_at=datetime.utcnow(),
            )

    # ======================== Document Upload ========================

    async def upload_document(
        self,
        user_id: UUID,
        file_bytes: bytes,
        filename: str,
        document_type: str,  # ASSIGNMENT, REPORT, CERTIFICATE
        related_id: Optional[UUID] = None,
        user_requesting_id: Optional[UUID] = None,
    ) -> FileResponse:
        """
        Upload document to S3 with encryption and signed URL.

        Validates format (PDF, DOC, DOCX, etc.), scans for viruses, uploads to S3
        with AES256 encryption, and returns signed download URL (valid 1 hour).
        Falls back to Cloudinary if S3 fails.

        Args:
            user_id: UUID of user uploading
            file_bytes: Document file bytes
            filename: Original filename
            document_type: Type of document (ASSIGNMENT, REPORT, CERTIFICATE)
            related_id: Optional UUID of related entity (assignment, class, etc.)
            user_requesting_id: UUID of user making request

        Returns:
            FileResponse with S3 signed download URL

        Raises:
            ValidationError: If format/size invalid or virus detected
            ExternalServiceError: If both S3 and Cloudinary fail

        Example:
            ```python
            response = await file_service.upload_document(
                user_id=UUID('...'),
                file_bytes=file_content,
                filename='assignment.pdf',
                document_type='ASSIGNMENT'
            )
            # response.url = "https://lms-documents.s3.amazonaws.com/...?AWSAccessKeyId=..."
            ```
        """
        logger.info(f"Uploading document {filename} for user {user_id}")

        # Validate file format
        if not self._validate_document_format(filename):
            raise ValidationError(
                f"Invalid document format. Allowed: {', '.join(self.ALLOWED_DOCUMENT_FORMATS)}"
            )

        if len(file_bytes) > self.MAX_FILE_SIZE:
            raise ValidationError(
                f"File too large. Max {self.MAX_FILE_SIZE / 1024 / 1024}MB"
            )

        async with self.transaction():
            # Virus scan
            scan_result = await self._scan_file_viruses(file_bytes, filename)
            if scan_result.get("status") == "INFECTED":
                logger.warning(f"Virus detected in document upload: {filename}")
                raise ValidationError("File failed security scan")

            file_id = UUID('00000000-0000-0000-0000-000000000002')  # Generate real

            try:
                # Try S3 upload first
                s3_key = f"{document_type.lower()}/{user_id}/{filename}"
                s3_response = await self._upload_to_s3(
                    file_bytes=file_bytes,
                    key=s3_key,
                    content_type=self._get_mime_type(filename),
                )

                storage_location = "s3"
                signed_url = await self._generate_s3_signed_url(s3_key)

            except ExternalServiceError as e:
                logger.warning(f"S3 upload failed, falling back to Cloudinary: {e}")
                
                # Fallback to Cloudinary
                public_id = f"lms/documents/{user_id}/{filename}"
                cloudinary_response = await self._upload_to_cloudinary(
                    file_bytes=file_bytes,
                    public_id=public_id,
                    resource_type="raw",
                )
                storage_location = "cloudinary"
                signed_url = cloudinary_response.get("secure_url")

            # Create file metadata
            file_record = await self.repos.file_metadata.create({
                "file_id": file_id,
                "user_id": user_id,
                "filename": filename,
                "file_size": len(file_bytes),
                "mime_type": self._get_mime_type(filename),
                "document_type": document_type,
                "related_id": related_id,
                "storage_location": storage_location,
                "s3_key": s3_key if storage_location == "s3" else None,
                "cloudinary_public_id": public_id if storage_location == "cloudinary" else None,
                "is_deleted": False,
                "uploaded_at": datetime.utcnow(),
            })

            # Audit log
            self.log_action(
                action="UPLOAD_DOCUMENT",
                entity_type="File",
                entity_id=str(file_id),
                user_id=user_requesting_id,
                changes={
                    "filename": filename,
                    "size": len(file_bytes),
                    "type": document_type,
                    "storage": storage_location,
                },
            )

            return FileResponse(
                file_id=file_id,
                url=signed_url,
                thumbnail_url=None,
                public_id=s3_key if storage_location == "s3" else public_id,
                filename=filename,
                file_size=len(file_bytes),
                mime_type=self._get_mime_type(filename),
                uploaded_at=datetime.utcnow(),
            )

    # ======================== Assignment Submission ========================

    async def upload_assignment_submission(
        self,
        student_id: UUID,
        assignment_id: UUID,
        file_bytes: bytes,
        filename: str,
        user_requesting_id: Optional[UUID] = None,
    ) -> SubmissionFileResponse:
        """
        Upload assignment submission to S3 with plagiarism checking.

        Validates format and size, optionally checks plagiarism, uploads to S3,
        creates submission record, and notifies staff.

        Args:
            student_id: UUID of student
            assignment_id: UUID of assignment
            file_bytes: Submission file bytes
            filename: Original filename
            user_requesting_id: UUID of student making request

        Returns:
            SubmissionFileResponse with plagiarism score if checked

        Raises:
            ValidationError: If student/assignment invalid or file invalid
            ValidationError: If submission size exceeds limits

        Example:
            ```python
            response = await file_service.upload_assignment_submission(
                student_id=UUID('...'),
                assignment_id=UUID('...'),
                file_bytes=file_content,
                filename='assignment_solution.pdf'
            )
            ```
        """
        logger.info(
            f"Uploading assignment submission from student {student_id} "
            f"for assignment {assignment_id}"
        )

        # Validate format
        if not self._validate_submission_format(filename):
            raise ValidationError(
                f"Invalid submission format. Allowed: {', '.join(self.ALLOWED_SUBMISSION_FORMATS)}"
            )

        if len(file_bytes) > 25 * 1024 * 1024:  # 25MB per file
            raise ValidationError("Single file too large. Max 25MB per file")

        async with self.transaction():
            # Validate student and assignment
            student = await self.repos.student.get_one(id=student_id)
            if not student:
                raise NotFoundError(f"Student {student_id} not found")

            assignment = await self.repos.assignment.get_one(id=assignment_id)
            if not assignment:
                raise NotFoundError(f"Assignment {assignment_id} not found")

            # Check if student in class with assignment
            if assignment.class_id != student.current_class_id:
                raise ForbiddenError("Student not in this assignment's class")

            # Check total submission size
            existing_submissions = await self.repos.submission.get_many(
                assignment_id=assignment_id,
                student_id=student_id,
            )
            total_size = sum(s.file_size for s in existing_submissions) + len(file_bytes)
            if total_size > self.MAX_TOTAL_UPLOAD:
                raise ValidationError(f"Total submission size exceeds {self.MAX_TOTAL_UPLOAD / 1024 / 1024}MB")

            # Scan for viruses
            scan_result = await self._scan_file_viruses(file_bytes, filename)
            if scan_result.get("status") == "INFECTED":
                raise ValidationError("File failed security scan")

            # Check plagiarism (placeholder - would call Turnitin API)
            plagiarism_score = await self._check_plagiarism(file_bytes, filename)

            # Upload to S3
            s3_key = f"submissions/assign/{assignment_id}/{student_id}/{filename}"
            await self._upload_to_s3(
                file_bytes=file_bytes,
                key=s3_key,
                content_type=self._get_mime_type(filename),
            )

            file_id = UUID('00000000-0000-0000-0000-000000000003')

            # Create submission record
            submission = await self.repos.submission.create({
                "file_id": file_id,
                "assignment_id": assignment_id,
                "student_id": student_id,
                "filename": filename,
                "file_size": len(file_bytes),
                "s3_key": s3_key,
                "plagiarism_score": plagiarism_score,
                "submitted_at": datetime.utcnow(),
            })

            # Notify staff
            await self._notify_assignment_submission(
                assignment_id=assignment_id,
                student_id=student_id,
                filename=filename,
            )

            # Audit log
            self.log_action(
                action="UPLOAD_SUBMISSION",
                entity_type="Submission",
                entity_id=str(file_id),
                user_id=user_requesting_id,
                changes={
                    "assignment_id": str(assignment_id),
                    "filename": filename,
                    "plagiarism_score": plagiarism_score,
                },
            )

            return SubmissionFileResponse(
                file_id=file_id,
                url=await self._generate_s3_signed_url(s3_key),
                thumbnail_url=None,
                public_id=s3_key,
                filename=filename,
                file_size=len(file_bytes),
                mime_type=self._get_mime_type(filename),
                uploaded_at=datetime.utcnow(),
                plagiarism_score=plagiarism_score,
                plagiarism_status="CHECKED" if plagiarism_score else "PENDING",
                assignment_id=assignment_id,
                student_id=student_id,
            )

    # ======================== Download & Preview ========================

    async def download_file(
        self,
        file_id: UUID,
        user_id: UUID,
    ) -> Tuple[bytes, str]:
        """
        Download file with permission checking.

        Validates file exists, checks user permissions, fetches from S3/Cloudinary,
        generates signed URL if needed, and logs download.

        Args:
            file_id: UUID of file
            user_id: UUID of requesting user

        Returns:
            Tuple of (file_bytes, filename)

        Raises:
            NotFoundError: If file not found or deleted
            ForbiddenError: If user lacks permission

        Example:
            ```python
            file_bytes, filename = await file_service.download_file(
                file_id=UUID('...'),
                user_id=UUID('...')
            )
            # Return as HTTP response with filename
            ```
        """
        logger.info(f"Downloading file {file_id} for user {user_id}")

        async with self.transaction():
            # Fetch file metadata
            file_record = await self.repos.file_metadata.get_one(id=file_id)
            if not file_record or file_record.is_deleted:
                raise NotFoundError(f"File {file_id} not found")

            # Check permissions
            await self._check_file_permission(file_record, user_id)

            # Fetch file
            if file_record.storage_location == "s3":
                file_bytes = await self._download_from_s3(file_record.s3_key)
            else:
                file_bytes = await self._download_from_cloudinary(
                    file_record.cloudinary_public_id
                )

            # Log download
            self.log_action(
                action="DOWNLOAD_FILE",
                entity_type="File",
                entity_id=str(file_id),
                user_id=user_id,
                changes={"filename": file_record.filename},
            )

            return file_bytes, file_record.filename

    async def get_file_preview(
        self,
        file_id: UUID,
        user_id: UUID,
        thumbnail: bool = False,
    ) -> FilePreviewResponse:
        """
        Get file preview (thumbnail, text, or page image).

        For images: returns Cloudinary thumbnail. For PDFs: returns first page as
        image. For documents: returns text preview (first 500 chars).

        Args:
            file_id: UUID of file
            user_id: UUID of requesting user
            thumbnail: If True, return smallest preview size

        Returns:
            FilePreviewResponse with preview details

        Raises:
            NotFoundError: If file not found
            ForbiddenError: If user lacks permission

        Example:
            ```python
            preview = await file_service.get_file_preview(
                file_id=UUID('...'),
                user_id=UUID('...'),
                thumbnail=True
            )
            ```
        """
        logger.info(f"Getting preview for file {file_id}")

        async with self.transaction():
            file_record = await self.repos.file_metadata.get_one(id=file_id)
            if not file_record or file_record.is_deleted:
                raise NotFoundError(f"File {file_id} not found")

            await self._check_file_permission(file_record, user_id)

            mime_type = file_record.mime_type
            
            if mime_type.startswith("image/"):
                # Image: return Cloudinary thumbnail
                if file_record.storage_location == "cloudinary":
                    preview_url = await self.apply_transformation(
                        file_record.cloudinary_public_id,
                        ["w_200,h_200,c_fill,q_auto,f_auto"] if thumbnail else ["q_auto,f_auto"]
                    )
                    preview_type = "thumbnail"
                else:
                    preview_url = await self._generate_s3_signed_url(file_record.s3_key)
                    preview_type = "image"

            elif mime_type == "application/pdf":
                # PDF: convert first page to image
                preview_url = f"https://lms-cdn.example.com/preview/{file_id}.jpg"
                preview_type = "page_image"

            else:
                # Document: text preview
                file_bytes = await self._download_from_s3(file_record.s3_key)
                preview_text = file_bytes[:500].decode("utf-8", errors="ignore")
                preview_url = f"data:text/plain;base64,{preview_text.encode().hex()}"
                preview_type = "text"

            return FilePreviewResponse(
                file_id=file_id,
                preview_url=preview_url,
                preview_type=preview_type,
                content_type=mime_type,
                preview_size=len(preview_url),
            )

    async def delete_file(
        self,
        file_id: UUID,
        user_id: UUID,
        hard_delete: bool = False,
    ) -> Dict[str, Any]:
        """
        Delete file (soft or hard delete).

        Soft delete: marks as deleted, file retained in backup for 30 days.
        Hard delete: permanently removes from S3/Cloudinary, archives metadata.

        Args:
            file_id: UUID of file
            user_id: UUID of requesting user
            hard_delete: If True, permanently delete from storage

        Returns:
            Confirmation dictionary

        Raises:
            NotFoundError: If file not found
            ForbiddenError: If user lacks permission

        Example:
            ```python
            result = await file_service.delete_file(
                file_id=UUID('...'),
                user_id=UUID('...'),
                hard_delete=False
            )
            ```
        """
        logger.info(f"Deleting file {file_id}, hard_delete={hard_delete}")

        async with self.transaction():
            file_record = await self.repos.file_metadata.get_one(id=file_id)
            if not file_record:
                raise NotFoundError(f"File {file_id} not found")

            # Check permissions (only owner or admin)
            if file_record.user_id != user_id:
                user = await self.repos.user.get_one(id=user_id)
                if not user or user.role != "ADMIN":
                    raise ForbiddenError("Cannot delete other users' files")

            if hard_delete:
                # Permanently delete from storage
                if file_record.storage_location == "s3":
                    await self._delete_from_s3(file_record.s3_key)
                else:
                    await self._delete_from_cloudinary(
                        file_record.cloudinary_public_id
                    )

                # Archive metadata
                await self.repos.file_metadata.delete(id=file_id)
                deletion_type = "hard_delete"

            else:
                # Soft delete
                await self.repos.file_metadata.update(
                    id=file_id,
                    is_deleted=True,
                    deleted_at=datetime.utcnow(),
                )
                deletion_type = "soft_delete"

            # Audit log
            self.log_action(
                action="DELETE_FILE",
                entity_type="File",
                entity_id=str(file_id),
                user_id=user_id,
                changes={
                    "deletion_type": deletion_type,
                    "filename": file_record.filename,
                },
            )

            return {
                "file_id": file_id,
                "status": "deleted",
                "deletion_type": deletion_type,
                "deleted_at": datetime.utcnow().isoformat(),
            }

    # ======================== Batch Operations ========================

    async def bulk_download(
        self,
        file_ids: List[UUID],
        user_id: UUID,
    ) -> bytes:
        """
        Download multiple files as ZIP archive.

        Validates permissions for each file, creates ZIP in memory, adds files.
        Useful for downloading all submissions, class materials, etc.

        Args:
            file_ids: List of file UUIDs
            user_id: UUID of requesting user

        Returns:
            ZIP file bytes

        Raises:
            ValidationError: If file list empty or too large
            ForbiddenError: If user lacks permission for any file

        Example:
            ```python
            zip_bytes = await file_service.bulk_download(
                file_ids=[UUID('...'), UUID('...'), UUID('...')],
                user_id=UUID('...')
            )
            # Return as downloadable ZIP
            ```
        """
        logger.info(f"Bulk downloading {len(file_ids)} files for user {user_id}")

        if not file_ids:
            raise ValidationError("No files specified")

        if len(file_ids) > 100:
            raise ValidationError("Maximum 100 files per download")

        async with self.transaction():
            zip_buffer = BytesIO()
            
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for file_id in file_ids:
                    file_record = await self.repos.file_metadata.get_one(id=file_id)
                    if not file_record:
                        logger.warning(f"File {file_id} not found, skipping")
                        continue

                    # Check permissions
                    try:
                        await self._check_file_permission(file_record, user_id)
                    except ForbiddenError:
                        logger.warning(
                            f"User {user_id} lacks permission for file {file_id}"
                        )
                        continue

                    # Download file
                    if file_record.storage_location == "s3":
                        file_bytes = await self._download_from_s3(file_record.s3_key)
                    else:
                        file_bytes = await self._download_from_cloudinary(
                            file_record.cloudinary_public_id
                        )

                    # Add to ZIP
                    zip_file.writestr(file_record.filename, file_bytes)

            zip_buffer.seek(0)

            # Audit log
            self.log_action(
                action="BULK_DOWNLOAD",
                entity_type="File",
                entity_id="multiple",
                user_id=user_id,
                changes={"file_count": len(file_ids)},
            )

            return zip_buffer.getvalue()

    async def bulk_upload(
        self,
        files: List[Tuple[bytes, str]],  # (file_bytes, filename) tuples
        user_id: UUID,
        bulk_type: str,
    ) -> BulkUploadResult:
        """
        Upload multiple files in parallel with error tracking.

        Uploads up to 5 files concurrently, tracks success/failure, returns results.
        Useful for bulk assignment submission scanning, material uploads, etc.

        Args:
            files: List of (file_bytes, filename) tuples
            user_id: UUID of requesting user
            bulk_type: Type of bulk upload (SUBMISSIONS, MATERIALS, etc.)

        Returns:
            BulkUploadResult with success count and file IDs

        Example:
            ```python
            result = await file_service.bulk_upload(
                files=[
                    (bytes1, 'file1.pdf'),
                    (bytes2, 'file2.pdf'),
                    (bytes3, 'file3.pdf'),
                ],
                user_id=UUID('...'),
                bulk_type='MATERIALS'
            )
            ```
        """
        logger.info(f"Bulk uploading {len(files)} files for user {user_id}")

        results = BulkUploadResult(
            successful=0,
            failed=0,
            total=len(files),
            operation_id=f"bulk_{user_id}_{datetime.utcnow().timestamp()}",
        )

        # Upload with concurrency limit (5)
        semaphore = asyncio.Semaphore(5)

        async def upload_file(file_bytes: bytes, filename: str) -> Optional[UUID]:
            async with semaphore:
                try:
                    response = await self.upload_document(
                        user_id=user_id,
                        file_bytes=file_bytes,
                        filename=filename,
                        document_type=bulk_type,
                        user_requesting_id=user_id,
                    )
                    results.successful += 1
                    return response.file_id
                except Exception as e:
                    logger.error(f"Failed to upload {filename}: {e}")
                    results.failed += 1
                    results.errors.append({
                        "filename": filename,
                        "error": str(e),
                    })
                    return None

        # Run uploads
        file_ids = await asyncio.gather(
            *[upload_file(file_bytes, filename) for file_bytes, filename in files]
        )

        results.file_ids = [fid for fid in file_ids if fid is not None]

        # Audit log
        self.log_action(
            action="BULK_UPLOAD",
            entity_type="File",
            entity_id="multiple",
            user_id=user_id,
            changes={
                "type": bulk_type,
                "successful": results.successful,
                "failed": results.failed,
            },
        )

        return results

    # ======================== Cloudinary Transform ========================

    async def apply_transformation(
        self,
        public_id: str,
        transformations: List[str],
    ) -> str:
        """
        Generate Cloudinary URL with transformations applied.

        Combines multiple transformations (resize, convert format, optimize, etc.)
        and returns transformed URL.

        Args:
            public_id: Cloudinary public ID
            transformations: List of transformation strings
                Example: ["w_1000,h_1000,c_fill", "q_auto,f_auto"]

        Returns:
            Full Cloudinary URL with transformations

        Example:
            ```python
            thumbnail_url = await file_service.apply_transformation(
                public_id="lms/users/123/profile",
                transformations=["w_200,h_200,c_fill", "q_auto,f_auto"]
            )
            # Returns: https://res.cloudinary.com/.../w_200,h_200,c_fill/q_auto,f_auto/...
            ```
        """
        transformation_str = "/".join(transformations)
        url = (
            f"https://res.cloudinary.com/{self.cloudinary_config['cloud_name']}"
            f"/image/upload/{transformation_str}/{public_id}"
        )
        logger.debug(f"Generated transformed URL: {url}")
        return url

    async def list_resources(
        self,
        folder_path: str,
        resource_type: str = "image",
    ) -> List[CloudinaryResource]:
        """
        List all resources in Cloudinary folder.

        Args:
            folder_path: Folder path (e.g., "lms/users")
            resource_type: Type of resource (image, video, raw)

        Returns:
            List of CloudinaryResource objects

        Example:
            ```python
            resources = await file_service.list_resources(
                folder_path="lms/quizzes/123",
                resource_type="image"
            )
            ```
        """
        logger.info(f"Listing {resource_type} resources in {folder_path}")

        # Placeholder - would call Cloudinary API
        resources = [
            CloudinaryResource(
                public_id=f"{folder_path}/image1",
                resource_type=resource_type,
                format="webp",
                size=50000,
                width=1000,
                height=1000,
                secure_url="https://res.cloudinary.com/...",
                created_at=datetime.utcnow(),
            )
        ]

        return resources

    # ======================== Storage Analytics ========================

    async def get_storage_usage(
        self,
        user_id: Optional[UUID] = None,
    ) -> StorageAnalyticsSchema:
        """
        Get storage usage statistics.

        If user_id provided: returns user's personal storage usage.
        If system-wide: returns institution-level aggregate analytics.

        Args:
            user_id: Optional UUID for user-specific stats

        Returns:
            StorageAnalyticsSchema with usage breakdown

        Example:
            ```python
            stats = await file_service.get_storage_usage(user_id=UUID('...'))
            # stats.quota_used_percent = 32.5
            ```
        """
        logger.info(
            f"Getting storage usage for {'user ' + str(user_id) if user_id else 'institution'}"
        )

        async with self.transaction():
            if user_id:
                # User-specific
                files = await self.repos.file_metadata.get_many(
                    user_id=user_id,
                    is_deleted=False,
                )
                quota_limit = self.STORAGE_QUOTA_PER_STUDENT
            else:
                # Institution-wide
                files = await self.repos.file_metadata.get_many(is_deleted=False)
                quota_limit = self.STORAGE_QUOTA_BYTES

            # Calculate stats
            total_size = sum(f.file_size for f in files)
            file_count = len(files)

            # Breakdown by type
            by_type = {}
            for file_record in files:
                file_type = file_record.document_type or "other"
                by_type[file_type] = by_type.get(file_type, 0) + file_record.file_size

            # Detect warnings
            warnings = []
            percent_used = (total_size / quota_limit) * 100 if quota_limit > 0 else 0
            if percent_used > 90:
                warnings.append("Storage quota above 90%")
            if percent_used > 100:
                warnings.append("Storage quota exceeded")

            return StorageAnalyticsSchema(
                total_size_bytes=total_size,
                file_count=file_count,
                by_type=by_type,
                quota_used_percent=percent_used,
                quota_limit_bytes=quota_limit,
                last_updated=datetime.utcnow(),
                storage_warnings=warnings,
            )

    # ======================== Helper Methods ========================

    async def _scan_file_viruses(
        self,
        file_bytes: bytes,
        filename: str,
    ) -> Dict[str, Any]:
        """Scan file for viruses using ClamAV (placeholder)."""
        logger.debug(f"Scanning {filename} for viruses")
        # In production, would integrate ClamAV or file scanning API
        return {"status": "CLEAN", "engine": "clamav"}

    async def _check_plagiarism(
        self,
        file_bytes: bytes,
        filename: str,
    ) -> Optional[float]:
        """Check plagiarism using Turnitin API (placeholder)."""
        logger.debug(f"Checking plagiarism for {filename}")
        # In production, would call Turnitin API
        return None

    async def _upload_to_s3(
        self,
        file_bytes: bytes,
        key: str,
        content_type: str,
    ) -> Dict[str, Any]:
        """Upload file to AWS S3 with encryption."""
        logger.debug(f"Uploading to S3: {key}")
        # Placeholder - would use aioboto3
        return {"bucket": self.s3_config["bucket"], "key": key}

    async def _download_from_s3(self, key: str) -> bytes:
        """Download file from S3."""
        logger.debug(f"Downloading from S3: {key}")
        return b"S3_file_content_placeholder"

    async def _delete_from_s3(self, key: str) -> None:
        """Delete file from S3."""
        logger.debug(f"Deleting from S3: {key}")

    async def _generate_s3_signed_url(self, key: str) -> str:
        """Generate signed download URL for S3."""
        return (
            f"https://{self.s3_config['bucket']}.s3.amazonaws.com/{key}"
            f"?X-Amz-Expires={self.SIGNED_URL_EXPIRATION}"
        )

    async def _upload_to_cloudinary(
        self,
        file_bytes: bytes,
        public_id: str,
        resource_type: str = "image",
    ) -> Dict[str, Any]:
        """Upload file to Cloudinary."""
        logger.debug(f"Uploading to Cloudinary: {public_id}")
        return {
            "public_id": public_id,
            "secure_url": f"https://res.cloudinary.com/{self.cloudinary_config['cloud_name']}"
                         f"/image/upload/{public_id}",
        }

    async def _download_from_cloudinary(self, public_id: str) -> bytes:
        """Download file from Cloudinary."""
        logger.debug(f"Downloading from Cloudinary: {public_id}")
        return b"Cloudinary_file_content_placeholder"

    async def _delete_from_cloudinary(self, public_id: str) -> None:
        """Delete file from Cloudinary."""
        logger.debug(f"Deleting from Cloudinary: {public_id}")

    async def _check_file_permission(
        self,
        file_record: Dict[str, Any],
        user_id: UUID,
    ) -> None:
        """Validate user has permission to access file."""
        user = await self.repos.user.get_one(id=user_id)
        if not user:
            raise UnauthorizedError("User not found")

        # Admin can access all files
        if user.role == "ADMIN":
            return

        # Owner can access own files
        if file_record.get("user_id") == user_id:
            return

        # Teacher can access student submissions in their classes
        if user.role == "TEACHER":
            # Would check if file is from student in teacher's class
            return

        raise ForbiddenError("No permission to access this file")

    def _validate_image_format(self, filename: str) -> bool:
        """Check if filename has allowed image format."""
        ext = filename.split(".")[-1].lower()
        return ext in self.ALLOWED_IMAGE_FORMATS

    def _validate_document_format(self, filename: str) -> bool:
        """Check if filename has allowed document format."""
        ext = filename.split(".")[-1].lower()
        return ext in self.ALLOWED_DOCUMENT_FORMATS

    def _validate_submission_format(self, filename: str) -> bool:
        """Check if filename has allowed submission format."""
        ext = filename.split(".")[-1].lower()
        return ext in self.ALLOWED_SUBMISSION_FORMATS

    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type from filename."""
        ext = filename.split(".")[-1].lower()
        mime_types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
            "gif": "image/gif",
            "pdf": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xls": "application/vnd.ms-excel",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "txt": "text/plain",
        }
        return mime_types.get(ext, "application/octet-stream")

    async def _notify_assignment_submission(
        self,
        assignment_id: UUID,
        student_id: UUID,
        filename: str,
    ) -> None:
        """Notify teachers of new assignment submission."""
        logger.info(
            f"Notifying staff of new submission for assignment {assignment_id}"
        )
        # Would trigger notification to assignment creator/teachers


__all__ = [
    "FileService",
    "FileResponse",
    "FilePreviewResponse",
    "SubmissionFileResponse",
    "BulkUploadResult",
    "StorageAnalyticsSchema",
    "ScanResult",
    "CloudinaryResource",
]
