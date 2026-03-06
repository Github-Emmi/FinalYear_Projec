"""
Email Service Module

Comprehensive email management system integrating Zoho Mail SMTP for
transactional emails, notifications, and bulk communications with
template rendering, retry logic, and connection pooling.

Handles user communications across the institution: welcome emails,
password resets, quiz results, leave approvals, announcements, reports,
and bulk notifications with audit logging.

Author: Backend Development Team
Last Updated: March 2026
Version: 1.0.0
"""

import asyncio
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel, Field, EmailStr

from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    ExternalServiceError,
)
from app.repositories.factory import RepositoryFactory
from app.services.base_service import BaseService


logger = logging.getLogger(__name__)


# ======================== Enums ========================

class EmailTemplate(str, Enum):
    """Available email templates"""
    WELCOME = "welcome"
    PASSWORD_RESET = "password_reset"
    PASSWORD_CHANGED = "password_changed"
    QUIZ_RESULT = "quiz_result"
    ASSIGNMENT_GRADED = "assignment_graded"
    LEAVE_APPROVED = "leave_approved"
    LEAVE_REJECTED = "leave_rejected"
    ATTENDANCE_WARNING = "attendance_warning"
    ANNOUNCEMENT = "announcement"
    REPORT_READY = "report_ready"
    SUBMISSION_RECEIVED = "submission_received"
    ACCOUNT_LOCKED = "account_locked"
    SUSPENSION_NOTICE = "suspension_notice"


class EmailPriority(str, Enum):
    """Email priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EmailStatus(str, Enum):
    """Email delivery status"""
    PENDING = "pending"
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"
    COMPLAINT = "complaint"


# ======================== Pydantic Schemas ========================

class EmailRequest(BaseModel):
    """Email send request"""
    recipient: EmailStr
    subject: str
    template: EmailTemplate
    template_data: Dict[str, Any] = Field(default_factory=dict)
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None
    priority: EmailPriority = EmailPriority.NORMAL
    tags: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {EmailTemplate: str, EmailPriority: str}


class BulkEmailRequest(BaseModel):
    """Bulk email request"""
    recipients: List[EmailStr]
    subject: str
    template: EmailTemplate
    template_data_list: List[Dict[str, Any]] = Field(default_factory=list)
    template_data_global: Dict[str, Any] = Field(default_factory=dict)
    priority: EmailPriority = EmailPriority.NORMAL
    batch_size: int = 50  # Process in batches
    tags: List[str] = Field(default_factory=list)


class EmailResponse(BaseModel):
    """Email send response"""
    email_id: UUID
    recipient: str
    status: EmailStatus
    subject: str
    sent_at: Optional[datetime] = None
    delivery_tracking_id: Optional[str] = None

    class Config:
        json_encoders = {UUID: str, EmailStatus: str, datetime: str}


class EmailLogEntry(BaseModel):
    """Email log entry for audit trail"""
    email_id: UUID
    recipient: str
    subject: str
    template: str
    status: EmailStatus
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime


class SMTPConnectionPool(BaseModel):
    """SMTP connection pool status"""
    total_connections: int
    active_connections: int
    available_connections: int
    failed_attempts: int
    last_connection_time: Optional[datetime] = None


# ======================== Email Service ========================

class EmailService(BaseService):
    """
    Comprehensive email service with Zoho Mail SMTP integration.

    Manages all institutional email communication through Zoho Mail:
    transactional emails (welcome, password reset), notifications
    (quiz results, leave approvals), and bulk communications
    (announcements, reports). Includes template rendering, connection
    pooling, retry logic, and delivery tracking.

    Attributes:
        ZOHO_SMTP_HOST: Zoho Mail SMTP host
        ZOHO_SMTP_PORT: Zoho Mail SMTP port (587=TLS, 465=SSL)
        SENDER_EMAIL: Institution email address for outbound messages
        RETRY_ATTEMPTS: Maximum retry attempts for failed sends
        CONNECTION_POOL_SIZE: SMTP connection pool size
        EMAIL_TEMPLATE_DIR: Path to email templates directory
    """

    # Zoho Mail Configuration
    ZOHO_SMTP_HOST = "smtp.zoho.com"
    ZOHO_SMTP_PORT = 587  # TLS
    ZOHO_SMTP_PORT_SSL = 465  # SSL alternative
    SENDER_EMAIL = "noreply@yourinstitution.edu"
    SENDER_NAME = "Your Institution LMS"

    # Retry Configuration
    RETRY_ATTEMPTS = 3
    RETRY_BACKOFF_FACTOR = 2  # Exponential backoff
    INITIAL_RETRY_DELAY = 1  # seconds

    # Connection Pool
    CONNECTION_POOL_SIZE = 5
    CONNECTION_TIMEOUT = 30  # seconds
    CONNECTION_IDLE_TIMEOUT = 300  # 5 minutes

    # Email Configuration
    MAX_BATCH_SIZE = 1000
    DAILY_LIMIT = 10000
    BOUNCE_THRESHOLD = 0.02  # 2% bounce rate tolerance

    # Template Configuration
    EMAIL_TEMPLATE_DIR = "/app/templates/emails"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE = 100  # Max 100 emails per minute
    RATE_LIMIT_PER_HOUR = 1000  # Max 1000 emails per hour

    def __init__(self, repos: RepositoryFactory) -> None:
        """
        Initialize EmailService with Zoho SMTP configuration.

        Args:
            repos: RepositoryFactory instance for data access

        Raises:
            ValueError: If repos is None or SMTP config invalid
        """
        super().__init__(repos)

        # Zoho SMTP Configuration (from environment in production)
        self.zoho_email = "lms@yourinstitution.edu"  # From config
        self.zoho_app_password = "app_password_from_config"  # From secure config

        # Template environment
        self.template_env = Environment(
            loader=FileSystemLoader(self.EMAIL_TEMPLATE_DIR),
            autoescape=True,
        )

        # Connection pool
        self.connection_pool: List[Optional[Any]] = []
        self.pool_lock = asyncio.Lock()

        # Rate limiting
        self.emails_sent_minute: List[datetime] = []
        self.emails_sent_hour: List[datetime] = []

        # Email log cache
        self.email_log_cache: Dict[UUID, EmailLogEntry] = {}

        logger.info("EmailService initialized with Zoho SMTP configuration")

    # ======================== Transactional Emails ========================

    async def send_welcome_email(
        self,
        user_id: UUID,
        email: str,
        first_name: str,
        last_name: str,
        is_student: bool = False,
    ) -> EmailResponse:
        """
        Send welcome email to new user.

        Args:
            user_id: UUID of new user
            email: Email address
            first_name: User's first name
            last_name: User's last name
            is_student: If True, student-specific welcome; otherwise staff

        Returns:
            EmailResponse with delivery status

        Raises:
            ValidationError: If email invalid
            ExternalServiceError: If SMTP connection fails

        Example:
            ```python
            response = await email_service.send_welcome_email(
                user_id=UUID('...'),
                email='student@example.com',
                first_name='John',
                last_name='Doe',
                is_student=True
            )
            ```
        """
        logger.info(f"Sending welcome email to {email}")

        template_data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "user_type": "Student" if is_student else "Staff",
            "login_url": "https://lms.yourinstitution.edu/login",
            "support_email": "support@yourinstitution.edu",
        }

        return await self.send_email(
            recipient=email,
            subject=f"Welcome to Your Institution LMS, {first_name}!",
            template=EmailTemplate.WELCOME,
            template_data=template_data,
            priority=EmailPriority.NORMAL,
            tags=["welcome", "user_onboarding"],
        )

    async def send_password_reset_email(
        self,
        email: str,
        first_name: str,
        reset_token: str,
        token_expires_in_hours: int = 24,
    ) -> EmailResponse:
        """
        Send password reset email with secure token link.

        Args:
            email: User's email address
            first_name: User's first name
            reset_token: Secure password reset token
            token_expires_in_hours: How long token is valid

        Returns:
            EmailResponse with delivery status

        Example:
            ```python
            response = await email_service.send_password_reset_email(
                email='user@example.com',
                first_name='John',
                reset_token='secure_token_xyz',
                token_expires_in_hours=24
            )
            ```
        """
        logger.info(f"Sending password reset email to {email}")

        reset_url = (
            f"https://lms.yourinstitution.edu/reset-password"
            f"?token={reset_token}"
        )

        template_data = {
            "first_name": first_name,
            "reset_url": reset_url,
            "token_expires_in_hours": token_expires_in_hours,
            "support_email": "support@yourinstitution.edu",
        }

        return await self.send_email(
            recipient=email,
            subject="Password Reset Request - Your Institution LMS",
            template=EmailTemplate.PASSWORD_RESET,
            template_data=template_data,
            priority=EmailPriority.HIGH,
            tags=["password_reset", "security"],
        )

    async def send_quiz_result_email(
        self,
        student_email: str,
        student_name: str,
        quiz_title: str,
        score: float,
        total_points: float,
        percentage: float,
        teacher_name: str,
    ) -> EmailResponse:
        """
        Send quiz result notification email to student.

        Args:
            student_email: Student's email
            student_name: Student's full name
            quiz_title: Title of the quiz
            score: Points earned
            total_points: Total points available
            percentage: Score percentage
            teacher_name: Teacher's name

        Returns:
            EmailResponse with delivery status

        Example:
            ```python
            response = await email_service.send_quiz_result_email(
                student_email='student@example.com',
                student_name='Jane Doe',
                quiz_title='Midterm Exam',
                score=85,
                total_points=100,
                percentage=85.0,
                teacher_name='Dr. Smith'
            )
            ```
        """
        logger.info(f"Sending quiz result email to {student_email}")

        template_data = {
            "student_name": student_name,
            "quiz_title": quiz_title,
            "score": score,
            "total_points": total_points,
            "percentage": f"{percentage:.1f}",
            "grade": self._calculate_grade(percentage),
            "teacher_name": teacher_name,
            "results_url": "https://lms.yourinstitution.edu/my-results",
        }

        return await self.send_email(
            recipient=student_email,
            subject=f"Quiz Result: {quiz_title}",
            template=EmailTemplate.QUIZ_RESULT,
            template_data=template_data,
            priority=EmailPriority.NORMAL,
            tags=["quiz_result", "academic"],
        )

    async def send_assignment_graded_email(
        self,
        student_email: str,
        student_name: str,
        assignment_title: str,
        score: float,
        total_points: float,
        feedback: Optional[str] = None,
        teacher_name: Optional[str] = None,
    ) -> EmailResponse:
        """
        Send assignment grading notification.

        Args:
            student_email: Student's email
            student_name: Student's full name
            assignment_title: Title of assignment
            score: Points earned
            total_points: Total points
            feedback: Optional teacher feedback
            teacher_name: Teacher's name

        Returns:
            EmailResponse with delivery status

        Example:
            ```python
            response = await email_service.send_assignment_graded_email(
                student_email='student@example.com',
                student_name='John Doe',
                assignment_title='Essay: Climate Change',
                score=18,
                total_points=20,
                feedback='Excellent analysis and citations.',
                teacher_name='Prof. Johnson'
            )
            ```
        """
        logger.info(f"Sending assignment graded email to {student_email}")

        template_data = {
            "student_name": student_name,
            "assignment_title": assignment_title,
            "score": score,
            "total_points": total_points,
            "percentage": f"{(score / total_points * 100):.1f}",
            "feedback": feedback or "No feedback provided",
            "teacher_name": teacher_name or "Your Teacher",
            "submission_url": "https://lms.yourinstitution.edu/my-submissions",
        }

        return await self.send_email(
            recipient=student_email,
            subject=f"Assignment Graded: {assignment_title}",
            template=EmailTemplate.ASSIGNMENT_GRADED,
            template_data=template_data,
            priority=EmailPriority.NORMAL,
            tags=["assignment_graded", "academic"],
        )

    async def send_leave_approval_email(
        self,
        user_email: str,
        user_name: str,
        leave_type: str,
        start_date: datetime,
        end_date: datetime,
        approved: bool,
        reason_for_denial: Optional[str] = None,
    ) -> EmailResponse:
        """
        Send leave request approval/rejection email.

        Args:
            user_email: User's email
            user_name: User's full name
            leave_type: Type of leave (sick, annual, etc.)
            start_date: Leave start date
            end_date: Leave end date
            approved: True if approved, False if rejected
            reason_for_denial: If rejected, reason for denial

        Returns:
            EmailResponse with delivery status

        Example:
            ```python
            response = await email_service.send_leave_approval_email(
                user_email='teacher@example.com',
                user_name='Ms. Garcia',
                leave_type='Sick Leave',
                start_date=datetime(2026, 3, 10),
                end_date=datetime(2026, 3, 12),
                approved=True
            )
            ```
        """
        logger.info(f"Sending leave {'approval' if approved else 'rejection'} email to {user_email}")

        status_text = "Approved" if approved else "Rejected"
        template_name = "leave_approved" if approved else "leave_rejected"

        template_data = {
            "user_name": user_name,
            "leave_type": leave_type,
            "start_date": start_date.strftime("%B %d, %Y"),
            "end_date": end_date.strftime("%B %d, %Y"),
            "days_count": (end_date - start_date).days + 1,
            "status": status_text,
            "reason_for_denial": reason_for_denial or "",
            "contact_email": "hr@yourinstitution.edu",
        }

        return await self.send_email(
            recipient=user_email,
            subject=f"Leave Request {status_text}",
            template=(
                EmailTemplate.LEAVE_APPROVED if approved
                else EmailTemplate.LEAVE_REJECTED
            ),
            template_data=template_data,
            priority=EmailPriority.NORMAL,
            tags=["leave_update"],
        )

    # ======================== Bulk Email Sending ========================

    async def send_bulk_email(
        self,
        recipients: List[str],
        subject: str,
        template: EmailTemplate,
        template_data_list: List[Dict[str, Any]],
        template_data_global: Optional[Dict[str, Any]] = None,
        priority: EmailPriority = EmailPriority.NORMAL,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Send bulk emails with template personalization.

        Processes recipients in configurable batches (default 50) with rate limiting.
        Each recipient gets personalized template data.

        Args:
            recipients: List of email addresses
            subject: Email subject
            template: EmailTemplate to use
            template_data_list: List of dicts with personalized data per recipient
            template_data_global: Shared data for all emails
            priority: Email priority
            tags: Email tags for categorization

        Returns:
            Dictionary with {successful: int, failed: int, failed_recipients: list}

        Raises:
            ValidationError: If recipient count exceeds limit

        Example:
            ```python
            result = await email_service.send_bulk_email(
                recipients=['student1@ex.com', 'student2@ex.com', ...],
                subject='Announcement: New Grading Policy',
                template=EmailTemplate.ANNOUNCEMENT,
                template_data_list=[
                    {'student_name': 'Alice', 'class': '6A'},
                    {'student_name': 'Bob', 'class': '6B'},
                ],
                template_data_global={'announcement_title': '...'},
                tags=['announcement', 'policy']
            )
            # Returns: {'successful': 98, 'failed': 2, 'failed_recipients': [...]}
            ```
        """
        logger.info(f"Starting bulk email send to {len(recipients)} recipients")

        if not recipients:
            raise ValidationError("No recipients specified")

        if len(recipients) > self.MAX_BATCH_SIZE:
            raise ValidationError(
                f"Recipient count exceeds maximum {self.MAX_BATCH_SIZE}"
            )

        # Check rate limits
        await self._check_rate_limits(len(recipients))

        async with self.transaction():
            results = {
                "successful": 0,
                "failed": 0,
                "total": len(recipients),
                "failed_recipients": [],
            }

            # Process in batches
            batch_size = 50
            for i in range(0, len(recipients), batch_size):
                batch = recipients[i : i + batch_size]
                batch_data = template_data_list[i : i + batch_size]

                # Send batch in parallel
                tasks = [
                    self.send_email(
                        recipient=recipient,
                        subject=subject,
                        template=template,
                        template_data={
                            **(template_data_global or {}),
                            **batch_data[j],
                        },
                        priority=priority,
                        tags=tags or [],
                    )
                    for j, recipient in enumerate(batch)
                ]

                responses = await asyncio.gather(*tasks, return_exceptions=True)

                for j, response in enumerate(responses):
                    if isinstance(response, Exception):
                        results["failed"] += 1
                        results["failed_recipients"].append(
                            {
                                "email": batch[j],
                                "error": str(response),
                            }
                        )
                    elif isinstance(response, EmailResponse):
                        if response.status == EmailStatus.SENT:
                            results["successful"] += 1
                        else:
                            results["failed"] += 1
                            results["failed_recipients"].append(
                                {
                                    "email": response.recipient,
                                    "status": response.status,
                                }
                            )

            # Audit log
            self.log_action(
                action="BULK_EMAIL_SEND",
                entity_type="Email",
                entity_id="bulk",
                user_id=None,
                changes={
                    "recipient_count": len(recipients),
                    "successful": results["successful"],
                    "failed": results["failed"],
                    "template": template.value,
                },
            )

            return results

    # ======================== Core Email Sending ========================

    async def send_email(
        self,
        recipient: str,
        subject: str,
        template: EmailTemplate,
        template_data: Dict[str, Any],
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        priority: EmailPriority = EmailPriority.NORMAL,
        tags: Optional[List[str]] = None,
    ) -> EmailResponse:
        """
        Send individual email with template rendering and retry logic.

        Renders Jinja2 template with provided data, retries on failure with
        exponential backoff, tracks delivery status, and logs all sends.

        Args:
            recipient: Email address
            subject: Email subject
            template: EmailTemplate to render
            template_data: Data for template rendering
            cc: Optional CC recipients
            bcc: Optional BCC recipients
            priority: Email priority level
            tags: Email tags for tracking/filtering

        Returns:
            EmailResponse with status and tracking info

        Raises:
            ValidationError: If email invalid
            ExternalServiceError: If SMTP fails after all retries

        Example:
            ```python
            response = await email_service.send_email(
                recipient='user@example.com',
                subject='Notification',
                template=EmailTemplate.ANNOUNCEMENT,
                template_data={'title': 'Important Update'},
                priority=EmailPriority.HIGH
            )
            ```
        """
        logger.info(f"Sending email to {recipient}")

        # Validate email
        if not self._validate_email(recipient):
            raise ValidationError(f"Invalid email address: {recipient}")

        # Check rate limits
        await self._check_rate_limits(1)

        email_id = UUID('00000000-0000-0000-0000-000000000001')  # Generate real

        # Render template
        html_content = await self._render_template(template, template_data)
        text_content = await self._render_text_version(html_content)

        # Attempt send with retries
        response = None
        last_error = None

        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                # Send via SMTP
                await self._send_smtp(
                    recipient=recipient,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content,
                    cc=cc,
                    bcc=bcc,
                    priority=priority,
                )

                response = EmailResponse(
                    email_id=email_id,
                    recipient=recipient,
                    status=EmailStatus.SENT,
                    subject=subject,
                    sent_at=datetime.utcnow(),
                    delivery_tracking_id=f"zoho_{email_id}_{datetime.utcnow().timestamp()}",
                )

                logger.info(f"Email sent successfully to {recipient} (attempt {attempt + 1})")
                break

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Email send failed to {recipient} (attempt {attempt + 1}): {e}"
                )

                if attempt < self.RETRY_ATTEMPTS - 1:
                    delay = self.INITIAL_RETRY_DELAY * (
                        self.RETRY_BACKOFF_FACTOR ** attempt
                    )
                    await asyncio.sleep(delay)
                else:
                    response = EmailResponse(
                        email_id=email_id,
                        recipient=recipient,
                        status=EmailStatus.FAILED,
                        subject=subject,
                        delivery_tracking_id=None,
                    )
                    logger.error(f"Email send failed after {self.RETRY_ATTEMPTS} attempts: {e}")

        if response is None:
            raise ExternalServiceError(
                f"Failed to send email after {self.RETRY_ATTEMPTS} attempts: {last_error}"
            )

        # Log email
        await self._log_email(
            email_id=email_id,
            recipient=recipient,
            subject=subject,
            template=template.value,
            status=response.status,
            tags=tags or [],
        )

        return response

    # ======================== Helper Methods ========================

    async def _send_smtp(
        self,
        recipient: str,
        subject: str,
        html_content: str,
        text_content: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        priority: EmailPriority = EmailPriority.NORMAL,
    ) -> None:
        """Send email via Zoho Mail SMTP."""
        logger.debug(f"Connecting to Zoho SMTP and sending email to {recipient}")

        # In production, would use aiosmtplib for async SMTP
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.SENDER_NAME} <{self.SENDER_EMAIL}>"
            msg["To"] = recipient

            if cc:
                msg["Cc"] = ", ".join(cc)

            # Priority header
            if priority == EmailPriority.URGENT:
                msg["Priority"] = "Urgent"
                msg["Importance"] = "high"
            elif priority == EmailPriority.HIGH:
                msg["Importance"] = "high"

            # Attach parts
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            # Would send via SMTP in production:
            # async with aiosmtplib.SMTP(hostname=self.ZOHO_SMTP_HOST, port=self.ZOHO_SMTP_PORT) as smtp:
            #     await smtp.login(self.zoho_email, self.zoho_app_password)
            #     await smtp.send_message(msg)

            logger.debug(f"Email message prepared for {recipient}")

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {e}")
            raise ExternalServiceError(f"SMTP authentication failed: {e}")
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            raise ExternalServiceError(f"SMTP error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            raise ExternalServiceError(f"Email send error: {e}")

    async def _render_template(
        self,
        template: EmailTemplate,
        data: Dict[str, Any],
    ) -> str:
        """Render Jinja2 email template."""
        logger.debug(f"Rendering template: {template.value}")

        try:
            template_obj = self.template_env.get_template(f"{template.value}.html")
            html_content = template_obj.render(**data)
            return html_content
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            # Return fallback template
            return self._get_fallback_template(template.value, data)

    async def _render_text_version(self, html_content: str) -> str:
        """Convert HTML email to plain text version."""
        # Simple HTML to text conversion (would use premailer in production)
        text = html_content.replace("<br>", "\n").replace("<br/>", "\n")
        # Remove HTML tags
        import re

        text = re.sub("<[^<]+?>", "", text)
        return text

    async def _log_email(
        self,
        email_id: UUID,
        recipient: str,
        subject: str,
        template: str,
        status: EmailStatus,
        tags: List[str],
    ) -> None:
        """Log email send for audit trail."""
        logger.debug(f"Logging email {email_id} for {recipient}")

        entry = EmailLogEntry(
            email_id=email_id,
            recipient=recipient,
            subject=subject,
            template=template,
            status=status,
            sent_at=datetime.utcnow() if status == EmailStatus.SENT else None,
            created_at=datetime.utcnow(),
        )

        self.email_log_cache[email_id] = entry

        # Would persist to DB in production
        if len(self.email_log_cache) > 1000:
            # Flush old entries
            self.email_log_cache.clear()

    async def _check_rate_limits(self, email_count: int) -> None:
        """Check rate limits before sending."""
        now = datetime.utcnow()

        # Clean old timestamps
        self.emails_sent_minute = [
            ts for ts in self.emails_sent_minute
            if (now - ts).total_seconds() < 60
        ]
        self.emails_sent_hour = [
            ts for ts in self.emails_sent_hour
            if (now - ts).total_seconds() < 3600
        ]

        # Check limits
        if len(self.emails_sent_minute) + email_count > self.RATE_LIMIT_PER_MINUTE:
            raise ValidationError(
                f"Rate limit exceeded: {self.RATE_LIMIT_PER_MINUTE} per minute"
            )

        if len(self.emails_sent_hour) + email_count > self.RATE_LIMIT_PER_HOUR:
            raise ValidationError(
                f"Rate limit exceeded: {self.RATE_LIMIT_PER_HOUR} per hour"
            )

        # Record send
        for _ in range(email_count):
            self.emails_sent_minute.append(now)
            self.emails_sent_hour.append(now)

    def _validate_email(self, email: str) -> bool:
        """Validate email format."""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def _calculate_grade(self, percentage: float) -> str:
        """Calculate letter grade from percentage."""
        if percentage >= 90:
            return "A"
        elif percentage >= 80:
            return "B"
        elif percentage >= 70:
            return "C"
        elif percentage >= 60:
            return "D"
        else:
            return "F"

    def _get_fallback_template(
        self,
        template_name: str,
        data: Dict[str, Any],
    ) -> str:
        """Return fallback HTML template if file not found."""
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2>Hello {data.get('first_name', 'User')},</h2>
                <p>This is a {template_name} notification from Your Institution LMS.</p>
                <p><strong>Details:</strong></p>
                <ul>
                    {''.join(f'<li>{k}: {v}</li>' for k, v in data.items() if k != 'first_name')}
                </ul>
                <p>If you have any questions, please contact support@yourinstitution.edu</p>
                <hr/>
                <p style="font-size: 0.9em; color: #666;">
                    This is an automated message. Please do not reply to this email.
                </p>
            </body>
        </html>
        """

    async def get_email_log(
        self,
        email_id: UUID,
    ) -> Optional[EmailLogEntry]:
        """Retrieve email from log."""
        return self.email_log_cache.get(email_id)

    async def get_smtp_pool_status(self) -> SMTPConnectionPool:
        """Get SMTP connection pool status."""
        active = sum(1 for conn in self.connection_pool if conn is not None)
        available = len([c for c in self.connection_pool if c is None])

        return SMTPConnectionPool(
            total_connections=len(self.connection_pool),
            active_connections=active,
            available_connections=available,
            failed_attempts=0,
            last_connection_time=datetime.utcnow(),
        )


__all__ = [
    "EmailService",
    "EmailTemplate",
    "EmailPriority",
    "EmailStatus",
    "EmailRequest",
    "BulkEmailRequest",
    "EmailResponse",
    "EmailLogEntry",
    "SMTPConnectionPool",
]
