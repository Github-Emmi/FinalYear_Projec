from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.contrib.auth import login,logout
from django.urls import reverse

from schoolapp.EmailBackEnd import EmailBackEnd

# Create your views here.

def index(request):
    return render(request, 'jobs/index.html', {})

def user_login(request):
    return render(request, 'jobs/login.html', {})

def DoLogin(request):
    if request.method != "POST":
        return HttpResponse('<h2>Method Not Allowed</h2>')
    else:
        user = EmailBackEnd.authenticate(request,username=request.POST.get("email"), password=request.POST.get("password"))
        if user!=None:
            login(request, user)
            if user.user_type =="1":
                return HttpResponseRedirect("/admin-home")
            elif user.user_type=="2":
                return HttpResponseRedirect(reverse("staff_home"))
            else:
                return HttpResponseRedirect(reverse("student_home"))
        else:
            messages.error(request,"Invalid Login Details")
            return HttpResponseRedirect("/")
        
def user_logout(request):
    logout(request)
    return HttpResponseRedirect('/')      