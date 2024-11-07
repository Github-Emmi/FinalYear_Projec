from django.db import models
from django.contrib.auth.models import AbstractUser
from django.dispatch.dispatcher import receiver
from django.db.models.signals import post_save 


# Create your models here.

    # creating CustomUser Models
class CustomUser(AbstractUser):
    user_type_data = ((1,"HOD"),(2,"Staff"),(3,"Student"))
    user_type = models.CharField(default=1, choices=user_type_data, max_length=10 )
    
   # Session Year models Lives Here:  
class SessionYearModel(models.Model):
    id = models.AutoField(primary_key=True)
    session_name = models.CharField(max_length=225)
    session_start_year = models.DateField()
    session_end_year = models.DateField()
    objects = models.Manager()
    
 # creating Amin models
class AdminHOD(models.Model):
    id = models.AutoField(primary_key=True)
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()
    
    # creating Staff models
class Staffs(models.Model):
    id=models.AutoField(primary_key=True)
    admin=models.OneToOneField(CustomUser,on_delete=models.CASCADE)
    address=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now_add=True)
    objects=models.Manager()
  
    # creating a department 
class Departments(models.Model):
    id = models.AutoField(primary_key=True)
    department_name = models.CharField(max_length= 225)
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
    
    # creating Courses(subject) Models
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
    gender = models.CharField(max_length= 225)
    profile_pic = models.FileField()
    address = models.TextField()  
    date_of_birth = models.CharField(max_length= 225)
    class_id = models.ForeignKey(Class, on_delete=models.DO_NOTHING) 
    department_id = models.ForeignKey(Departments, on_delete=models.DO_NOTHING)
    session_year_id = models.ForeignKey(SessionYearModel, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()    
    
        # creating Attendence Models
class Attendence(models.Model):
    id = models.AutoField(primary_key=True)
    subject_id = models.ForeignKey(Subjects, on_delete=models.DO_NOTHING)
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
    score_remark = models.CharField(max_length= 225)
    admincomment_id = models.CharField(max_length= 225)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager() 
    
    # creating AttendenceReport Models
class AttendanceReport(models.Model):
    id = models.AutoField(primary_key=True)
    student_id = models.ForeignKey(Students, on_delete=models.DO_NOTHING)
    attendance_id = models.ForeignKey(Attendence, on_delete=models.CASCADE)
    status=models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager() 
    
class LeaveReportStudent(models.Model):
    id = models.AutoField(primary_key=True)
    student_id = models.ForeignKey(Students, on_delete=models.CASCADE)
    leave_date = models.CharField(max_length= 225)
    leave_message =  models.TextField()
    leave_status = models.IntegerField(default=0) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()    
    
class LeaveReportStaff(models.Model):
    id = models.AutoField(primary_key=True)
    staff_id = models.ForeignKey(Staffs, on_delete=models.CASCADE)
    leave_date = models.CharField(max_length= 225)
    leave_message =  models.TextField()
    leave_status = models.IntegerField(default=0) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager() 
    
class FeedBackStudent(models.Model):
    id = models.AutoField(primary_key=True)
    student_id = models.ForeignKey(Students, on_delete=models.CASCADE)
    feedback = models.TextField()
    feedback_reply =  models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()    
    
class FeedBackStaffs(models.Model):
    id = models.AutoField(primary_key=True)
    staff_id = models.ForeignKey(Staffs, on_delete=models.CASCADE)
    feedback = models.TextField()
    feedback_reply =  models.TextField()
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
    message =  models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    objects = models.Manager()     
    
@receiver(post_save, sender=CustomUser)
def create_user_profile(sender,instance,created,**kwargs):
    if created:
        if instance.user_type==1:
            AdminHOD.objects.create(admin=instance)
        if instance.user_type==2:
            Staffs.objects.create(admin=instance,address="")
        if instance.user_type==3:
            Students.objects.create(admin=instance,class_id=Class.objects.get(id=1),department_id=Departments.objects.get(id=1),session_year_id=SessionYearModel.objects.get(id=1),address="",profile_pic="",gender="")
    
@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    if instance.user_type==1:
        instance.adminhod.save()
    if instance.user_type==2:
        instance.staffs.save()  
    if instance.user_type==3:
        instance.students.save()    