from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.contrib.auth import login,logout
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .models import RememberToken
import secrets

from schoolapp.EmailBackEnd import EmailBackEnd

# Create your views here.

def index(request):
     return render(request, 'jobs/index.html', {})

def about(request):
     return render(request, 'jobs/about.html', {}) 

def classes(request):
     return render(request, 'jobs/classes.html', {})    

def academics(request):
     return render(request, 'jobs/academics.html', {})  

def gallery(request):
     
     return render(request, 'jobs/gallery.html', {})

def contact(request):
     return render(request, 'jobs/contact.html', {})   

def user_login(request):
    return render(request, 'jobs/login.html', {})


def DoLogin(request):
    if request.method != "POST":
        return HttpResponse('<h2>Method Not Allowed</h2>')
    else:
        email = request.POST.get("email")
        password = request.POST.get("password")
        remember = request.POST.get("remember_me") == "true"

        user = EmailBackEnd.authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)

            if remember:
                token = secrets.token_hex(32)
                RememberToken.objects.update_or_create(user=user, defaults={'token': token})
                response = HttpResponseRedirect(reverse_user_home(user))
                response.set_cookie('remember_token', token, max_age=60*60*24*7, httponly=True, secure=True)
                return response

            return HttpResponseRedirect(reverse_user_home(user))
        else:
            messages.error(request, "Invalid Login Details (Email or Password)")
            return HttpResponseRedirect("/login")

def reverse_user_home(user):
    if user.user_type == "1":
        return "/admin-home"
    elif user.user_type == "2":
        return reverse("staff_home")
    else:
        return reverse("student_home")
        
def user_logout(request):
    logout(request)
    return HttpResponseRedirect('/')      





def sent(request):
     if request.method == "POST":
          message_name = request.POST['name']
          message_email = request.POST['email']
          message_subject = request.POST['subject']
          message = request.POST['message']
          # send an email 
          send_mail(
               'New message from ' + message_name, 
               message,
               message_email,
               ['febmex02@gmail.com', 'aghason.emmanuel@gmail.com'],
          )
          return render(request, 'jobs/sent.html', {
               'message_name': message_name,
               ' message_email': message_email,
               ' message_subject': message_subject,
               'message' : message
               })
     else:
          return render(request,'jobs/index.html')


