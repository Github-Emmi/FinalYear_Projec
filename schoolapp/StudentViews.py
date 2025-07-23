import datetime
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.files.storage import FileSystemStorage
from schoolapp.models import *
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.shortcuts import get_object_or_404


def get_student_sessions(student):
    result_sessions = StudentResults.objects.filter(student_id=student).values_list('session_id', flat=True)
    attendance_sessions = AttendanceReport.objects.filter(student_id=student).values_list('attendance_id__session_year_id', flat=True)
    session_ids = set(result_sessions) | set(attendance_sessions)
    return SessionYearModel.objects.filter(id__in=session_ids).order_by("-session_start_year")


@login_required
def student_home(request):
    student = request.user.students
    session_id = request.session.get('active_student_session_id', student.session_year_id.id)
    session = SessionYearModel.objects.get(id=session_id)
    request.session['active_student_session_id'] = session_id

    student_sessions = get_student_sessions(student)

    attendance_reports = AttendanceReport.objects.filter(
        student_id=student, attendance_id__session_year_id=session
    )
    total = attendance_reports.count()
    present = attendance_reports.filter(status=True).count()
    absent = attendance_reports.filter(status=False).count()

    subjects = Subjects.objects.filter(
        department_id=student.department_id, class_id=student.class_id
    )
    subject_count = subjects.count()

    sub_names, data_present, data_absent = [], [], []
    for sub in subjects:
        att = Attendence.objects.filter(subject_id=sub, session_year_id=session)
        sub_names.append(sub.subject_name)
        data_present.append(
            AttendanceReport.objects.filter(attendance_id__in=att, student_id=student, status=True).count()
        )
        data_absent.append(
            AttendanceReport.objects.filter(attendance_id__in=att, student_id=student, status=False).count()
        )

    return render(request, "student_templates/student_home.html", {
        "students": student,
        "session_obj": session,
        "student_sessions": student_sessions,
        "subjects_data": subjects,
        "subjects": subject_count,
        "data_name": sub_names,
        "data1": data_present,
        "data2": data_absent,
        "total_attendance": total,
        "attendance_present": present,
        "attendance_absent": absent,
    })


######## Switch Session Year ########
@require_POST
@login_required
def student_switch_session(request):
    session_id = request.POST.get("session_year_id")
    student = request.user.students

    # Validate if the selected session belongs to the student
    valid_ids = set(StudentResults.objects.filter(student_id=student).values_list('session_id', flat=True))
    valid_ids |= set(AttendanceReport.objects.filter(student_id=student).values_list('attendance_id__session_year_id', flat=True))

    if session_id and int(session_id) in valid_ids:
        request.session['active_student_session_id'] = int(session_id)
    return HttpResponseRedirect(request.META.get('HTTP_REFERER') or reverse('student_home'))

@login_required
def student_profile(request):
    user = CustomUser.objects.get(id=request.user.id)
    students = Students.objects.get(admin=user)
    return render(request, "student_templates/student_profile.html", {
        "user": user,
        "students": students
    })


@login_required
def student_profile_save(request):
    if request.method != "POST":
        return HttpResponseRedirect(reverse("student_profile"))
    else:
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        address = request.POST.get("address")
        password = request.POST.get("password")

        if request.FILES.get('profile_pic', False):
            profile_pic = request.FILES['profile_pic']
            fs = FileSystemStorage()
            filename = fs.save(profile_pic.name, profile_pic)
            profile_pic_url = fs.url(filename)
        else:
            profile_pic_url = None

        try:
            user = CustomUser.objects.get(id=request.user.id)
            user.first_name = first_name
            user.last_name = last_name
            if password:
                user.set_password(password)
            user.save()

            students = Students.objects.get(admin=user.id)
            students.residential_address = address
            if profile_pic_url:
                students.profile_pic = profile_pic_url
            students.save()

            messages.success(request, "Profile Saved!")
            return HttpResponseRedirect(reverse("student_profile"))
        except:
            messages.error(request, "Profile Failed to Save!")
            return HttpResponseRedirect(reverse("student_profile"))


########## Assignment Views ##########
@login_required
def student_assignments(request):
    student = request.user.students
    session_id = request.session.get('active_student_session_id', student.session_year_id.id)
    session = SessionYearModel.objects.get(id=session_id)
    student_sessions = get_student_sessions(student)

    assignments = Assignment.objects.filter(
        class_id=student.class_id,
        department_id=student.department_id,
        session_year_id=session
    ).order_by("-created_at")

    submissions = AssignmentSubmission.objects.filter(student=student)
    submitted_assignment_ids = submissions.values_list("assignment__id", flat=True)

    return render(request, "student_templates/assignment_list.html", {
        "assignments": assignments,
        "submitted_assignment_ids": submitted_assignment_ids,
        "student_sessions": student_sessions,
        "session_obj": session,
    })


@login_required
def submit_assignment(request, assignment_id):
    student = Students.objects.get(admin=request.user.id)
    assignment = Assignment.objects.get(id=assignment_id)

    if request.method == "POST":
        file = request.FILES.get("file")
        if not file:
            messages.error(request, "Please select a file to upload.")
            return redirect("student_assignments")

        AssignmentSubmission.objects.create(
            assignment=assignment,
            student=student,
            submitted_file=file  
        )
        messages.success(request, "Assignment submitted successfully.")
        return redirect("student_assignments")

    return render(request, "student_templates/submit_assignment.html", {
        "assignment": assignment
    })

@login_required
def assignment_detail(request, assignment_id):
    assignment = get_object_or_404(Assignment, id=assignment_id)
    student = Students.objects.get(admin=request.user)

    # Check if already submitted
    submission = AssignmentSubmission.objects.filter(assignment=assignment, student=student).first()

    if request.method == "POST" and not submission:
        submitted_file = request.FILES.get("submitted_file")
        if not submitted_file:
            messages.error(request, "Please select a file to upload.")
        else:
            try:
                AssignmentSubmission.objects.create(
                    assignment=assignment,
                    student=student,
                    submitted_file=submitted_file
                )
                messages.success(request, "Assignment submitted successfully.")
                return redirect("student_assignment_detail", assignment_id=assignment.id)
            except Exception as e:
                messages.error(request, f"Error: {e}")

    return render(request, "student_templates/assignment_detail.html", {
        "assignment": assignment,
        "submission": submission
    })

@login_required
def student_submission_feedback(request, submission_id):
    student = request.user.students
    submission = get_object_or_404(
        AssignmentSubmission,
        id=submission_id,
        student=student,
        graded=True  # ensure only graded ones can be viewed
    )
    
    return render(request, "student_templates/submission_feedback.html", {
        "submission": submission
    })

@login_required
def student_submissions(request):
    student = request.user.students
    submissions = AssignmentSubmission.objects.filter(student=student).select_related('assignment', 'assignment__staff')

    return render(request, "student_templates/student_submission_list.html", {
        "submissions": submissions
    })



@login_required
def student_view_attendance(request):
    student = request.user.students
    session_id = request.session.get('active_student_session_id', student.session_year_id.id)
    session = SessionYearModel.objects.get(id=session_id)
    student_sessions = get_student_sessions(student)

    subjects = Subjects.objects.filter(
        department_id=student.department_id,
        class_id=student.class_id
    )

    return render(request, "student_templates/student_view_attendance.html", {
        "subjects": subjects,
        "students": student,
        "session_obj": session,
        "student_sessions": student_sessions,
    })




@login_required
def student_view_attendance_post(request):
    subject_id = request.POST.get("subject")
    start_date = request.POST.get("start_date")
    end_date = request.POST.get("end_date")

    start_data_parse = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end_data_parse = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

    subject_obj = Subjects.objects.get(id=subject_id)
    student = Students.objects.get(admin=request.user.id)
    session = student.session_year_id

    attendance = Attendence.objects.filter(
        attendance_date__range=(start_data_parse, end_data_parse),
        subject_id=subject_obj,
        session_year_id=session
    )
    attendance_reports = AttendanceReport.objects.filter(
        attendance_id__in=attendance,
        student_id=student
    )

    return render(request, "student_templates/student_attendance_data.html", {
        "attendance_reports": attendance_reports,
        "students": student
    })


@login_required
def student_apply_leave(request):
    students = Students.objects.get(admin=request.user)
    leave_data = LeaveReportStudent.objects.filter(student_id=students)

    return render(request, "student_templates/student_apply_leave.html", {
        "leave_data": leave_data,
        "students": students
    })


@login_required
def student_apply_leave_save(request):
    if request.method != "POST":
        return HttpResponseRedirect(reverse("student_apply_leave"))
    else:
        leave_date = request.POST.get("leave_date")
        leave_msg = request.POST.get("leave_msg")
        student_obj = Students.objects.get(admin=request.user.id)

        try:
            leave_report = LeaveReportStudent(
                student_id=student_obj,
                leave_date=leave_date,
                leave_message=leave_msg,
                leave_status=0
            )
            leave_report.save()
            messages.success(request, "Successfully Applied for Leave")
        except:
            messages.error(request, "Failed to Apply for Leave")
        return HttpResponseRedirect(reverse("student_apply_leave"))


@login_required
def student_feedback(request):
    students = Students.objects.get(admin=request.user)
    feedback_data = FeedBackStudent.objects.filter(student_id=students)

    return render(request, "student_templates/student_feedback.html", {
        "feedback_data": feedback_data,
        "students": students
    })


@login_required
def student_feedback_save(request):
    if request.method != "POST":
        return HttpResponseRedirect(reverse("student_feedback"))
    else:
        feedback_msg = request.POST.get("feedback_msg")
        student_obj = Students.objects.get(admin=request.user.id)

        try:
            feedback = FeedBackStudent(
                student_id=student_obj,
                feedback=feedback_msg,
                feedback_reply=""
            )
            feedback.save()
            messages.success(request, "Successfully Sent Feedback")
        except:
            messages.error(request, "Failed to Send Feedback")
        return HttpResponseRedirect(reverse("student_feedback"))


@login_required
def student_view_result(request):
    student = request.user.students
    session_id = request.session.get('active_student_session_id', student.session_year_id.id)
    session = SessionYearModel.objects.get(id=session_id)
    student_sessions = get_student_sessions(student)

    results = StudentResults.objects.filter(student_id=student, session_id=session)
    attendance_reports = AttendanceReport.objects.filter(
        student_id=student, attendance_id__session_year_id=session
    )

    total = attendance_reports.count()
    present = attendance_reports.filter(status=True).count()
    absent = attendance_reports.filter(status=False).count()

    total_scored = 0
    total_possible = 0
    for r in results:
        if r.student_exam_result and r.student_assignment_result:
            total_scored += r.student_exam_result + r.student_assignment_result
            total_possible += 100

    percentage = (total_scored / total_possible) * 100 if total_possible else 0

    return render(request, "student_templates/student_result.html", {
        "studentresult": results,
        "students": student,
        "session_obj": session,
        "total_attendance": total,
        "attendance_present": present,
        "attendance_absent": absent,
        "overall_percentage": round(percentage, 2),
        "total_scored": total_scored,
        "total_possible": total_possible,
        "student_sessions": student_sessions,
    })

######## Timetable Views ########
@login_required
def student_timetable(request):
    student = request.user.students
    session_id = request.session.get("active_student_session_id", student.session_year_id.id)
    session = SessionYearModel.objects.get(id=session_id)

    timetable_entries = TimeTable.objects.filter(
        class_id=student.class_id,
        department_id=student.department_id,
        session_year=session
    ).select_related("subject", "teacher").order_by("day", "start_time")

    # Organize by day for template
    from collections import defaultdict
    week = defaultdict(list)
    for entry in timetable_entries:
        week[entry.get_day_display()].append(entry)

    return render(request, "student_templates/timetable_view.html", {
        "week": dict(week),
        "student": student,
        "session_obj": session,
    })














@login_required
def student_make_payment(request):
    user= CustomUser.objects.get(id=request.user.id)
    students= Students.objects.get(admin=user)
    return render(request,"student_templates/make_payment.html",{"students":students})
