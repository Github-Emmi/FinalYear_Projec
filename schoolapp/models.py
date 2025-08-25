from django.db import models
from django.contrib.auth.models import AbstractUser
from django.dispatch.dispatcher import receiver
from django.db.models.signals import post_save
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.urls import reverse
from difflib import SequenceMatcher
import openai
from django.utils.translation import gettext_lazy as _
from schoolapp.storages import RawMediaCloudinaryStorage  # adjust path if needed

# Create your models here.


# creating CustomUser Models
class CustomUser(AbstractUser):
    user_type_data = ((1, "HOD"), (2, "Staff"), (3, "Student"))
    user_type = models.CharField(default=1, choices=user_type_data, max_length=10)


class RememberToken(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

# Session Year models Lives Here:
class SessionYearModel(models.Model):
    id = models.AutoField(primary_key=True)
    session_name = models.CharField(max_length=225)
    session_start_year = models.DateField()
    session_end_year = models.DateField()
    objects = models.Manager()
    def __str__(self):
        # Format dates as "14 June 2023"
        start_date = self.session_start_year.strftime("%d %B %Y")
        end_date = self.session_end_year.strftime("%d %B %Y")
        return f"{start_date} TO {end_date}"
    


# creating Amin models
class AdminHOD(models.Model):
    id = models.AutoField(primary_key=True)
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()

    # creating Staff models


class Staffs(models.Model):
    id = models.AutoField(primary_key=True)
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    address = models.TextField()
    session_year_id = models.ForeignKey(SessionYearModel, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()
    
    def __str__(self):
        return self.admin.first_name + " " + self.admin.last_name
    def get_absolute_url(self):
        # Opens the admin’s staff chat focused on this staff member
        return reverse("staff_feedback_chat", args=[self.id])

# creating a department
class Departments(models.Model):
    id = models.AutoField(primary_key=True)
    department_name = models.CharField(max_length=225)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()

    class Meta:
        pass

    def __str__(self):
        return self.department_name

    # creating Class Models


class Class(models.Model):
    id = models.AutoField(primary_key=True)
    class_name = models.CharField(max_length=225)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()

    class Meta:
        pass

    def __str__(self):
        return self.class_name


class Subjects(models.Model):
    id = models.AutoField(primary_key=True)
    subject_name = models.CharField(max_length=225)
    class_id = models.ForeignKey(Class, on_delete=models.CASCADE, default=1)
    department_id = models.ForeignKey(Departments, on_delete=models.CASCADE, default=1)
    staff_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()

    # creating Students Models
class Students(models.Model):
    id = models.AutoField(primary_key=True)
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    gender = models.CharField(max_length=225)
    age = models.CharField(max_length=225)
    height = models.CharField(max_length=225)
    weight = models.CharField(max_length=225)
    eye_color = models.CharField(max_length=225)
    place_of_birth = models.CharField(max_length=225)
    home_town = models.CharField(max_length=225)
    state_of_origin = models.CharField(max_length=225)
    lga = models.CharField(max_length=225)
    nationality = models.CharField(max_length=225)
    residential_address = models.CharField(max_length=225)
    bus_stop = models.CharField(max_length=225)
    religion = models.CharField(max_length=225)
    father_name = models.CharField(max_length=225)
    father_address = models.CharField(max_length=225)
    father_occupation = models.CharField(max_length=225)
    father_postion = models.CharField(max_length=225)
    father_phone_num_1 = models.CharField(max_length=225)
    father_phone_num_2 = models.CharField(max_length=225)
    mother_name = models.CharField(max_length=225)
    mother_address = models.CharField(max_length=225)
    mother_occupation = models.CharField(max_length=225)
    mother_position = models.CharField(max_length=225)
    mother_phone_num_1 = models.CharField(max_length=225)
    mother_phone_num_2 = models.CharField(max_length=225)
    last_class = models.CharField(max_length=225)
    school_attended_last = models.CharField(max_length=225)
    profile_pic = models.FileField(upload_to="media/profile_pics/")
    date_of_birth = models.CharField(max_length=225)
    asthmatic = models.CharField(max_length=3, default="")
    hypertension = models.CharField(max_length=3, default="")
    disabilities = models.CharField(max_length=3, default="")
    epilepsy = models.CharField(max_length=3, default="")
    blind = models.CharField(max_length=3, default="")
    mental_illness = models.CharField(max_length=3, default="")
    tuberculosis = models.CharField(max_length=3, default="")
    spectacle_use = models.CharField(max_length=3, default="")
    sickle_cell = models.CharField(max_length=3, default="")
    health_problems = models.TextField(blank=True, null=True, max_length=225)
    medication = models.TextField(blank=True, null=True, max_length=225)
    drug_allergy = models.TextField(blank=True, null=True, max_length=225)

    class_id = models.ForeignKey(Class, on_delete=models.CASCADE)
    department_id = models.ForeignKey(Departments, on_delete=models.CASCADE)
    session_year_id = models.ForeignKey(SessionYearModel, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()
    def get_absolute_url(self):
        return reverse("student_feedback_chat", args=[self.id])

class Attendence(models.Model):
    id = models.AutoField(primary_key=True)
    subject_id = models.ForeignKey(Subjects, on_delete=models.CASCADE)
    session_year_id = models.ForeignKey(SessionYearModel, on_delete=models.CASCADE)
    attendance_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()

    def __str__(self):
        return f"{self.subject_id.subject_name} - {self.attendance_date}"

    def get_absolute_url(self):
        return reverse("save_updateattendance_data") + f"?date={self.attendance_date}&subject_id={self.subject_id.id}&session_id={self.session_year_id.id}"


class StudentResults(models.Model):
    id = models.AutoField(primary_key=True)
    student_id = models.ForeignKey(Students, on_delete=models.CASCADE)
    subject_id = models.ForeignKey(Subjects, on_delete=models.CASCADE)
    session_id = models.ForeignKey(SessionYearModel, on_delete=models.CASCADE)
    student_exam_result = models.FloatField(default=0)
    student_assignment_result = models.FloatField(default=0)
    student_total_result = models.FloatField(default=0)
    score_remark = models.CharField(max_length=225)
    admincomment_id = models.CharField(max_length=225)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()


###### Assignment Model ####### 
class Assignment(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    file = models.FileField(upload_to="assignments/")
    class_id = models.ForeignKey(Class, on_delete=models.CASCADE)
    department_id = models.ForeignKey(Departments, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subjects, default="", on_delete=models.CASCADE)
    session_year = models.ForeignKey(SessionYearModel, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staffs, on_delete=models.CASCADE)
    due_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_due(self):
        return timezone.now() > self.due_date

    def __str__(self):
        return f"{self.title} ({self.class_id} - {self.department_id})"
    
    def get_absolute_url(self):
        return reverse('student_assignment_detail', kwargs={'assignment_id': self.id})
    

####### Assignment Submission Model #######
class AssignmentSubmission(models.Model):
    assignment = models.ForeignKey('Assignment', on_delete=models.CASCADE)
    student = models.ForeignKey('Students', on_delete=models.CASCADE)
    submitted_file = models.FileField(
        upload_to="submitted_assignments/",
        storage=RawMediaCloudinaryStorage()
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded = models.BooleanField(default=False)
    grade = models.CharField(max_length=10, null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ('assignment', 'student')
    def __str__(self):
        return f"{self.student.admin.username} - {self.assignment.title}"
    def get_absolute_url(self):
        return reverse('student_assignments')
    def get_absolute_url(self):
        return reverse("student_submission_feedback", args=[self.id])
    def get_absolute_url(self):
        return reverse("staff_view_submission_detail", args=[self.id])
    def get_absolute_url(self):
        return reverse("student_submission_feedback", args=[self.id])



    # creating AttendenceReport Models
class AttendanceReport(models.Model):
    id = models.AutoField(primary_key=True)
    student_id = models.ForeignKey(Students, on_delete=models.CASCADE)
    attendance_id = models.ForeignKey(Attendence, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()


class LeaveReportStudent(models.Model):
    id = models.AutoField(primary_key=True)
    student_id = models.ForeignKey(Students, on_delete=models.CASCADE)
    leave_date = models.CharField(max_length=225)
    leave_message = models.TextField()
    leave_status = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()


class LeaveReportStaff(models.Model):
    id = models.AutoField(primary_key=True)
    staff_id = models.ForeignKey(Staffs, on_delete=models.CASCADE)
    leave_date = models.CharField(max_length=225)
    leave_message = models.TextField()
    leave_status = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()


class FeedBackStudent(models.Model):
    id = models.AutoField(primary_key=True)
    student_id = models.ForeignKey(Students, on_delete=models.CASCADE)
    feedback = models.TextField()
    feedback_reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()
    def get_absolute_url(self):
        # STUDENT (recipient of admin’s message) to open their chat page.
        return reverse("student_feedback")


class FeedBackStaffs(models.Model):
    id = models.AutoField(primary_key=True)
    staff_id = models.ForeignKey(Staffs, on_delete=models.CASCADE)
    feedback = models.TextField()
    feedback_reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()


User = get_user_model()

class NotificationStudent(models.Model):
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notification_student'  # <--- unique related name here
    )
    verb = models.CharField(max_length=255,)
    description = models.TextField(blank=True)
    link = models.URLField(blank=True)
    read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']


class NotificationStaffs(models.Model):
    recipient = models.ForeignKey(
        User, default="",
        on_delete=models.CASCADE,
        related_name='notification_staff'  # <--- unique related name here
    )
    verb = models.CharField(max_length=255, default="")
    description = models.TextField(blank=True)
    link = models.URLField(blank=True)
    read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

class Event(models.Model):
    EVENT_TYPES = [
        ('EVENT', 'Event'),
        ('EXAM', 'Exam'),
        ('HOLIDAY', 'Holiday'),
        ('RESULT', 'Result Release'),
        ('OTHER', 'Other'),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='EVENT')
    event_datetime = models.DateTimeField()
    related_session = models.ForeignKey(SessionYearModel, on_delete=models.SET_NULL, null=True, blank=True)
    target_audience = models.CharField(max_length=20, choices=[('ALL', 'All'), ('STUDENTS', 'Students'), ('STAFFS', 'Staffs')])
    created_at = models.DateTimeField(auto_now_add=True)
    def get_event_color(self):
        return {
            'EXAM': '#007bff',
            'HOLIDAY': '#dc3545',
            'RESULT': '#ffc107',
            'GENERAL': '#28a745',
            'ASSIGNMENT': '#6610f2'
        }.get(self.event_type, '#6c757d')  # Default grey
    def get_absolute_url(self):
        return reverse('event_detail', kwargs={'event_id': self.id})

class TimeTable(models.Model):
    DAY_CHOICES = [
        ('MON', 'Monday'),
        ('TUE', 'Tuesday'),
        ('WED', 'Wednesday'),
        ('THU', 'Thursday'),
        ('FRI', 'Friday'),
        ('SAT', 'Saturday'),
    ]
    subject = models.ForeignKey(Subjects, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Staffs, on_delete=models.SET_NULL, null=True, blank=True)
    class_id = models.ForeignKey(Class, on_delete=models.CASCADE)
    department_id = models.ForeignKey(Departments, on_delete=models.CASCADE)
    session_year = models.ForeignKey(SessionYearModel, on_delete=models.CASCADE)
    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    classroom = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['day', 'start_time']
    def __str__(self):
        return f"{self.subject.subject_name} - {self.day} {self.start_time}-{self.end_time}"
    
# =====================
# QUIZ MODELS
# =====================

class Quiz(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PUBLISHED', 'Published'),
    ]

    title = models.CharField(max_length=255)
    instructions = models.TextField()
    subject = models.ForeignKey(Subjects, on_delete=models.CASCADE)
    class_id = models.ForeignKey(Class, on_delete=models.CASCADE)
    department_id = models.ForeignKey(Departments, on_delete=models.CASCADE)
    session_year = models.ForeignKey(SessionYearModel, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staffs, on_delete=models.CASCADE)

    deadline = models.DateTimeField()  # Notify students before this time
    duration_minutes = models.PositiveIntegerField(default=30)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="DRAFT"
    )  # Accessible only when published
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.subject.subject_name}"
    def get_absolute_url(self):
        return reverse("admin_quiz_detail", args=[self.id])


class Question(models.Model):
    QUESTION_TYPE_CHOICES = [
        ("MCQ", "Multiple Choice"),
        ("OPEN", "Open-Ended"),
    ]

    quiz = models.ForeignKey(Quiz, related_name="questions", on_delete=models.CASCADE)
    question_text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES, default="MCQ")

    # For MCQs
    option_a = models.CharField(max_length=255, blank=True, null=True)
    option_b = models.CharField(max_length=255, blank=True, null=True)
    option_c = models.CharField(max_length=255, blank=True, null=True)
    option_d = models.CharField(max_length=255, blank=True, null=True)
    correct_answer = models.CharField(
        max_length=1,
        choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")],
        blank=True, null=True
    )

    # For open-ended
    correct_text_answer = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.quiz.title} - {self.question_text[:50]}"


class StudentQuizSubmission(models.Model):
    student = models.ForeignKey(Students, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    total_score = models.FloatField(default=0.0)
    is_graded = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.admin.get_full_name()} - {self.quiz.title}"

    def grade_submission(self, use_ai=True):
        """
        Grade all answers in this submission.
        - Calls StudentAnswer.grade_answer() on each answer.
        - Calculates total score.
        """
        total_questions = self.quiz.questions.count()
        correct_answers = 0

        for answer in self.answers.all():
            if answer.grade_answer(use_ai=use_ai):
                correct_answers += 1

        # Score as percentage
        self.total_score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        self.is_graded = True
        self.save()
        return self.total_score

class StudentAnswer(models.Model):
    submission = models.ForeignKey(StudentQuizSubmission, related_name='answers', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.CharField(
        max_length=1,
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')],
        null=True, blank=True
    )
    text_answer = models.TextField(null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    ai_confidence = models.FloatField(null=True, blank=True)  # Confidence score if AI graded

    def __str__(self):
        return f"{self.submission.student.admin.get_full_name()} - QID: {self.question.id}"

    def grade_answer(self, use_ai=True):
        """
        Grade this answer automatically.
        If use_ai=True and it's an open-ended question, use GPT to grade.
        """
        # ✅ Case 1: Multiple Choice
        if self.question.question_type == 'MCQ':
            if self.selected_option == self.question.correct_answer:
                self.is_correct = True
            else:
                self.is_correct = False
            self.ai_confidence = 1.0
            self.save()
            return self.is_correct

        # ✅ Case 2: Short Answer (Open-ended)
        if self.question.question_type == 'OPEN':
            # Fallback simple similarity check
            if self.question.correct_text_answer:
                ratio = SequenceMatcher(None, self.text_answer.lower(), self.question.correct_text_answer.lower()).ratio()
                if ratio > 0.85:  # simple similarity threshold
                    self.is_correct = True
                    self.ai_confidence = ratio
                    self.save()
                    return True

            if use_ai:
                try:
                    # Call OpenAI API
                    openai.api_key = settings.OPENAI_API_KEY

                    prompt = f"""
                    You are an examiner grading a student's answer.
                    Question: {self.question.question_text}
                    Correct Answer: {self.question.correct_text_answer}
                    Student's Answer: {self.text_answer}

                    Score the student's answer strictly as Correct or Incorrect.
                    Respond in JSON with fields:
                    {{
                        "is_correct": true/false,
                        "confidence": float between 0 and 1
                    }}
                    """

                    response = openai.ChatCompletion.create(
                        model="gpt-4o-mini",  # or "gpt-4" / "gpt-5" when available
                        messages=[{"role": "system", "content": "You are a strict but fair exam grader."},
                                  {"role": "user", "content": prompt}],
                        max_tokens=150,
                        temperature=0
                    )

                    ai_output = response.choices[0].message["content"].strip()

                    # Parse AI output safely
                    import json
                    result = json.loads(ai_output)

                    self.is_correct = result.get("is_correct", False)
                    self.ai_confidence = result.get("confidence", 0.5)
                    self.save()
                    return self.is_correct

                except Exception as e:
                    print("AI grading failed:", str(e))
                    # Fallback to marking as ungraded
                    self.is_correct = False
                    self.ai_confidence = None
                    self.save()
                    return False

        return False


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.user_type == 1:
            AdminHOD.objects.create(admin=instance)
        elif instance.user_type == 2:
            session_year_obj, _ = SessionYearModel.objects.get_or_create(id=1)
            Staffs.objects.create(admin=instance, session_year_id=session_year_obj)
        elif instance.user_type == 3:
            class_obj, _ = Class.objects.get_or_create(id=1)
            department_obj, _ = Departments.objects.get_or_create(id=1)
            session_year_obj, _ = SessionYearModel.objects.get_or_create(id=1)
            Students.objects.create(
                admin=instance,
                age="",
                gender="",
                height="",
                weight="",
                eye_color="",
                place_of_birth="",
                home_town="",
                state_of_origin="",
                lga="",
                nationality="",
                residential_address="",
                bus_stop="",
                religion="",
                father_name="",
                father_address="",
                father_occupation="",
                father_postion="",
                father_phone_num_1="",
                father_phone_num_2="",
                mother_name="",
                mother_address="",
                mother_occupation="",
                mother_position="",
                mother_phone_num_1="",
                mother_phone_num_2="",
                last_class="",
                school_attended_last="",
                profile_pic="",
                date_of_birth="",
                asthmatic = "",
                hypertension="",
                disabilities="",
                epilepsy="",
                blind="",
                mental_illness="",
                tuberculosis="",
                spectacle_use="",
                sickle_cell="",
                health_problems="",
                medication="",
                drug_allergy="",
                class_id=class_obj,
                department_id=department_obj,
                session_year_id=session_year_obj,
            )


@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    if instance.user_type == 1:
        instance.adminhod.save()
    if instance.user_type == 2:
        instance.staffs.save()
    if instance.user_type == 3:
        instance.students.save()
