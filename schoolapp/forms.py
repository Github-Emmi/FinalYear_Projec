from django import forms
from django.forms import ChoiceField

from schoolapp.models import Departments, SessionYearModel, Subjects, Students, Class

class ChoiceNoValidation(ChoiceField):
    def validate(self, value):
        pass

class DateInput(forms.DateInput):
    input_type = "date"

class AddStudentForm(forms.Form):
    email=forms.EmailField(label="Email",max_length=50,widget=forms.EmailInput(attrs={"class":"form-control","autocomplete":"off"}))
    password=forms.CharField(label="Password",max_length=50,widget=forms.TextInput(attrs={"class":"form-control"}))
    first_name=forms.CharField(label="First Name",max_length=50,widget=forms.TextInput(attrs={"class":"form-control"}))
    last_name=forms.CharField(label="Last Name",max_length=50,widget=forms.TextInput(attrs={"class":"form-control"}))
    username=forms.CharField(label="Username",max_length=50,widget=forms.TextInput(attrs={"class":"form-control","autocomplete":"off"})) 
    date_of_birth_id=forms.CharField(label="Date Of Birth",max_length=50,widget=forms.TextInput(attrs={"class":"form-control"}))
    address=forms.CharField(label="Address",max_length=50,widget=forms.TextInput(attrs={"class":"form-control"}))
    
    department_list=[]
    try:
        deparments=Departments.objects.all()
        for deparment in deparments:
            small_deparment=(deparment.id,deparment.department_name)
            department_list.append(small_deparment)
    except:
        department_list=[]
        
    class_list=[]
    try:
        classes=Class.objects.all()
        for cl in classes:
            small_class=(cl.id,cl.class_name)
            class_list.append(small_class)
    except:
        class_list=[]    

    session_list = []
    try:
        sessions = SessionYearModel.objects.all()

        for ses in sessions:
            small_ses = (ses.id, str(ses.session_start_year)+"   TO  "+str(ses.session_end_year))
            session_list.append(small_ses)
    except:
        session_list=[]

    gender_choice=(
        ("Male","Male"),
        ("Female","Female")
    )

    department_id=forms.ChoiceField(label="Department",choices=department_list,widget=forms.Select(attrs={"class":"form-control"}))
    class_id=forms.ChoiceField(label="Class",choices=class_list,widget=forms.Select(attrs={"class":"form-control"}))
    sex=forms.ChoiceField(label="Sex",choices=gender_choice,widget=forms.Select(attrs={"class":"form-control"}))
    session_year_id=forms.ChoiceField(label="Session Year",choices=session_list,widget=forms.Select(attrs={"class":"form-control"}))
    profile_pic=forms.FileField(label="Profile Pic",max_length=50,widget=forms.FileInput(attrs={"class":"form-control"}))

class EditStudentForm(forms.Form):
    email=forms.EmailField(label="Email",max_length=50,widget=forms.EmailInput(attrs={"class":"form-control"}))
    password=forms.CharField(label="Password",max_length=50,widget=forms.TextInput(attrs={"class":"form-control"}))
    first_name=forms.CharField(label="First Name",max_length=50,widget=forms.TextInput(attrs={"class":"form-control"}))
    last_name=forms.CharField(label="Last Name",max_length=50,widget=forms.TextInput(attrs={"class":"form-control"}))
    username=forms.CharField(label="Username",max_length=50,widget=forms.TextInput(attrs={"class":"form-control"}))
    date_of_birth_id=forms.CharField(label="Date Of Birth",max_length=50,widget=forms.TextInput(attrs={"class":"form-control"}))
    address=forms.CharField(label="Address",max_length=50,widget=forms.TextInput(attrs={"class":"form-control"}))


    department_list=[]
    try:
        deparments=Departments.objects.all()
        for deparment in deparments:
            small_deparment=(deparment.id,deparment.department_name)
            department_list.append(small_deparment)
    except:
        department_list=[]
        
    class_list=[]
    try:
        classes=Class.objects.all()
        for cl in classes:
            small_class=(cl.id,cl.class_name)
            class_list.append(small_class)
    except:
        class_list=[]    

    session_list = []
    try:
        sessions = SessionYearModel.objects.all()

        for ses in sessions:
            small_ses = (ses.id, str(ses.session_start_year)+"   TO  "+str(ses.session_end_year))
            session_list.append(small_ses)
    except:
        session_list=[]

    gender_choice=(
        ("Male","Male"),
        ("Female","Female")
    )

    department_id=forms.ChoiceField(label="Department",choices=department_list,widget=forms.Select(attrs={"class":"form-control"}))
    sex=forms.ChoiceField(label="Sex",choices=gender_choice,widget=forms.Select(attrs={"class":"form-control"}))
    class_id=forms.ChoiceField(label="Class",choices=class_list,widget=forms.Select(attrs={"class":"form-control"}))
    session_year_id=forms.ChoiceField(label="Session Year",choices=session_list,widget=forms.Select(attrs={"class":"form-control"}))
    profile_pic=forms.FileField(label="Profile Pic",max_length=50,widget=forms.FileInput(attrs={"class":"form-control"}),required=False)

# class EditResultForm(forms.Form):
#     def __init__(self, *args, **kwargs):
#         self.staff_id=kwargs.pop("staff_id")
#         super(EditResultForm,self).__init__(*args,**kwargs)
#         subject_list=[]
#         try:
#             subjects=Subjects.objects.filter(staff_id=self.staff_id)
#             for subject in subjects:
#                 subject_single=(subject.id,subject.subject_name)
#                 subject_list.append(subject_single)
#         except:
#             subject_list=[]
#         self.fields['subject_id'].choices=subject_list

#     session_list=[]
#     try:
#         sessions=SessionYearModel.object.all()
#         for session in sessions:
#             session_single=(session.id,str(session.session_start_year)+" TO "+str(session.session_end_year))
#             session_list.append(session_single)
#     except:
#         session_list=[]

#     subject_id=forms.ChoiceField(label="Subject",widget=forms.Select(attrs={"class":"form-control"}))
#     session_ids=forms.ChoiceField(label="Session Year",choices=session_list,widget=forms.Select(attrs={"class":"form-control"}))
#     student_ids=ChoiceNoValidation(label="Student",widget=forms.Select(attrs={"class":"form-control"}))
#     assignment_marks=forms.CharField(label="Assignment Marks",widget=forms.TextInput(attrs={"class":"form-control"}))
#     exam_marks=forms.CharField(label="Exam Marks",widget=forms.TextInput(attrs={"class":"form-control"}))

