import datetime
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.core.files.storage import FileSystemStorage
from schoolapp.models import *
from django.contrib.auth.decorators import login_required

@login_required
def student_home(request):
    user = CustomUser.objects.get(id=request.user.id)
    students = Students.objects.get(admin=user)
    student_obj=Students.objects.get(admin=request.user.id)
    attendance_total=AttendanceReport.objects.filter(student_id=student_obj).count()
    attendance_present=AttendanceReport.objects.filter(student_id=student_obj,status=True).count()
    attendance_absent=AttendanceReport.objects.filter(student_id=student_obj,status=False).count()
    department=Departments.objects.get(id=student_obj.department_id.id)
    classes=Class.objects.get(id=student_obj.class_id.id)
    subjects=Subjects.objects.filter(department_id=department.id,class_id=classes.id).count()
    subjects_data=Subjects.objects.filter(department_id=department,class_id=classes)
    session_obj=SessionYearModel.objects.get(id=student_obj.session_year_id.id)
    
    subject_name=[]
    data_present=[]
    data_absent=[]
    subject_data=Subjects.objects.filter(department_id=student_obj.department_id, class_id=student_obj.class_id)
    for subject in subject_data:
        attendance=Attendence.objects.filter(subject_id=subject.id)
        attendance_present_count=AttendanceReport.objects.filter(attendance_id__in=attendance,status=True,student_id=student_obj.id).count()
        attendance_absent_count=AttendanceReport.objects.filter(attendance_id__in=attendance,status=False,student_id=student_obj.id).count()
        subject_name.append(subject.subject_name)
        data_present.append(attendance_present_count)
        data_absent.append(attendance_absent_count)
    
    return render(request,"student_templates/student_home.html",{"total_attendance":attendance_total,"attendance_absent":attendance_absent,"attendance_present":attendance_present,"subjects":subjects,"data_name":subject_name,"data1":data_present,"data2":data_absent,'subjects_data':subjects_data,'session_obj':session_obj,'students':students})

@login_required
def student_profile(request):
    user=CustomUser.objects.get(id=request.user.id)
    students=Students.objects.get(admin=user)
    return render(request,"student_templates/student_profile.html",{"user":user,"students":students})

@login_required
def student_profile_save(request):
    if request.method != "POST":
        return HttpResponseRedirect(reverse("student_profile"))
    else:
        first_name= request.POST.get("first_name")
        last_name= request.POST.get("last_name")
        address= request.POST.get("address")
        password= request.POST.get("password")  
        if request.FILES.get('profile_pic',False):
                profile_pic=request.FILES['profile_pic']
                fs=FileSystemStorage()
                filename=fs.save(profile_pic.name,profile_pic)
                profile_pic_url=fs.url(filename)
        else:
            profile_pic_url=None
        try:
            user= CustomUser.objects.get(id=request.user.id)
            user.first_name= first_name
            user.last_name= last_name
            if password!= None and password!="":
                password.set_password(password)
            user.save()  
            #### getting student data via admin user is
            students= Students.objects.get(admin=user.id)
            students.address= address
            if profile_pic_url!=None:
                students.profile_pic=profile_pic_url
            students.save()
            messages.success(request, "Profiled Saved!")
            return HttpResponseRedirect(reverse("student_profile"))
        except:
            messages.success(request, "Profiled Failed To Saved!")
            return HttpResponseRedirect(reverse("student_profile"))
        

# schoolapp/StudentViews.py
@login_required
def student_chatroom(request):
    student = Students.objects.get(admin=request.user)
    room = Room.objects.filter(is_classroom_room =True, classroom_id=student.class_id).first()
    if not room:
        return render(request, 'student_templates/error.html', {'message': 'No chatroom available for your class.'})
    classmates = Students.objects.filter(class_id=student.class_id).select_related('admin')
    return render(request, 'student_templates/chatroom.html', {'room': room, 'participants': classmates})


@login_required
def student_view_attendance(request):
    user = CustomUser.objects.get(id=request.user.id)
    students = Students.objects.get(admin=user)
    student= Students.objects.get(admin=request.user.id)
    department=student.department_id
    classes = student.class_id
    subjects= Subjects.objects.filter(department_id=department, class_id=classes)
    return render(request,"student_templates/student_view_attendance.html",{"subjects":subjects,'students':students})

@login_required
def student_view_attendance_post(request):
    subject_id=request.POST.get("subject")
    start_date=request.POST.get("start_date")
    end_date=request.POST.get("end_date")

    start_data_parse=datetime.datetime.strptime(start_date,"%Y-%m-%d").date()
    end_data_parse=datetime.datetime.strptime(end_date,"%Y-%m-%d").date()
    subject_obj=Subjects.objects.get(id=subject_id)
    user_object=CustomUser.objects.get(id=request.user.id)
    stud_obj=Students.objects.get(admin=user_object) 
    user = CustomUser.objects.get(id=request.user.id)
    students = Students.objects.get(admin=user)
    
    attendance=Attendence.objects.filter(attendance_date__range=(start_data_parse,end_data_parse),subject_id=subject_obj)
    attendance_reports=AttendanceReport.objects.filter(attendance_id__in=attendance,student_id=stud_obj)
    return render(request,"student_templates/student_attendance_data.html",{"attendance_reports":attendance_reports,"students":students})

@login_required
def student_apply_leave(request):
    user = CustomUser.objects.get(id=request.user.id)
    students = Students.objects.get(admin=user)
    student_obj = Students.objects.get(admin=request.user.id)
    leave_data=LeaveReportStudent.objects.filter(student_id=student_obj)
    return render(request,"student_templates/student_apply_leave.html",{"leave_data":leave_data,"students":students})

@login_required
def student_apply_leave_save(request):
    if request.method!="POST":
        return HttpResponseRedirect(reverse("student_apply_leave"))
    else:
        leave_date=request.POST.get("leave_date")
        leave_msg=request.POST.get("leave_msg")

        student_obj=Students.objects.get(admin=request.user.id)
        try:
            leave_report=LeaveReportStudent(student_id=student_obj,leave_date=leave_date,leave_message=leave_msg,leave_status=0)
            leave_report.save()
            messages.success(request, "Successfully Applied for Leave")
            return HttpResponseRedirect(reverse("student_apply_leave"))
        except:
            messages.error(request, "Failed To Apply for Leave")
            return HttpResponseRedirect(reverse("student_apply_leave"))

@login_required
def student_feedback(request):
    user = CustomUser.objects.get(id=request.user.id)
    students = Students.objects.get(admin=user)
    student_id=Students.objects.get(admin=request.user.id)
    feedback_data=FeedBackStudent.objects.filter(student_id=student_id)
    return render(request,"student_templates/student_feedback.html",{"feedback_data":feedback_data,"students":students})

@login_required
def student_feedback_save(request):
    if request.method!="POST":
        return HttpResponseRedirect(reverse("student_feedback_save"))
    else:
        feedback_msg=request.POST.get("feedback_msg")

        student_obj=Students.objects.get(admin=request.user.id)
        try:
            feedback=FeedBackStudent(student_id=student_obj,feedback=feedback_msg,feedback_reply="")
            feedback.save()
            messages.success(request, "Successfully Sent Feedback")
            return HttpResponseRedirect(reverse("student_feedback"))
        except:
            messages.error(request, "Failed To Send Feedback")
            return HttpResponseRedirect(reverse("student_feedback"))

@login_required
def student_view_result(request):
    student_obj=Students.objects.get(admin=request.user.id)
    attendance_total=AttendanceReport.objects.filter(student_id=student_obj).count()
    attendance_present=AttendanceReport.objects.filter(student_id=student_obj,status=True).count()
    attendance_absent=AttendanceReport.objects.filter(student_id=student_obj,status=False).count()
    user = CustomUser.objects.get(id=request.user.id)
    students = Students.objects.get(admin=user)
    student=Students.objects.get(admin=request.user.id)
    studentresult=StudentResults.objects.filter(student_id=student.id)
    session_obj=SessionYearModel.objects.get(id=student_obj.session_year_id.id)
    return render(request,"student_templates/student_result.html",{"total_attendance":attendance_total,"attendance_absent":attendance_absent,"attendance_present":attendance_present,"studentresult":studentresult,"students":students,"session_obj":session_obj})

@login_required
def student_make_payment(request):
    user= CustomUser.objects.get(id=request.user.id)
    students= Students.objects.get(admin=user)
    return render(request,"student_templates/make_payment.html",{"students":students})
