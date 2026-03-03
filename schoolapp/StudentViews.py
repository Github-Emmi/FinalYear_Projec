import datetime
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.files.storage import FileSystemStorage
from schoolapp.models import *
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.timezone import localtime
from django.shortcuts import get_object_or_404
from notifications.signals import notify
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime



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

    qs = Assignment.objects.filter(
        class_id=student.class_id,
        department_id=student.department_id,
        session_year_id=session
    ).order_by("-created_at")

    # Live search
    query = request.GET.get("q", "")
    if query:
        qs = qs.filter(title__icontains=query) | qs.filter(description__icontains=query)

    paginator = Paginator(qs, 10)
    page_no = request.GET.get("page")
    assignments = paginator.get_page(page_no)

    submitted_assignment_ids = AssignmentSubmission.objects.filter(
        student=student
    ).values_list("assignment_id", flat=True)

    context = {
        "assignments": assignments,
        "submitted_assignment_ids": submitted_assignment_ids,
        "student_sessions": student_sessions,
        "session_obj": session,
        "query": query,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string("student_templates/_assignments_table.html", context, request=request)
        return JsonResponse({"html": html})

    return render(request, "student_templates/assignment_list.html", context)


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
                # ✅ Save submission and keep a reference
                submission = AssignmentSubmission.objects.create(
                    assignment=assignment,
                    student=student,
                    submitted_file=submitted_file
                )

                # ✅ Notify staff with correct target
                notify.send(
                    sender=request.user,
                    recipient=assignment.staff.admin,
                    verb="New assignment submission received",
                    description=f"{student.admin.get_full_name()} submitted for '{assignment.title}'",
                    target=submission
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
    student = Students.objects.select_related("admin").get(admin=request.user)
    feedback_messages = FeedBackStudent.objects.filter(
        student_id=student
    ).order_by("created_at")

    # Fallback avatar paths if you don't store profile pics
    admin_avatar_url = "/static/assets/images/avatar3.png"
    student_avatar_url = student.profile_pic

    return render(
        request,
        "student_templates/student_feedback_chat.html",
        {
            "feedback_messages": feedback_messages,
            "student": student,
            "admin_avatar_url": admin_avatar_url,
            "student_avatar_url": student_avatar_url
        },
    )

@login_required
def student_feedback_save(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)

    feedback_msg = (request.POST.get("feedback_msg") or "").strip()
    if not feedback_msg:
        return JsonResponse({"status": "error", "message": "Message cannot be empty"}, status=400)

    student_obj = Students.objects.select_related("admin").get(admin=request.user)

    fb = FeedBackStudent.objects.create(
        student_id=student_obj,
        feedback=feedback_msg,
        feedback_reply="",
    )

    # ✅ notify all admin
    admin_users = User.objects.filter(is_superuser=True, is_active=True)
    if admin_users.exists():
        notify.send(
            sender=request.user,
            recipient=admin_users,  # can be a queryset/list
            verb="New feedback received",
            description=f"{student_obj.admin.get_full_name() or student_obj.admin.username} sent a new message",
            target=student_obj,  # 🔗 this is why get_absolute_url() on Students matters
        )

    return JsonResponse({
        "status": "success",
        "message": fb.feedback,
        "time": localtime(fb.created_at).strftime("%b %d, %I:%M %p"),
    })

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
def student_schedule_json(request):
    student = request.user.students
    session_id = request.session.get('active_student_session_id', student.session_year_id.id)
    session = SessionYearModel.objects.get(id=session_id)

    # Monday = 0, Sunday = 6 (we want Mon–Fri only)
    valid_days = ['MON', 'TUE', 'WED', 'THU', 'FRI']

    timetable_entries = TimeTable.objects.filter(
        class_id=student.class_id,
        department_id=student.department_id,
        session_year=session,
        day__in=valid_days
    )

    events = []

    day_map = {
        'NONE': 0,  # If no day is set, default to Monday
        'MON': 1,
        'TUE': 2,
        'WED': 3,
        'THU': 4,
        'FRI': 5,
        'SAT': 6,
        'SUN': 7,
    }

    # We'll render entries as recurring weekly events (every week, same day/time)
    for entry in timetable_entries:
        events.append({
            "title": f"{entry.subject.subject_name} ({entry.classroom})",
            "daysOfWeek": [day_map[entry.day]],  # e.g. [0] = Monday
            "startTime": str(entry.start_time),
            "endTime": str(entry.end_time),
            "color": "#007bff",  # Optional: subject color
        })

    return JsonResponse(events, safe=False)

######## Quiz Views ########

from django.utils import timezone

@login_required
def student_quiz_list(request):
    student = get_object_or_404(Students, admin=request.user)
    quizzes = Quiz.objects.filter(
        class_id=student.class_id,
        department_id=student.department_id,
        session_year=student.session_year_id,
        status="PUBLISHED",
        deadline__gte=timezone.now()   # make sure deadline not passed
    ).select_related("subject", "class_id", "department_id", "session_year").order_by("-created_at")

    print("DEBUG QUIZZES: ", quizzes)  # 👈 See what is passed

    attempted_ids = []  # until QuizAttempt model is created
    return render(request, "student_templates/quiz_list.html", {
        "quizzes": quizzes,
        "attempted_ids": attempted_ids,
    })

# 2. Take Quiz (with timer)
def take_quiz(request, quiz_id):
    student = get_object_or_404(Students, admin=request.user)
    quiz = get_object_or_404(Quiz, id=quiz_id)

    # Check deadline
    if timezone.now() > quiz.deadline:
        return render(request, "student_templates/quiz_closed.html", {"quiz": quiz})

    # Get or create submission
    submission, created = StudentQuizSubmission.objects.get_or_create(
        student=student, quiz=quiz
    )

    if submission.is_graded:
        # Already submitted and graded
        return redirect("view_result", submission.id)

    if request.method == "POST":
        # Save answers
        for question in quiz.questions.all():
            answer_value = request.POST.get(str(question.id))
            if not answer_value:
                continue  # skip unanswered

            student_answer, created = StudentAnswer.objects.get_or_create(
                submission=submission, question=question
            )

            if question.question_type == "MCQ":
                student_answer.selected_option = answer_value
                student_answer.is_correct = (answer_value == question.correct_answer)
            else:  # Open-ended
                student_answer.text_answer = answer_value
                # leave grading for staff/AI
            student_answer.save()

        # Auto-grade MCQs immediately
        submission.grade_submission(use_ai=False)
        return redirect("view_result", submission.id)

    # Calculate remaining time (in seconds)
    elapsed = (timezone.now() - submission.submitted_at).total_seconds()
    remaining_time = (quiz.duration_minutes * 60) - elapsed
    if remaining_time <= 0:
        submission.grade_submission(use_ai=False)
        return redirect("view_result", submission.id)

    return render(request, "student_templates/take_quiz.html", {
        "quiz": quiz,
        "submission": submission,
        "remaining_time": int(remaining_time)
    })


# 3. View results
def view_result(request, submission_id):
    submission = get_object_or_404(StudentQuizSubmission, id=submission_id)

    # If staff chooses to delay results
    if not submission.is_graded:
        return render(request, "student_templates/result_pending.html", {"quiz": submission.quiz})

    return render(request, "student_templates/view_result.html", {"submission": submission})


# 4. Auto-submit via AJAX
@csrf_exempt
def auto_submit_quiz(request, quiz_id):
    if request.method == "POST":
        student = get_object_or_404(Students, admin=request.user)
        quiz = get_object_or_404(Quiz, id=quiz_id)
        submission = get_object_or_404(StudentQuizSubmission, student=student, quiz=quiz)

        submission.grade_submission(use_ai=False)
        return JsonResponse({"status": "submitted"})

    return JsonResponse({"error": "Invalid request"}, status=400)

@login_required
def student_make_payment(request):
    user= CustomUser.objects.get(id=request.user.id)
    students= Students.objects.get(admin=user)
    return render(request,"student_templates/make_payment.html",{"students":students})
