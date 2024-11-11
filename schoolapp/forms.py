from django import forms
from schoolapp.models import (
    Departments,
    SessionYearModel,
    Students,
    Class,
)


class DateInput(forms.DateInput):
    input_type = "date"

############################################################
# Add Student Form #
############################################################

class AddStudentForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=50,
        widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "off","placeholder":"Enter your Email"}),
    )
    password = forms.CharField(
        label="Password",
        max_length=50,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder":"Enter your Password"}),
    )
    first_name = forms.CharField(
        label="First Name",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder":"Enter your Surname"}),
    )
    last_name = forms.CharField(
        label="Last Name",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder":"Enter your name(s)"}),
    )
    username = forms.CharField(
        label="Username",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
    )

    department_list = []
    try:
        deparments = Departments.objects.all()
        for deparment in deparments:
            small_deparment = (deparment.id, deparment.department_name)
            department_list.append(small_deparment)
    except:
        department_list = []

    class_list = []
    try:
        classes = Class.objects.all()
        for cl in classes:
            small_class = (cl.id, cl.class_name)
            class_list.append(small_class)
    except:
        class_list = []

    session_list = []
    try:
        sessions = SessionYearModel.objects.all()

        for ses in sessions:
            small_ses = (
                ses.id,
                str(ses.session_start_year) + "   TO  " + str(ses.session_end_year),
            )
            session_list.append(small_ses)
    except:
        session_list = []

    department_id = forms.ChoiceField(
        label="Department",
        choices=department_list,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    class_id = forms.ChoiceField(
        label="Class",
        choices=class_list,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    session_year_id = forms.ChoiceField(
        label="Session Year",
        choices=session_list,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    profile_pic = forms.FileField(
        label="Profile Picture",
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control"}),
    )

    date_of_birth_id = forms.DateField(
        label="Date of Birth",
        widget=DateInput(attrs={"class": "form-control"}),
    )
    age = forms.CharField(
        label="Age",
        max_length=3,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    height = forms.CharField(
        label="Height (cm)",
        max_length=5,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    weight = forms.CharField(
        label="Weight (kg)",
        max_length=5,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    eye_color = forms.CharField(
        label="Eye Color",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    residential_address = forms.CharField(
        label="Residential Address",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    bus_stop = forms.CharField(
        label="Bus Stop",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    religion = forms.CharField(
        label="Religion",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_class = forms.CharField(
        label="Last Class",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    school_attended_last = forms.CharField(
        label="School Attended",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    place_of_birth = forms.CharField(
        label="Place of Birth",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    home_town = forms.CharField(
        label="Home Town",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    state_of_origin = forms.CharField(
        label="State Of Origin",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    lga = forms.CharField(
        label="Local Government Area",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    nationality = forms.CharField(
        label="Nationality",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    gender_choice = (("Male", "Male"), ("Female", "Female"))
    sex = forms.ChoiceField(
        label="Gender",
        choices=gender_choice,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    # Parent Details
    father_name = forms.CharField(
        label="Father's Name",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    father_address = forms.CharField(
        label="Father's Address",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    father_occupation = forms.CharField(
        label="Father's Occupation",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    father_postion = forms.CharField(
        label="Father's Position",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    father_phone_num_1 = forms.CharField(
        label="Father's Phone (Home)",
        max_length=15,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    father_phone_num_2 = forms.CharField(
        label="Father's Phone (Office)",
        max_length=15,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    mother_name = forms.CharField(
        label="Mother's Name",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    mother_address = forms.CharField(
        label="Mother's Address",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    mother_occupation = forms.CharField(
        label="Mother's Occupation",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    mother_position = forms.CharField(
        label="Mother's Position",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    mother_phone_num_1 = forms.CharField(
        label="Mother's Phone (Home)",
        max_length=15,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    mother_phone_num_2 = forms.CharField(
        label="Mother's Phone (Office)",
        max_length=15,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    # Medical Information
    health_choice = (("Yes", "Yes"), ("No", "No"))

    asthmatic = forms.ChoiceField(
        label="Asthmatic",
        choices=health_choice,
        widget=forms.RadioSelect,
    )
    hypertension = forms.ChoiceField(
        label="Hypertension",
        choices=health_choice,
        widget=forms.RadioSelect,
    )
    disabilities = forms.ChoiceField(
        label="Disabilities",
        choices=health_choice,
        widget=forms.RadioSelect,
    )
    epilepsy = forms.ChoiceField(
        label="Epilepsy",
        choices=health_choice,
        widget=forms.RadioSelect,
    )
    blind = forms.ChoiceField(
        label="Blind",
        choices=health_choice,
        widget=forms.RadioSelect,
    )
    mental_illness = forms.ChoiceField(
        label="Mental Illness",
        choices=health_choice,
        widget=forms.RadioSelect,
    )
    tuberculosis = forms.ChoiceField(
        label="tuberculosis",
        choices=health_choice,
        widget=forms.RadioSelect,
        
    )
    spectacle_use = forms.ChoiceField(
        label="Spectacle Use",
        choices=health_choice,  
        widget=forms.RadioSelect,
    )
    sickle_cell = forms.ChoiceField(
        label="Sickle Cell",
        choices=health_choice,
        widget=forms.RadioSelect,
        
    )
    health_problems = forms.ChoiceField(
        label="Health Problems",
        choices=health_choice,
        widget=forms.RadioSelect,
    )
    medication = forms.CharField(
        label="Current Medication",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    drug_allergy = forms.CharField(
        label="Drug Allergies",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


############################################################
# Edit Student Form #
############################################################


class EditStudentForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=50,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "readonly": "readonly",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        max_length=50,
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder":"Leave blank or enter a new password"}),
    )
    first_name = forms.CharField(
        label="First Name",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label="Last Name",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    username = forms.CharField(
        label="Username",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
    )

    department_list = []
    try:
        deparments = Departments.objects.all()
        for deparment in deparments:
            small_deparment = (deparment.id, deparment.department_name)
            department_list.append(small_deparment)
    except:
        department_list = []

    class_list = []
    try:
        classes = Class.objects.all()
        for cl in classes:
            small_class = (cl.id, cl.class_name)
            class_list.append(small_class)
    except:
        class_list = []

    session_list = []
    try:
        sessions = SessionYearModel.objects.all()

        for ses in sessions:
            small_ses = (
                ses.id,
                str(ses.session_start_year) + "   TO  " + str(ses.session_end_year),
            )
            session_list.append(small_ses)
    except:
        session_list = []

    department_id = forms.ChoiceField(
        label="Department",
        choices=department_list,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    class_id = forms.ChoiceField(
        label="Class",
        choices=class_list,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    session_year_id = forms.ChoiceField(
        label="Session Year",
        choices=session_list,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    profile_pic = forms.FileField(
        label="Profile Picture",
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control"}),
    )

    date_of_birth_id = forms.DateField(
        label="Date of Birth",
        widget=DateInput(attrs={"class": "form-control"}),
    )
    age = forms.CharField(
        label="Age",
        max_length=3,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    height = forms.CharField(
        label="Height (cm)",
        max_length=5,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    weight = forms.CharField(
        label="Weight (kg)",
        max_length=5,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    eye_color = forms.CharField(
        label="Eye Color",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    residential_address = forms.CharField(
        label="Residential Address",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    bus_stop = forms.CharField(
        label="Bus Stop",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    religion = forms.CharField(
        label="Religion",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_class = forms.CharField(
        label="Last Class",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    school_attended_last = forms.CharField(
        label="School Attended",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    place_of_birth = forms.CharField(
        label="Place of Birth",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    home_town = forms.CharField(
        label="Home Town",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    state_of_origin = forms.CharField(
        label="State Of Origin",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    lga = forms.CharField(
        label="Local Government Area",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    nationality = forms.CharField(
        label="Nationality",
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    gender_choice = (("Male", "Male"), ("Female", "Female"))
    sex = forms.ChoiceField(
        label="Gender",
        choices=gender_choice,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    # Parent Details
    father_name = forms.CharField(
        label="Father's Name",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    father_address = forms.CharField(
        label="Father's Address",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    father_occupation = forms.CharField(
        label="Father's Occupation",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    father_postion = forms.CharField(
        label="Father's Position",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    father_phone_num_1 = forms.CharField(
        label="Father's Phone (Home)",
        max_length=15,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    father_phone_num_2 = forms.CharField(
        label="Father's Phone (Office)",
        max_length=15,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    mother_name = forms.CharField(
        label="Mother's Name",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    mother_address = forms.CharField(
        label="Mother's Address",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    mother_occupation = forms.CharField(
        label="Mother's Occupation",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    mother_position = forms.CharField(
        label="Mother's Position",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    mother_phone_num_1 = forms.CharField(
        label="Mother's Phone (Home)",
        max_length=15,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    mother_phone_num_2 = forms.CharField(
        label="Mother's Phone (Office)",
        max_length=15,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    # Medical Information
    health_choice = (("Yes", "Yes"), ("No", "No"))

    asthmatic = forms.ChoiceField(
        label="Asthmatic",
        choices=health_choice,
    )
    hypertension = forms.ChoiceField(
        label="Hypertension",
        choices=health_choice,
    )
    disabilities = forms.ChoiceField(
        label="Disabilities",
        choices=health_choice,
    )
    epilepsy = forms.ChoiceField(
        label="Epilepsy",
        choices=health_choice,
    )
    blind = forms.ChoiceField(
        label="Blind",
        choices=health_choice,
    )
    mental_illness = forms.ChoiceField(
        label="Mental Illness",
        choices=health_choice,
    )
    tuberculosis = forms.ChoiceField(
        label="Tuberculosis",
        choices=health_choice,
    )
    spectacle_use = forms.ChoiceField(
        label="Spectacle Use",
        choices=health_choice,
    )
    sickle_cell = forms.ChoiceField(
        label="Sickle Cell",
        choices=health_choice,
    )
    health_problems = forms.ChoiceField(
        label="Health Problems",
        choices=health_choice,
    )
    medication = forms.CharField(
        label="Current Medication",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    drug_allergy = forms.CharField(
        label="Drug Allergies",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )


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
