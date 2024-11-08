import json
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.core import serializers
from django.urls import reverse
from schoolapp.models import CustomUser,Departments,SessionYearModel,Students,Subjects,Class,Attendence, AttendanceReport, Staffs, LeaveReportStaff, \
    StudentResults,FeedBackStaffs


def staff_home(request):
    #For Fetch All Student Under Staff
    subjects=Subjects.objects.filter(staff_id=request.user.id)

    department_id_list=[]
    for subject in subjects:
        department=Departments.objects.get(id=subject.department_id.id)
        department_id_list.append(department.id)

    final_department=[]
    #removing Duplicate Course ID
    for department_id in department_id_list:
        if department_id not in final_department:
            final_department.append(department_id)
    students_count=Students.objects.filter(department_id__in=final_department).count()
    
    #Fetch All Attendance Count
    attendance_count=Attendence.objects.filter(subject_id__in=subjects).count()

    #Fetch All Approve Leave
    staff=Staffs.objects.get(admin=request.user.id)
    leave_count=LeaveReportStaff.objects.filter(staff_id=staff.id,leave_status=1).count()
    subject_count=subjects.count()
    

    #Fetch Attendance Data by Subject
    subject_list=[]
    
    attendance_list=[]
    for subject in subjects:
        attendance_count1=Attendence.objects.filter(subject_id=subject.id).count()
        subject_list.append(subject.subject_name)
        
        attendance_list.append(attendance_count1)
        
 
    students_attendance=Students.objects.filter(department_id__in=final_department)
    student_list=[]
    student_list_attendance_present=[]
    student_list_attendance_absent=[]
    for student in students_attendance:
        attendance_present_count=AttendanceReport.objects.filter(status=True,student_id=student.id).count()
        attendance_absent_count=AttendanceReport.objects.filter(status=False,student_id=student.id).count()
        student_list.append(student.admin.username)
        student_list_attendance_present.append(attendance_present_count)
        student_list_attendance_absent.append(attendance_absent_count)

    return render(request,"staff_templates/staff-home.html",{"students_count":students_count,"attendance_count":attendance_count,"leave_count":leave_count,"subject_count":subject_count,"subject_list":subject_list,"attendance_list":attendance_list,"student_list":student_list,"present_list":student_list_attendance_present,"absent_list":student_list_attendance_absent})

def staff_profile(request):
    user=CustomUser.objects.get(id=request.user.id)
    staff=Staffs.objects.get(admin=user)
    return render(request,"staff_templates/staff_profile.html",{"user":user,"staff":staff})

def staff_profile_save(request):
    if request.method!="POST":
        return HttpResponseRedirect(reverse("staff_profile"))
    else:
        first_name=request.POST.get("first_name")
        last_name=request.POST.get("last_name")
        address=request.POST.get("address")
        password=request.POST.get("password")
        try:
            customuser=CustomUser.objects.get(id=request.user.id)
            customuser.first_name=first_name
            customuser.last_name=last_name
            if password!=None and password!="":
                customuser.set_password(password)
            customuser.save()

            staff=Staffs.objects.get(admin=customuser.id)
            staff.address=address
            staff.save()
            messages.success(request, "Successfully Updated Profile")
            return HttpResponseRedirect(reverse("staff_profile"))
        except:
            messages.error(request, "Failed to Update Profile")
            return HttpResponseRedirect(reverse("staff_profile"))
        
def staff_take_attendance(request):
    subjects=Subjects.objects.filter(staff_id=request.user.id)
    session_years=SessionYearModel.objects.all()
    return render(request,"staff_templates/take-attendance.html",{"subjects":subjects,"session_years":session_years})

@csrf_exempt
def get_students(request):
    subject_id=request.POST.get("subject")
    session_year=request.POST.get("session_year")

    subject=Subjects.objects.get(id=subject_id)
    session_model=SessionYearModel.objects.get(id=session_year)
    students=Students.objects.filter(department_id=subject.department_id,class_id=subject.class_id,session_year_id=session_model)
    list_data=[]

    for student in students:
        data_small={"id":student.admin.id,"name":student.admin.first_name+" "+student.admin.last_name}
        list_data.append(data_small)
    return JsonResponse(json.dumps(list_data),content_type="application/json",safe=False)

@csrf_exempt
def save_attendance_data(request):
    student_ids=request.POST.get("student_ids")
    subject_id=request.POST.get("subject_id")
    attendance_date=request.POST.get("attendance_date")
    session_year_id=request.POST.get("session_year_id")

    subject_model=Subjects.objects.get(id=subject_id)
    session_model=SessionYearModel.objects.get(id=session_year_id)
    json_sstudent=json.loads(student_ids)
    #print(data[0]['id'])


    try:
        attendance=Attendence(subject_id=subject_model,attendance_date=attendance_date,session_year_id=session_model)
        attendance.save()

        for stud in json_sstudent:
             student=Students.objects.get(admin=stud['id'])
             attendance_report=AttendanceReport(student_id=student,attendance_id=attendance,status=stud['status'])
             attendance_report.save()
        return HttpResponse("OK")
    except:
        return HttpResponse("ERR")
    
def staff_update_attendance(request):
    subjects=Subjects.objects.filter(staff_id=request.user.id)
    session_year_id=SessionYearModel.objects.all()
    return render(request,"staff_templates/staff_update_attendance.html",{"subjects":subjects,"session_year_id":session_year_id})

@csrf_exempt
def get_attendance_dates(request):
    subject=request.POST.get("subject")
    session_year_id=request.POST.get("session_year_id")
    subject_obj=Subjects.objects.get(id=subject)
    session_year_obj=SessionYearModel.objects.get(id=session_year_id)
    attendance=Attendence.objects.filter(subject_id=subject_obj,session_year_id=session_year_obj)
    attendance_obj=[]
    for attendance_single in attendance:
        data={"id":attendance_single.id,"attendance_date":str(attendance_single.attendance_date),"session_year_id":attendance_single.session_year_id.id}
        attendance_obj.append(data)

    return JsonResponse(json.dumps(attendance_obj),safe=False)

@csrf_exempt
def get_attendance_student(request):
    attendance_date=request.POST.get("attendance_date")
    attendance=Attendence.objects.get(id=attendance_date)

    attendance_data=AttendanceReport.objects.filter(attendance_id=attendance)
    list_data=[]

    for student in attendance_data:
        data_small={"id":student.student_id.admin.id,"name":student.student_id.admin.first_name+" "+student.student_id.admin.last_name,"status":student.status}
        list_data.append(data_small)
    return JsonResponse(json.dumps(list_data),content_type="application/json",safe=False)

@csrf_exempt
def save_updateattendance_data(request):
    student_ids=request.POST.get("student_ids")
    attendance_date=request.POST.get("attendance_date")
    attendance=Attendence.objects.get(id=attendance_date)

    json_sstudent=json.loads(student_ids)


    try:
        for stud in json_sstudent:
             student=Students.objects.get(admin=stud['id'])
             attendance_report=AttendanceReport.objects.get(student_id=student,attendance_id=attendance)
             attendance_report.status=stud['status']
             attendance_report.save()
        return HttpResponse("OK")
    except:
        return HttpResponse("ERR")
    
def staff_apply_leave(request):
    staff_obj = Staffs.objects.get(admin=request.user.id)
    leave_data=LeaveReportStaff.objects.filter(staff_id=staff_obj)
    return render(request,"staff_templates/staff_apply_leave.html",{"leave_data":leave_data})

def staff_apply_leave_save(request):
    if request.method!="POST":
        return HttpResponseRedirect(reverse("staff_apply_leave"))
    else:
        leave_date=request.POST.get("leave_date")
        leave_msg=request.POST.get("leave_msg")

        staff_obj=Staffs.objects.get(admin=request.user.id)
        try:
            leave_report=LeaveReportStaff(staff_id=staff_obj,leave_date=leave_date,leave_message=leave_msg,leave_status=0)
            leave_report.save()
            messages.success(request, "Successfully Applied for Leave")
            return HttpResponseRedirect(reverse("staff_apply_leave"))
        except:
            messages.error(request, "Failed To Apply for Leave")
            return HttpResponseRedirect(reverse("staff_apply_leave"))
        
def staff_feedback(request):
    staff_id=Staffs.objects.get(admin=request.user.id)
    feedback_data=FeedBackStaffs.objects.filter(staff_id=staff_id)
    return render(request,"staff_templates/staff_feedback.html",{"feedback_data":feedback_data})

def staff_feedback_save(request):
    if request.method!="POST":
        return HttpResponseRedirect(reverse("staff_feedback_save"))
    else:
        feedback_msg=request.POST.get("feedback_msg")

        staff_obj=Staffs.objects.get(admin=request.user.id)
        try:
            feedback=FeedBackStaffs(staff_id=staff_obj,feedback=feedback_msg,feedback_reply="")
            feedback.save()
            messages.success(request, "Successfully Sent Feedback")
            return HttpResponseRedirect(reverse("staff_feedback"))
        except:
            messages.error(request, "Failed To Send Feedback")
            return HttpResponseRedirect(reverse("staff_feedback"))

def staff_add_result(request):
    subjects = Subjects.objects.filter(staff_id=request.user.id)
    session_years = SessionYearModel.objects.all()
    return render(request, "staff_templates/staff_add_results.html",{"subjects":subjects,"session_years":session_years})


def save_student_result(request):
    if request.method!='POST':
        return HttpResponseRedirect('staff_add_result')
    student_admin_id=request.POST.get('student_list')
    test_marks=request.POST.get('test_marks')
    exam_marks=request.POST.get('exam_marks')
    total_result=request.POST.get('total_result') 
    remark=request.POST.get('teacher_comment')
    p_comment=request.POST.get('principal_comment')
    subject_id=request.POST.get('subject')
    session_year_id = request.POST.get('session_year')

    student_obj=Students.objects.get(admin=student_admin_id)
    subject_obj=Subjects.objects.get(id=subject_id)
    session_obj=SessionYearModel.objects.get(id=session_year_id)

    # try:
    check_exist=StudentResults.objects.filter(subject_id=subject_obj,student_id=student_obj,session_id=session_obj).exists()
    if check_exist:
        result=StudentResults.objects.get(subject_id=subject_obj,student_id=student_obj,session_id=session_obj)
        result.student_assignment_result=test_marks
        result.student_exam_result=exam_marks
        result.student_total_result=total_result
        result.score_remark=remark
        result.admincomment_id=p_comment
        result.save()
        messages.success(request, "Successfully Updated Result")
        return HttpResponseRedirect(reverse("staff_add_result"))
    else:
        result=StudentResults(subject_id=subject_obj,student_id=student_obj,session_id=session_obj,student_exam_result=exam_marks,
                              student_assignment_result=test_marks,student_total_result=total_result,score_remark=remark,admincomment_id=p_comment)
        result.save()
        messages.success(request, "Successfully Added Result")
        return HttpResponseRedirect(reverse("staff_add_result"))
    # # except:
    # #     messages.error(request, "Failed to Add Result")
    # #     return HttpResponseRedirect(reverse("staff_add_result"))
    