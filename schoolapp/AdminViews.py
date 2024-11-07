from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
import json
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from schoolapp.forms import AddStudentForm, EditStudentForm
from schoolapp.models import CustomUser, Class, Departments, SessionYearModel, Staffs, StudentResults, Students, Subjects, \
    FeedBackStudent, FeedBackStaffs, LeaveReportStudent, LeaveReportStaff, Attendence, AttendanceReport
@login_required(login_url="/")
def admin_home(request):
    student_count1=Students.objects.all().count()
    staff_count=Staffs.objects.all().count()
    subject_count=Subjects.objects.all().count()
    department_count=Departments.objects.all().count()
    class_count=Class.objects.all().count()

    all_department=Departments.objects.all()
    department_name_list=[]
    subject_count_list=[]
    student_count_list_in_department=[]
    for department in all_department:
        subjects=Subjects.objects.filter(department_id=department.id).count()
        students=Students.objects.filter(department_id=department.id).count()
        department_name_list.append(department.department_name)
        subject_count_list.append(subjects)
        student_count_list_in_department.append(students)

    subjects_all=Subjects.objects.all()
    subject_list=[]
    student_count_list_in_subject=[]
    for subject in subjects_all:
        department=Departments.objects.get(id=subject.department_id.id)
        student_count=Students.objects.filter(department_id=department.id).count()
        subject_list.append(subject.subject_name)
        student_count_list_in_subject.append(student_count)

    staffs=Staffs.objects.all()
    attendance_present_list_staff=[]
    attendance_absent_list_staff=[]
    staff_name_list=[]
    for staff in staffs:
        subject_ids=Subjects.objects.filter(staff_id=staff.admin.id)
        attendance=Attendence.objects.filter(subject_id__in=subject_ids).count()
        leaves=LeaveReportStaff.objects.filter(staff_id=staff.id,leave_status=1).count()
        attendance_present_list_staff.append(attendance)
        attendance_absent_list_staff.append(leaves)
        staff_name_list.append(staff.admin.username)

    students_all=Students.objects.all()
    attendance_present_list_student=[]
    attendance_absent_list_student=[]
    student_name_list=[]
    for student in students_all:
        attendance=AttendanceReport.objects.filter(student_id=student.id,status=True).count()
        absent=AttendanceReport.objects.filter(student_id=student.id,status=False).count()
        leaves=LeaveReportStudent.objects.filter(student_id=student.id,leave_status=1).count()
        attendance_present_list_student.append(attendance)
        attendance_absent_list_student.append(leaves+absent)
        student_name_list.append(student.admin.username)
    
    return render(request, 'admin_templates/admin_home.html',{"student_count":student_count1,"class_count":class_count,"staff_count":staff_count,"subject_count":subject_count,"department_count":department_count,"department_name_list":department_name_list,"subject_count_list":subject_count_list,"student_count_list_in_department":student_count_list_in_department,"student_count_list_in_subject":student_count_list_in_subject,"subject_list":subject_list,"staff_name_list":staff_name_list,"attendance_present_list_staff":attendance_present_list_staff,"attendance_absent_list_staff":attendance_absent_list_staff,"student_name_list":student_name_list,"attendance_present_list_student":attendance_present_list_student,"attendance_absent_list_student":attendance_absent_list_student})

def admin_profile(request):
    user=CustomUser.objects.get(id=request.user.id)
    return render(request,"admin_templates/admin_profile.html",{"user":user})

def admin_profile_save(request):
    if request.method!="POST":
        return HttpResponseRedirect(reverse("admin_profile"))
    else:
        first_name=request.POST.get("first_name")
        last_name=request.POST.get("last_name")
        password=request.POST.get("password")
        try:
            customuser=CustomUser.objects.get(id=request.user.id)
            customuser.first_name=first_name
            customuser.last_name=last_name
            if password!=None and password!="":
                customuser.set_password(password)
            customuser.save()
            messages.success(request, "Successfully Updated Profile")
            return HttpResponseRedirect(reverse("admin_profile"))
        except:
            messages.error(request, "Failed to Update Profile")
            return HttpResponseRedirect(reverse("admin_profile"))
    

@login_required(login_url="/")
def add_staff(request):
    return render(request, 'admin_templates/add_staff.html')

@login_required(login_url="/")
def save_staff(request):
    if request.method!="POST":
        return HttpResponse("Method Not Allowed")
    else:
        first_name=request.POST.get("first_name")
        last_name=request.POST.get("last_name")
        username=request.POST.get("username")
        email=request.POST.get("email")
        password=request.POST.get("password")
        address=request.POST.get("address")
        try:
            user=CustomUser.objects.create_user(username=username,password=password,email=email,last_name=last_name,first_name=first_name,user_type=2)
            user.staffs.address=address
            user.save()
            messages.success(request,"Successfully Added Staff")
            return HttpResponseRedirect("/add-staff")
        except:
            messages.error(request,"Failed to Add Staff")
            return HttpResponseRedirect("/add-staff")
        
@login_required(login_url="/")
def add_class(request):
    return render(request, 'admin_templates/add_class.html')  

@login_required(login_url="/")
def save_class(request):
    if request.method!="POST":
        return HttpResponse("Method Not Allowed")
    else:
        classes = request.POST.get("class")
        try:
            class_model=Class(class_name=classes)
            class_model.save()
            messages.success(request,"Successfully Added Class")
            return HttpResponseRedirect(reverse('add_class'))
        except:
            messages.error(request,"Failed To Add Class")
            return HttpResponseRedirect(reverse('add_class'))
        
@login_required(login_url="/")
def add_department(request):
    return render(request, 'admin_templates/add_department.html')  

@login_required(login_url="/")
def save_department(request):
    if request.method!="POST":
        return HttpResponse("Method Not Allowed")
    else:
        departments = request.POST.get("department")
        try:
            department_model=Departments(department_name=departments)
            department_model.save()
            messages.success(request,"Successfully Added Department")
            return HttpResponseRedirect(reverse('add_department'))
        except:
            messages.error(request,"Failed To Add Class")
            return HttpResponseRedirect(reverse('add_department'))      
                
        ###############   Add Student Views #################
@login_required(login_url="/")
def add_student(request):
    form=AddStudentForm()
    return render(request, 'admin_templates/add_student.html', {'form':form})   

        ###############   Save Student Views #################
@login_required(login_url="/")
def save_student(request):
    if request.method!="POST":
        return HttpResponse("Method Not Allowed")
    else:
        form=AddStudentForm(request.POST,request.FILES)
        if form.is_valid():
            first_name=form.cleaned_data["first_name"]
            last_name=form.cleaned_data["last_name"]
            username=form.cleaned_data["username"]
            email=form.cleaned_data["email"]
            password=form.cleaned_data["password"]
            date_of_birth_id=form.cleaned_data["date_of_birth_id"]
            address=form.cleaned_data["address"]
            session_year_id=form.cleaned_data["session_year_id"]
            class_id=form.cleaned_data["class_id"]
            department_id=form.cleaned_data["department_id"]
            sex=form.cleaned_data["sex"]

            profile_pic=request.FILES['profile_pic']
            fs=FileSystemStorage()
            filename=fs.save(profile_pic.name,profile_pic)
            profile_pic_url=fs.url(filename)

            try:
                user=CustomUser.objects.create_user(username=username,password=password,email=email,last_name=last_name,first_name=first_name,user_type=3)
                user.students.address=address
                user.students.date_of_birth=date_of_birth_id
                class_obj=Class.objects.get(id=class_id)
                user.students.class_id=class_obj
                department_obj= Departments.objects.get(id=department_id)
                user.students.department_id=department_obj
                session_year = SessionYearModel.objects.get(id=session_year_id)
                user.students.session_year_id=session_year
                user.students.gender=sex
                user.students.profile_pic=profile_pic_url
                user.save()
                messages.success(request,"Successfully Added Student")
                return HttpResponseRedirect(reverse("add_student"))
            except:
                messages.error(request,"Failed to Add Student")
                return HttpResponseRedirect(reverse("add_student"))
        else:
            form=AddStudentForm(request.POST)
            return render(request, "admin_templates/add_student.html", {"form": form})
        
 ###############   Add Subject Views #################
@login_required(login_url="/")
def add_subject(request):
    classes = Class.objects.all()
    departments = Departments.objects.all()
    staffs = CustomUser.objects.filter(user_type=2)
    return render(request, 'admin_templates/add_subject.html', {'staffs':staffs,'classes':classes,'departments':departments})       
        
@login_required(login_url="/")
def save_subject(request):
    if request.method!="POST":
        return HttpResponse("<h2>Method Not Allowed")
    else:
        subject_name = request.POST.get("subject_name")
        department_modules = request.POST.get("department")
        class_modules = request.POST.get("class")
        staff_modules = request.POST.get("staff")
        departments = Departments.objects.get(id=department_modules)
        classes = Class.objects.get(id=class_modules)
        staff = CustomUser.objects.get(id=staff_modules)
        
        try:
            subject = Subjects(subject_name=subject_name,department_id=departments, class_id=classes, staff_id=staff) 
            subject.save()
            messages.success(request, 'Successfully Added Subject')
            return HttpResponseRedirect(reverse('add_subject'))
        except:
            messages.error(request, 'failed to Add Subject')
            return HttpResponseRedirect(reverse('add_subject'))
        
@login_required(login_url="/")
def manage_staff(request):
    staffs = Staffs.objects.all()
    return render(request, 'admin_templates/manage_staff.html', {'staffs':staffs,}) 

@login_required(login_url="/")
def manage_student(request):
    students = Students.objects.all()
    return render(request, 'admin_templates/manage_student.html', {'students':students,})
      
@login_required(login_url="/")
def manage_class(request):
    classes = Class.objects.all()
    return render(request, 'admin_templates/manage_class.html', {'classes':classes,})

@login_required(login_url="/")
def manage_department(request):
    departments = Departments.objects.all()
    return render(request, 'admin_templates/manage_department.html', {'departments':departments,})      

@login_required(login_url="/")
def manage_subject(request):
    subjects = Subjects.objects.all()
    return render(request, 'admin_templates/manage_subject.html', {'subjects':subjects,})

@login_required(login_url="/")
def manage_session(request):
    return render(request, "admin_templates/manage_session.html")

@login_required(login_url="/")
def manage_session_save(request):
    if request.method!="POST":
        return HttpResponseRedirect(reverse('manage_session'))
    else:
        session_name = request.POST.get("session_name")
        session_start_year = request.POST.get("session_start")
        session_end_year = request.POST.get("session_end")
        try:
            session_year = SessionYearModel(session_name=session_name,session_start_year=session_start_year,session_end_year=session_end_year)
            session_year.save() 
            messages.success(request, 'Successfully Added Session Year')
            return HttpResponseRedirect(reverse('manage_session'))
        except:
            messages.error(request, 'failed to Add Session')
            return HttpResponseRedirect(reverse('manage_session'))
                

@login_required(login_url="/")
def edit_staff(request,staff_id):
    staff=Staffs.objects.get(admin=staff_id)
    return render(request,"admin_templates/edit_staff.html",{"staff":staff,"id":staff_id})

        
@login_required(login_url="/")
def save_edit_staff(request):
    if request.method!="POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        staff_id=request.POST.get("staff_id")
        first_name=request.POST.get("first_name")
        last_name=request.POST.get("last_name")
        email=request.POST.get("email")
        username=request.POST.get("username")
        address=request.POST.get("address")
        try:
            user=CustomUser.objects.get(id=staff_id)
            user.first_name=first_name
            user.last_name=last_name
            user.email=email
            user.username=username
            user.save()
            ####    quaring Staff Objects
            staff_model=Staffs.objects.get(admin=staff_id)
            staff_model.address=address
            staff_model.save()
            messages.success(request,"Successfully Edited Staff")
            return HttpResponseRedirect(reverse("edit_staff",kwargs={"staff_id":staff_id}))
        except:
            messages.error(request,"Failed to Edit Staff")
            return HttpResponseRedirect(reverse("edit_staff",kwargs={"staff_id":staff_id}))
    
@login_required(login_url="/")
def edit_student(request,student_id):
    request.session['student_id']=student_id
    student=Students.objects.get(admin=student_id)
    form=EditStudentForm()
    form.fields['email'].initial=student.admin.email
    form.fields['first_name'].initial=student.admin.first_name
    form.fields['last_name'].initial=student.admin.last_name
    form.fields['username'].initial=student.admin.username
    form.fields['address'].initial=student.address
    form.fields['class_id'].initial=student.class_id.id
    form.fields['department_id'].initial=student.department_id.id
    form.fields['sex'].initial=student.gender
    form.fields['password'].initial=student.admin.password
    form.fields['date_of_birth_id'].initial=student.date_of_birth
    form.fields['session_year_id'].initial=student.session_year_id.id
    return render(request,"admin_templates/edit_student.html",{"form":form,"id":student_id,"username":student.admin.username})
            
@login_required(login_url="/")
def save_edit_student(request,):   
    if request.method!="POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        student_id=request.session.get("student_id")
        if student_id==None:
            return HttpResponseRedirect(reverse("manage_student"))
        form=EditStudentForm(request.POST,request.FILES)
        if form.is_valid():
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            email = form.cleaned_data["email"]
            address = form.cleaned_data["address"]
            date_of_birth_id = form.cleaned_data["date_of_birth_id"]
            session_year_id=form.cleaned_data["session_year_id"]
            class_id = form.cleaned_data["class_id"]
            department_id = form.cleaned_data["department_id"]
            sex = form.cleaned_data["sex"]

            if request.FILES.get('profile_pic',False):
                profile_pic=request.FILES['profile_pic']
                fs=FileSystemStorage()
                filename=fs.save(profile_pic.name,profile_pic)
                profile_pic_url=fs.url(filename)
            else:
                profile_pic_url=None

            try:
                user=CustomUser.objects.get(id=student_id)
                user.first_name=first_name
                user.last_name=last_name
                user.username=username
                user.email=email
                user.password=password
                if password!=None and password!="":
                    user.set_password(password)
                user.save()

                student=Students.objects.get(admin=student_id)
                student.address=address
                student.date_of_birth=date_of_birth_id
                ####### fetching session's Objects ######
                session_year= SessionYearModel.objects.get(id=session_year_id)
                student.session_year_id = session_year
                 ####### fetching class Objects ######
                classes=Class.objects.get(id=class_id)
                student.class_id=classes
                departments =Departments.objects.get(id=department_id)
                student.department_id=departments
                student.gender=sex
                if profile_pic_url!=None:
                    student.profile_pic=profile_pic_url
                student.save()
                del request.session['student_id']
                messages.success(request,"Successfully Edited Student")
                return HttpResponseRedirect(reverse("edit_student",kwargs={"student_id":student_id}))
            except:
                messages.error(request,"Failed to Edit Student")
                return HttpResponseRedirect(reverse("edit_student",kwargs={"student_id":student_id}))
        else:
            form=EditStudentForm(request.POST)
            student=Students.objects.get(admin=student_id)
            return render(request,"admin_templates/edit_student.html",{"form":form,"id":student_id,"username":student.admin.username})
        
@login_required(login_url="/")
def edit_subject(request,subject_id):
    subject=Subjects.objects.get(id=subject_id)
    classes=Class.objects.all()
    departments=Departments.objects.all()
    staffs=CustomUser.objects.filter(user_type=2)
    return render(request,"admin_templates/edit_subject.html",{"subject":subject,"staffs":staffs,"classes":classes,"id":subject_id,"departments":departments}) 

@login_required(login_url="/")
def save_edit_subject(request,):
    if request.method!="POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        subject_id=request.POST.get("subject_id")
        subject_name=request.POST.get("subject_name")
        staff_id=request.POST.get("staff")
        class_id=request.POST.get("class")
        department_id=request.POST.get("department")

        try:
            subject=Subjects.objects.get(id=subject_id)
            subject.subject_name=subject_name
            staff=CustomUser.objects.get(id=staff_id)
            subject.staff_id=staff
            classes= Class.objects.get(id=class_id)
            subject.class_id=classes
            departments= Departments.objects.get(id=department_id)
            subject.department_id=departments
            subject.save()

            messages.success(request,"Successfully Edited Subject")
            return HttpResponseRedirect(reverse("edit_subject",kwargs={"subject_id":subject_id}))
        except:
            messages.error(request,"Failed to Edit Subject")
            return HttpResponseRedirect(reverse("edit_subject",kwargs={"subject_id":subject_id}))
 

@login_required(login_url="/")
def edit_class(request,class_id):
    classes= Class.objects.get(id=class_id)
    return render(request, "admin_templates/edit_class.html", {'classes':classes,'id':class_id})

@login_required(login_url="/")
def save_edit_class(request):
    if request.method!="POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        class_id=request.POST.get("class_id")
        class_name=request.POST.get("class")

        try:
            classes= Class.objects.get(id=class_id)
            classes.class_name=class_name
            classes.save()
            messages.success(request,"Successfully Edited Class")
            return HttpResponseRedirect(reverse("edit_class",kwargs={"class_id":class_id}))
        except:
            messages.error(request,"Failed to Edit Class")
            return HttpResponseRedirect(reverse("edit_class",kwargs={"class_id":class_id}))
        
login_required(login_url="/")
def edit_department(request,department_id):
    departments= Departments.objects.get(id=department_id)
    return render(request, "admin_templates/edit_department.html", {'departments':departments,'id':department_id})

@login_required(login_url="/")
def save_edit_department(request):
    if request.method!="POST":
        return HttpResponse("<h2>Method Not Allowed</h2>")
    else:
        department_id=request.POST.get("department_id")
        department_name=request.POST.get("department")

        try:
            departments= Departments.objects.get(id=department_id)
            departments.department_name=department_name
            departments.save()
            messages.success(request,"Successfully Edited Class")
            return HttpResponseRedirect(reverse("edit_department",kwargs={"department_id":department_id}))
        except:
            messages.error(request,"Failed to Edit Class")
            return HttpResponseRedirect(reverse("edit_department",kwargs={"department_id":department_id}))
 
@csrf_exempt
def check_email_exist(request):
    email=request.POST.get("email")
    user_obj=CustomUser.objects.filter(email=email).exists()
    if user_obj:
        return HttpResponse(True)
    else:
        return HttpResponse(False)

@csrf_exempt
def check_username_exist(request):
    username=request.POST.get("username")
    user_obj=CustomUser.objects.filter(username=username).exists()
    if user_obj:
        return HttpResponse(True)
    else:
        return HttpResponse(False)

def staff_feedback_message(request):
    feedbacks=FeedBackStaffs.objects.all()
    return render(request,"admin_templates/staff_feedback.html",{"feedbacks":feedbacks})

def student_feedback_message(request):
    feedbacks=FeedBackStudent.objects.all()
    return render(request,"admin_templates/student_feedback.html",{"feedbacks":feedbacks})

@csrf_exempt
def student_feedback_message_replied(request):
    feedback_id=request.POST.get("id")
    feedback_message=request.POST.get("message")

    try:
        feedback=FeedBackStudent.objects.get(id=feedback_id)
        feedback.feedback_reply=feedback_message
        feedback.save()
        return HttpResponse("True")
    except:
        return HttpResponse("False")

@csrf_exempt
def staff_feedback_message_replied(request):
    feedback_id=request.POST.get("id")
    feedback_message=request.POST.get("message")

    try:
        feedback=FeedBackStaffs.objects.get(id=feedback_id)
        feedback.feedback_reply=feedback_message
        feedback.save()
        return HttpResponse("True")
    except:
        return HttpResponse("False")

def staff_leave_view(request):
    leaves=LeaveReportStaff.objects.all()
    return render(request,"admin_templates/staff_leave_view.html",{"leaves":leaves})

def student_leave_view(request):
    leaves=LeaveReportStudent.objects.all()
    return render(request,"admin_templates/student_leave_view.html",{"leaves":leaves})

def student_approve_leave(request,leave_id):
    leave=LeaveReportStudent.objects.get(id=leave_id)
    leave.leave_status=1
    leave.save()
    return HttpResponseRedirect(reverse("student_leave_view"))

def student_disapprove_leave(request,leave_id):
    leave=LeaveReportStudent.objects.get(id=leave_id)
    leave.leave_status=2
    leave.save()
    return HttpResponseRedirect(reverse("student_leave_view"))


def staff_approve_leave(request,leave_id):
    leave=LeaveReportStaff.objects.get(id=leave_id)
    leave.leave_status=1
    leave.save()
    return HttpResponseRedirect(reverse("staff_leave_view"))

def staff_disapprove_leave(request,leave_id):
    leave=LeaveReportStaff.objects.get(id=leave_id)
    leave.leave_status=2
    leave.save()
    return HttpResponseRedirect(reverse("staff_leave_view"))   

def admin_view_attendance(request):
    subjects=Subjects.objects.all()
    session_year_id=SessionYearModel.objects.all()
    return render(request,"admin_templates/admin_view_attendance.html",{"subjects":subjects,"session_year_id":session_year_id})

@csrf_exempt
def admin_get_attendance_dates(request):
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
def admin_get_attendance_student(request):
    attendance_date=request.POST.get("attendance_date")
    attendance=Attendence.objects.get(id=attendance_date)

    attendance_data=AttendanceReport.objects.filter(attendance_id=attendance)
    list_data=[]

    for student in attendance_data:
        data_small={"id":student.student_id.admin.id,"name":student.student_id.admin.first_name+" "+student.student_id.admin.last_name,"status":student.status}
        list_data.append(data_small)
    return JsonResponse(json.dumps(list_data),content_type="application/json",safe=False)     

def admin_view_results(request):
    students=Students.objects.all()
    session_year_id=SessionYearModel.objects.all()
    return render(request,"admin_templates/admin_view_results.html",{"students":students,"session_year_id":session_year_id})

@csrf_exempt
def admin_get_student_result(request):
    #### collecting selected student and session year
    student_id=request.POST.get("students")
    session_year=request.POST.get("session_year_id")
    ##### getting the values and passing it to their objects
    student_model=Students.objects.get(id=student_id)
    session_model=SessionYearModel.objects.get(id=session_year)
    studentresult=StudentResults.objects.filter(student_id=student_model,session_id=session_model)
    list_data=[]

    for student in studentresult:
        data_small={"subject":student.subject_id.subject_name,"exam":student.student_exam_result,"test":student.student_assignment_result,
                    "total":student.student_total_result,"score_remark":student.score_remark,"admin_comment":student.admincomment_id}
        list_data.append(data_small)
    return JsonResponse(json.dumps(list_data),content_type="application/json",safe=False)

