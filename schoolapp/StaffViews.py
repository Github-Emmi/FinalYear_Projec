import json
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.core import serializers
from django.urls import reverse
from schoolapp.models import *
from django.contrib.auth.decorators import login_required
from notifications.signals import notify
from django.shortcuts import get_object_or_404, render


@login_required
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

@login_required
def staff_profile(request):
    user=CustomUser.objects.get(id=request.user.id)
    staff=Staffs.objects.get(admin=user)
    return render(request,"staff_templates/staff_profile.html",{"user":user,"staff":staff})

@login_required
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

####### Assignment Views ###    
@login_required
def staff_add_assignment(request):
    staff = Staffs.objects.get(admin=request.user.id)
    assigned_subjects = Subjects.objects.filter(staff_id=staff.admin.id)
    assigned_classes = Class.objects.filter(id__in=assigned_subjects.values_list('class_id', flat=True).distinct())
    assigned_departments = Departments.objects.filter(id__in=assigned_subjects.values_list('department_id', flat=True).distinct())
    sessions = SessionYearModel.objects.all()

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        file = request.FILES.get("file")
        class_id = request.POST.get("class_id")
        department_id = request.POST.get("department_id")
        subject_id = request.POST.get("subject_id")
        session_year = request.POST.get("session_year")
        due_date = request.POST.get("due_date")

        try:
            class_obj = Class.objects.get(id=class_id)
            department_obj = Departments.objects.get(id=department_id)
            subject_obj = Subjects.objects.get(id=subject_id)
            session_obj = SessionYearModel.objects.get(id=session_year)

            assignment = Assignment.objects.create(
                title=title,
                description=description,
                file=file,
                class_id=class_obj,
                department_id=department_obj,
                subject=subject_obj,
                session_year=session_obj,
                staff=staff,
                due_date=due_date
            )

            students = Students.objects.filter(
                class_id=class_obj,
                department_id=department_obj,
                session_year_id=session_obj
            )
            for student in students:
                notify.send(
                    sender=request.user,
                    recipient=student.admin,
                    verb=f"New assignment posted: {assignment.title}",
                    description=assignment.description,
                    target=assignment
                )

            messages.success(request, "Assignment uploaded successfully and notifications sent.")
        except Exception as e:
            messages.error(request, f"Error: {e}")

        return redirect("staff_add_assignment")

    return render(request, "staff_templates/add_assignment.html", {
        "subjects": assigned_subjects,
        "classes": assigned_classes,
        "departments": assigned_departments,
        "sessions": sessions
    })



######## Attendance Views #######
@login_required
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
    student_ids = request.POST.get("student_ids")
    subject_id = request.POST.get("subject_id")
    attendance_date = request.POST.get("attendance_date")
    session_year_id = request.POST.get("session_year_id")

    subject_model = Subjects.objects.get(id=subject_id)
    session_model = SessionYearModel.objects.get(id=session_year_id)
    json_students = json.loads(student_ids)

    try:
        # Check if attendance already exists
        attendance, created = Attendence.objects.get_or_create(
            subject_id=subject_model,
            attendance_date=attendance_date,
            session_year_id=session_model
        )

        # If updating, delete old records
        if not created:
            AttendanceReport.objects.filter(attendance_id=attendance).delete()

        for student_data in json_students:
            student = Students.objects.get(admin=student_data['id'])
            AttendanceReport.objects.create(
                student_id=student,
                attendance_id=attendance,
                status=student_data['status']
            )

            # Notify each student
            # Send notification (no target to avoid link)
            message = "Attendance Created" if created else "Attendance Updated"

            notify.send(
                sender=request.user,
                recipient=student.admin,
                verb=message,
                description="Your attendance record has been updated.",
            )

        return HttpResponse("CREATED" if created else "UPDATED")

    except Exception as e:
        print("Error saving attendance:", e)
        return HttpResponse("ERR")

@login_required
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
    
@login_required   
def staff_apply_leave(request):
    staff_obj = Staffs.objects.get(admin=request.user.id)
    leave_data=LeaveReportStaff.objects.filter(staff_id=staff_obj)
    return render(request,"staff_templates/staff_apply_leave.html",{"leave_data":leave_data})

@login_required
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
        
@login_required       
def staff_feedback(request):
    staff_id=Staffs.objects.get(admin=request.user.id)
    feedback_data=FeedBackStaffs.objects.filter(staff_id=staff_id)
    return render(request,"staff_templates/staff_feedback.html",{"feedback_data":feedback_data})

@login_required
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

@login_required
def staff_add_result(request):
    subjects = Subjects.objects.filter(staff_id=request.user.id)
    session_years = SessionYearModel.objects.all()
    return render(request, "staff_templates/staff_add_results.html",{"subjects":subjects,"session_years":session_years})

@login_required
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

from django.core.paginator import Paginator

@login_required
def submission_list(request):
    staff = Staffs.objects.get(admin=request.user)
    qs = AssignmentSubmission.objects.filter(
        assignment__staff=staff,
        graded=False
    ).select_related('student__admin', 'assignment', 'assignment__class_id', 'assignment__session_year')

    # Filtering
    assignment_id = request.GET.get('assignment')
    session_id = request.GET.get('session')
    cls_id = request.GET.get('class')
    if assignment_id:
        qs = qs.filter(assignment_id=assignment_id)
    if session_id:
        qs = qs.filter(assignment__session_year_id=session_id)
    if cls_id:
        qs = qs.filter(assignment__class_id_id=cls_id)

    # Django Paginator
    paginator = Paginator(qs.order_by('-submitted_at'), 10)
    page = request.GET.get('page')
    submissions = paginator.get_page(page)

    # For filters dropdown
    assignments = Assignment.objects.filter(staff=staff)
    sessions = SessionYearModel.objects.all()
    classes = Class.objects.all()

    context = {
        'submissions': submissions,
        'assignments': assignments,
        'sessions': sessions,
        'classes': classes,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'staff_templates/submission_list_ajax.html', context)
    return render(request, 'staff_templates/submission_list.html', context)



@login_required
def staff_view_submissions(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    submissions = AssignmentSubmission.objects.filter(assignment=assignment).select_related('student__admin')

    return render(request, "staff_templates/assignment_submissions.html", {
        "assignment": assignment,
        "submissions": submissions
    })

@login_required
def staff_grade_submission(request, submission_id):
    submission = get_object_or_404(AssignmentSubmission, id=submission_id)

    if request.method == "POST":
        grade = request.POST.get("grade")
        feedback = request.POST.get("feedback")

        submission.grade = grade
        submission.feedback = feedback
        submission.graded = True
        submission.save()

        # 🔔 Notify student
        notify.send(
            sender=request.user,
            recipient=submission.student.admin,
            verb=f"Your assignment '{submission.assignment.title}' has been graded.",
            description=f"Grade: {grade}. Feedback: {feedback or 'No additional feedback.'}",
            target=submission.assignment
        )

        messages.success(request, "Submission graded successfully and student notified.")
        return redirect("staff_view_submissions", assignment_id=submission.assignment.id)

    return render(request, "staff_templates/grade_submission.html", {
        "submission": submission
    })

@login_required
def staff_timetable_view(request):
    staff = Staffs.objects.get(admin=request.user)

    # Fetch timetable entries assigned to this staff
    timetable_entries = TimeTable.objects.filter(teacher=staff).select_related(
        'subject', 'class_id', 'department_id', 'session_year'
    ).order_by('day', 'start_time')

    days = dict(TimeTable.DAY_CHOICES)

    return render(request, "staff_templates/staff_timetable.html", {
        "timetable": timetable_entries,
        "days": days
    })

@login_required
def staff_add_quiz(request):
    staff = Staffs.objects.get(admin=request.user)
    # Filter subjects assigned to this staff
    assigned_subjects = Subjects.objects.filter(staff_id=staff.admin.id)
    assigned_classes = Class.objects.filter(id__in=assigned_subjects.values_list('class_id', flat=True))
    assigned_departments = Departments.objects.filter(id__in=assigned_subjects.values_list('department_id', flat=True))
    sessions = SessionYearModel.objects.all()
    if request.method == "POST":
        title = request.POST.get("title")
        instructions = request.POST.get("instructions")
        subject_id = request.POST.get("subject_id")
        class_id = request.POST.get("class_id")
        department_id = request.POST.get("department_id")
        session_year_id = request.POST.get("session_year")
        deadline = request.POST.get("deadline")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")
        try:
            quiz = Quiz.objects.create(
                title=title,
                instructions=instructions,
                subject=Subjects.objects.get(id=subject_id),
                class_id=Class.objects.get(id=class_id),
                department_id=Departments.objects.get(id=department_id),
                session_year=SessionYearModel.objects.get(id=session_year_id),
                deadline=deadline,
                start_time=start_time,
                end_time=end_time,
                staff=staff
            )
            messages.success(request, "Quiz created successfully.")
            return redirect("staff_add_quiz")
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, "staff_templates/add_quiz.html", {
        "subjects": assigned_subjects,
        "classes": assigned_classes,
        "departments": assigned_departments,
        "sessions": sessions,
    })

@login_required
def staff_quiz_list(request):
    staff = Staffs.objects.get(admin=request.user)
    quizzes = Quiz.objects.filter(staff=staff).select_related("subject", "class_id", "department_id", "session_year")

    return render(request, "staff_templates/quiz_list.html", {
        "quizzes": quizzes
    })

@login_required
def staff_add_question_to_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, staff__admin=request.user)

    if request.method == "POST":
        question_text = request.POST.get("question_text")
        option_a = request.POST.get("option_a")
        option_b = request.POST.get("option_b")
        option_c = request.POST.get("option_c")
        option_d = request.POST.get("option_d")
        correct_answer = request.POST.get("correct_answer")

        try:
            Question.objects.create(
                quiz=quiz,
                question_text=question_text,
                option_a=option_a,
                option_b=option_b,
                option_c=option_c,
                option_d=option_d,
                correct_answer=correct_answer
            )
            messages.success(request, "Question added successfully.")
        except Exception as e:
            messages.error(request, f"Error: {e}")

        return redirect("staff_add_question_to_quiz", quiz_id=quiz.id)

    return render(request, "staff_templates/quiz_add_question.html", {
        "quiz": quiz
    })

@login_required
def staff_view_quiz_questions(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, staff__admin=request.user)
    questions = quiz.questions.all()

    return render(request, "staff_templates/quiz_question_list.html", {
        "quiz": quiz,
        "questions": questions
    })

@login_required
def staff_delete_question(request, question_id):
    question = get_object_or_404(Question, id=question_id, quiz__staff__admin=request.user)
    quiz_id = question.quiz.id
    question.delete()
    messages.success(request, "Question deleted.")
    return redirect("staff_view_quiz_questions", quiz_id=quiz_id)

@login_required
def toggle_quiz_status(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, staff__admin=request.user)

    if quiz.status == "DRAFT":
        quiz.status = "PUBLISHED"
        messages.success(request, f"✅ Quiz '{quiz.title}' is now Published.")
    else:
        quiz.status = "DRAFT"
        messages.info(request, f"⏸️ Quiz '{quiz.title}' is now in Draft mode.")

    quiz.save()
    return redirect("staff_quiz_list")
