from django.urls import path

from schoolapp import views, AdminViews, StaffViews, StudentViews

urlpatterns = [
path('', views.index, name='index'),
path('about.html', views.about, name='about'),
path('classes.html', views.classes, name='classes'),
path('academics.html', views.academics, name='academics'),
path('gallery.html', views.gallery, name='gallery'),
path('contact.html', views.contact, name='contact'),
path('sent.html', views.sent, name='sent'),
path('login', views.user_login, name='login'),
path('DoLogin', views.DoLogin, name='do_login'),
path('logout', views.user_logout, name='logout'),
   ####################################
           # Admin Views #
   ####################################
path('admin-home', AdminViews.admin_home, name='admin_home'),
path('admin-profile', AdminViews.admin_profile, name='admin_profile'),
path('admin-profile-save', AdminViews.admin_profile_save, name="admin_profile_save"),
path('add-staff', AdminViews.add_staff, name='add_staff'),
path('save_staff', AdminViews.save_staff, name='save_staff'),
path('add-class', AdminViews.add_class, name='add_class'),
path('save-class', AdminViews.save_class, name='save_class'),
path('add-department', AdminViews.add_department, name='add_department'),
path('save-department', AdminViews.save_department, name='save_department'),
path('add-student', AdminViews.add_student, name='add_student'),
path('save_student', AdminViews.save_student, name='save_student'),
path('add-subject', AdminViews.add_subject, name='add_subject'),
path('save-subject', AdminViews.save_subject, name='save_subject'),
path('manage-staff', AdminViews.manage_staff, name='manage_staff'),
path('manage-student', AdminViews.manage_student, name='manage_student'),
path('manage-class', AdminViews.manage_class, name='manage_class'),
path('manage-department', AdminViews.manage_department, name='manage_department'),
path('manage-subject', AdminViews.manage_subject, name='manage_subject'),
path('manage-session', AdminViews.manage_session, name='manage_session'),
path('manage-session-save', AdminViews.manage_session_save, name='manage_session_save'),
path('edit-student/<str:student_id>', AdminViews.edit_student, name='edit_student'),
path('save-edit-student', AdminViews.save_edit_student, name='save_edit_student'),
#########       path ends for edit and save Student      ###########
path('edit-staff/<str:staff_id>', AdminViews.edit_staff, name='edit_staff'),
path('save-edit-staff', AdminViews.save_edit_staff, name='save_edit_staff'),
#########       path ends for edit and save Staff         ###########
path('edit-subject/<str:subject_id>', AdminViews.edit_subject, name='edit_subject'),
path('save-edit-subject', AdminViews.save_edit_subject, name='save_edit_subject'),
#########       path ends for edit and save Subject       ###########
path('edit-department/<str:department_id>', AdminViews.edit_department, name='edit_department'),
path('save-edit-department', AdminViews.save_edit_department, name='save_edit_department'),
#########       path ends for edit and save Department     ###########
path('edit-class/<str:class_id>', AdminViews.edit_class, name='edit_class'),
path('save-edit-class', AdminViews.save_edit_class, name='save_edit_class'),
path('check-email-exist', AdminViews.check_email_exist,name="check_email_exist"),
path('check-username-exist', AdminViews.check_username_exist,name="check_username_exist"),
path('student-feedback-message', AdminViews.student_feedback_message,name="student_feedback_message"),
path('student-feedback-message-replied', AdminViews.student_feedback_message_replied,name="student_feedback_message_replied"),
path('staff-feedback-message', AdminViews.staff_feedback_message,name="staff_feedback_message"),
path('staff-feedback-message-replied', AdminViews.staff_feedback_message_replied,name="staff_feedback_message_replied"),
path('student-leave-view', AdminViews.student_leave_view,name="student_leave_view"),
path('staff-leave-view', AdminViews.staff_leave_view,name="staff_leave_view"),
path('student-approve-leave/<str:leave_id>', AdminViews.student_approve_leave,name="student_approve_leave"),
path('student-disapprove-leave/<str:leave_id>', AdminViews.student_disapprove_leave,name="student_disapprove_leave"),
path('staff-disapprove-leave/<str:leave_id>', AdminViews.staff_disapprove_leave,name="staff_disapprove_leave"),
path('staff-approve-leave/<str:leave_id>', AdminViews.staff_approve_leave,name="staff_approve_leave"),
path('admin-view-attendance', AdminViews.admin_view_attendance,name="admin_view_attendance"),
path('admin-view-results', AdminViews.admin_view_results,name="admin_view_results"),
path('admin-get-attendance-dates', AdminViews.admin_get_attendance_dates,name="admin_get_attendance_dates"),
path('admin-get-attendance-student', AdminViews.admin_get_attendance_student,name="admin_get_attendance_student"),
path('admin-get-student-result', AdminViews.admin_get_student_result,name="admin_get_student_result"),

   ####################################
           # Staff Views #
   ####################################
path('staff-home', StaffViews.staff_home, name="staff_home"),
path('staff-profile', StaffViews.staff_profile, name="staff_profile"),
path('staff-rofile-save', StaffViews.staff_profile_save, name="staff_profile_save"),
path('staff-take-attendance', StaffViews.staff_take_attendance, name="take_attendance"),
path('staff-update-attendance', StaffViews.staff_update_attendance, name="staff_update_attendance"),
path('get-students', StaffViews.get_students, name="get_students"),
path('get-attendance-dates', StaffViews.get_attendance_dates, name ="get_attendance_dates"),
path('get-attendance-student', StaffViews.get_attendance_student, name="get_attendance_student"),
path('save-attendance-data', StaffViews.save_attendance_data, name="save_attendance_data"),
path('save-updateattendance-data', StaffViews.save_updateattendance_data, name="save_updateattendance_data"),
path('staff-apply-leave', StaffViews.staff_apply_leave, name="staff_apply_leave"),
path('staff-apply-leave-save', StaffViews.staff_apply_leave_save, name="staff_apply_leave_save"),
path('staff-feedback', StaffViews.staff_feedback, name="staff_feedback"),
path('staff-feedback-save', StaffViews.staff_feedback_save, name="staff_feedback_save"),
path('staff-add-result', StaffViews.staff_add_result, name="staff_add_result"),
path('save-student-result', StaffViews.save_student_result, name="save_student_result"),

   ####################################
           # Student Views #
   ####################################
path('student-home', StudentViews.student_home, name="student_home"), 
path('student-profile', StudentViews.student_profile, name="student_profile"),
path('staff-profile-save', StudentViews.student_profile_save, name="student_profile_save"),
path('student-view-attendance', StudentViews.student_view_attendance, name="student_view_attendance"),
path('student-view-attendance-post', StudentViews.student_view_attendance_post, name="student_view_attendance_post"),
path('student-apply-leave', StudentViews.student_apply_leave, name="student_apply_leave"),
path('student-apply-leave-save', StudentViews.student_apply_leave_save, name="student_apply_leave_save"),
path('student-feedback', StudentViews.student_feedback, name="student_feedback"),
path('student-feedback-save', StudentViews.student_feedback_save, name="student_feedback_save"),
path('student-view-result',StudentViews.student_view_result,name="student_view_result"),
path('student-make-payment',StudentViews.student_make_payment,name="student_make_payment"),
]
  


