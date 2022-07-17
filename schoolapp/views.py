from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.contrib.auth import login,logout

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
            return HttpResponseRedirect("/admin-home")
        else:
            messages.error(request, 'Invalid email or password')
            return HttpResponseRedirect("/")
        
def user_logout(request):
    logout(request)
    return HttpResponseRedirect('/')      