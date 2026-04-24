from app.tasks import celery_app

def test_task_names_registered():
    tasks = celery_app.celery_app.tasks
    assert "app.tasks.grading_tasks.grade_submission_task" in tasks
    assert "app.tasks.grading_tasks.grade_attempt_task" in tasks
    assert "app.tasks.email_tasks.send_email_task" in tasks
    assert "app.tasks.notification_tasks.push_ws_notification_task" in tasks

def test_send_email_task_signature():
    from app.tasks.email_tasks import send_email_task
    send_email_task.signature(("to@example.com", "Subject", "Body"))

def test_grade_submission_task_signature():
    from app.tasks.grading_tasks import grade_submission_task
    grade_submission_task.signature(("submission_id",))

def test_grade_attempt_task_signature():
    from app.tasks.grading_tasks import grade_attempt_task
    grade_attempt_task.signature(("attempt_id",))
