ProgrammingError at /student-quizzes/
(1146, "Table 'emmidev$febmexdb.schoolapp_quiz' doesn't exist")
Request Method:	GET
Request URL:	https://www.febmexinternationalschools.com/student-quizzes/
Django Version:	4.2.23
Exception Type:	ProgrammingError
Exception Value:	
(1146, "Table 'emmidev$febmexdb.schoolapp_quiz' doesn't exist")
Exception Location:	/home/emmidev/.virtualenvs/feb_venv/lib/python3.10/site-packages/pymysql/err.py, line 150, in raise_mysql_exception
Raised during:	schoolapp.StudentViews.student_quiz_list

/home/emmidev/FinalYear_Projec/schoolapp/templates/student_templates/quiz_list.html, error at line 13

1146
3	{% block title %}Quizzes{% endblock %}
4	
5	{% block main_content %}
6	<div class="container mt-3">
7	  <h4>📚 Available Quizzes</h4>
8	  <table class="table table-bordered">
9	    <thead>
10	      <tr><th>Title</th><th>Subject</th><th>Due</th><th>Status</th><th>Action</th></tr>
11	    </thead>
12	    <tbody>
13	    {% for quiz in quizzes %}
14	      <tr>
15	        <td>{{ quiz.title }}</td>
16	        <td>{{ quiz.subject.subject_name }}</td>
17	        <td>{{ quiz.deadline|date:"Y-m-d H:i" }}</td>
18	        <td>
19	          {% if quiz.id in attempted_ids %}
20	            <span class="badge badge-success">Attempted</span>
21	          {% else %}
22	            <span class="badge badge-warning">Pending</span>
23	          {% endif %}

{% extends 'student_templates/base.html' %}
{% load static %}
{% block title %}Quizzes{% endblock %}

{% block main_content %}
<div class="container mt-3">
  <h4>📚 Available Quizzes</h4>
  <table class="table table-bordered">
    <thead>
      <tr><th>Title</th><th>Subject</th><th>Due</th><th>Status</th><th>Action</th></tr>
    </thead>
    <tbody>
    {% for quiz in quizzes %}
      <tr>
        <td>{{ quiz.title }}</td>
        <td>{{ quiz.subject.subject_name }}</td>
        <td>{{ quiz.deadline|date:"Y-m-d H:i" }}</td>
        <td>
          {% if quiz.id in attempted_ids %}
            <span class="badge badge-success">Attempted</span>
          {% else %}
            <span class="badge badge-warning">Pending</span>
          {% endif %}
        </td>
        <td>
          {% if quiz.id not in attempted_ids %}
            <a href="{% url 'student_quiz_start' quiz.id %}" class="btn btn-sm btn-primary">Attempt</a>
          {% else %}
            <span class="text-muted">Completed</span>
          {% endif %}
        </td>
      </tr>
    {% empty %}
      <tr><td colspan="5" class="text-center text-muted">No available quizzes</td></tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
