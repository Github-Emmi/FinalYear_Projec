from django.db import models
from django.contrib.auth.models import AbstractUser
from django.dispatch.dispatcher import receiver
from django.db.models.signals import post_save
from django.conf import settings
from django.utils import timezone


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

class Attendence(models.Model):
    id = models.AutoField(primary_key=True)
    subject_id = models.ForeignKey(Subjects, on_delete=models.CASCADE)
    session_year_id = models.ForeignKey(SessionYearModel, on_delete=models.CASCADE)
    attendance_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()


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
    session_year = models.ForeignKey(SessionYearModel, on_delete=models.CASCADE)
    staff = models.ForeignKey(Staffs, on_delete=models.CASCADE)
    due_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def is_due(self):
        return timezone.now() > self.due_date

    def __str__(self):
        return f"{self.title} ({self.class_id} - {self.department_id})"

####### Assignment Submission Model #######
class AssignmentSubmission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    student = models.ForeignKey(Students, on_delete=models.CASCADE)
    submitted_file = models.FileField(upload_to="submitted_assignments/")
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded = models.BooleanField(default=False)
    grade = models.CharField(max_length=10, null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ('assignment', 'student')  # prevent multiple submissions

    def __str__(self):
        return f"{self.student.admin.username} - {self.assignment.title}"


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


class FeedBackStaffs(models.Model):
    id = models.AutoField(primary_key=True)
    staff_id = models.ForeignKey(Staffs, on_delete=models.CASCADE)
    feedback = models.TextField()
    feedback_reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()


class NotificationStudent(models.Model):
    id = models.AutoField(primary_key=True)
    student_id = models.ForeignKey(Students, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()


class NotificationStaffs(models.Model):
    id = models.AutoField(primary_key=True)
    staff_id = models.ForeignKey(Staffs, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()


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
