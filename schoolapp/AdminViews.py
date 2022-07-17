from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from schoolapp.models import CustomUser, Departments, Staffs


@login_required(login_url="/")
def admin_home(request):
    return render(request, 'admin_templates/main-content.html')

@login_required(login_url="/")
def add_staff(request):
    return render(request, 'admin_templates/add_staff.html')

@login_required(login_url="/")
def save_staff(request):
    if request.method != "POST":
        return HttpResponse("</h2>Method Not Allowed")
    else:
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        password = request.POST.get("password")
        email = request.POST.get("email")
        address = request.POST.get("address")
        try:
            user = CustomUser.objects.create_user(first_name=first_name,last_name=last_name,username=username,email=email,password=password,  user_type=2)
            user = Staffs(address=address)
            user.save()
            messages.success(request, 'Successfully Added Staff.')
            return HttpResponseRedirect('/add-staff')
        except:
            messages.error(request, 'failed To Add Staff')
            return HttpResponseRedirect('/add-staff')
        
@login_required(login_url="/")
def add_department(request):
    return render(request, 'admin_templates/add_department.html')  

@login_required(login_url="/")
def save_department(request):
    if request.method != "POST":
        return HttpResponse("<h2>Method Not Allowed")
    else:
        department = request.POST.get("department")
        try:
            department_model = Departments(department_name=department)
            department_model.save()
            messages.success(request, 'Successfully Added Department.')
            return HttpResponseRedirect('/add-department')
        except:
            messages.error(request, 'Failed To Add Department')
            return HttpResponseRedirect('/add-department')
                
        
@login_required(login_url="/")
def add_student(request):
    departments = Departments.objects.all()
    return render(request, 'admin_templates/add_student.html', {'departments':departments})   

@login_required(login_url="/")
def save_student(request):
    if request.method != "POST":
        return HttpResponse("</h2>Method Not Allowed")
    else:
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        password = request.POST.get("password")
        email = request.POST.get("email")
        department_id = request.POST.get("department")
        address = request.POST.get("address")
        session_start = request.POST.get("session_start")
        session_end = request.POST.get("session_end")
        sex = request.POST.get("sex")
        address = request.POST.get("address")
        try:
            user = CustomUser.objects.create_user(first_name=first_name,last_name=last_name,username=username,email=email,password=password,user_type=3)
            user.students.address=address
            department_obj = Departments.objects.get(id=department_id)
            user.students.department_id=department_obj
            user.students.session_start_year=session_start
            user.students.session_end_year=session_end
            user.students.gender=sex
            user.students.profile_pic=""
            
            user.save()
            messages.success(request, 'Successfully Added Staff.')
            return HttpResponseRedirect('/add-student')
        except:
            messages.error(request, 'failed To Add Staff')
            return HttpResponseRedirect('/add-student')     
        
        
        
        
         