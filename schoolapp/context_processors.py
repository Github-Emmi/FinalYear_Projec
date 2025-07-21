# schoolapp/context_processors.py

from schoolapp.models import Students, StudentResults, AttendanceReport, SessionYearModel

def student_sessions_processor(request):
    if request.user.is_authenticated and hasattr(request.user, 'students'):
        student = request.user.students
        session_ids_from_results = set(
            StudentResults.objects.filter(student_id=student).values_list('session_id', flat=True)
        )
        session_ids_from_attendance = set(
            AttendanceReport.objects.filter(student_id=student).values_list('attendance_id__session_year_id', flat=True)
        )
        combined_session_ids = session_ids_from_results.union(session_ids_from_attendance)
        sessions = SessionYearModel.objects.filter(id__in=combined_session_ids)
        return {'student_sessions': sessions}
    return {}

def notifications(request):
    if request.user.is_authenticated:
        qs = request.user.notification_student.filter(read=False)
        return {
            'unread_notification_count': qs.count(),
            'recent_notifications': request.user.notification_student.all()[:5],  # latest 5
        }
    return {}