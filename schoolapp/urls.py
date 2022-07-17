from django.urls import path, re_path

from schoolapp import views, AdminViews

urlpatterns = [
path('', views.user_login, name='login'),
path('DoLogin', views.DoLogin, name='dologin'),
path('logout', views.user_logout, name='logout'),
   ######## Admin Views ###############
path('admin-home', AdminViews.admin_home, name='admin_home'),
path('add-staff', AdminViews.add_staff, name='add_staff'),
path('save_staff', AdminViews.save_staff, name='save_staff'),
path('add-department', AdminViews.add_department, name='add_department'),
path('save-department', AdminViews.save_department, name='save_department'),
path('add-student', AdminViews.add_student, name='add_student'),
path('save_student', AdminViews.save_student, name='save_student'),

]