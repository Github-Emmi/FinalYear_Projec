# schoolapp/context_processors.py
from schoolapp.models import StudentResults, AttendanceReport, SessionYearModel

def student_sessions_context(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'students'):
        return {}

    student = request.user.students

    result_sessions = StudentResults.objects.filter(student_id=student).values_list('session_id', flat=True)
    attendance_sessions = AttendanceReport.objects.filter(student_id=student).values_list('attendance_id__session_year_id', flat=True)
    session_ids = set(result_sessions) | set(attendance_sessions)

    student_sessions = SessionYearModel.objects.filter(id__in=session_ids).order_by('-session_start_year')
    
    return {'student_sessions': student_sessions}
